"""Document pipeline. Everything happens in memory: bytes in, masked fields out.

upload bytes -> type/size check -> PDF pages via PyMuPDF -> OpenCV quality -> Tesseract (stdin/stdout,
no temp files) -> PII masked -> extractors -> findings. Nothing is written to disk or a database here.
The recognised text is treated as data only: it is parsed with fixed patterns and never sent to a
model or used to choose an action.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import pymupdf as fitz  # PyMuPDF

from app.ocr.extractors import EXTRACTORS
from app.safety.pii import mask_pii

MAX_BYTES = 8 * 1024 * 1024
MAX_PIXELS = 40_000_000
MAX_PDF_PAGES = 3
OCR_TIMEOUT_S = 45
TARGET_DPI = 200

MAGIC = {b"%PDF": "pdf", b"\x89PNG": "png", b"\xff\xd8\xff": "jpeg"}


class UploadError(ValueError):
    def __init__(self, code: str, status: int) -> None:
        super().__init__(code)
        self.code = code
        self.status = status


@dataclass
class Finding:
    code: str  # unreadable | blurry | low_resolution | missing_field | unknown_doc_type
    field: str | None = None


@dataclass
class ExtractionResult:
    doc_type: str
    fields: dict[str, Any] = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)
    quality: dict[str, Any] = field(default_factory=dict)


def sniff(data: bytes) -> str:
    for magic, kind in MAGIC.items():
        if data.startswith(magic):
            return kind
    raise UploadError("unsupported_type", 415)


def load_doc_types(data_dir: Path) -> dict[str, dict[str, Any]]:
    raw = json.loads((data_dir / "doc_types.json").read_text("utf-8"))
    return {d["id"]: d for d in raw["doc_types"]}


def _pages(data: bytes, kind: str) -> list[np.ndarray]:
    if kind == "pdf":
        try:
            doc = fitz.open(stream=data, filetype="pdf")
        except Exception as e:  # noqa: BLE001 - corrupt PDFs raise many types
            raise UploadError("corrupt_file", 422) from e
        if doc.is_encrypted:
            raise UploadError("encrypted_pdf", 422)
        pages = []
        for page in list(doc)[:MAX_PDF_PAGES]:
            pix = page.get_pixmap(dpi=TARGET_DPI)
            arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
            pages.append(cv2.cvtColor(arr, cv2.COLOR_RGB2BGR if pix.n == 3 else cv2.COLOR_RGBA2BGR))
        return pages
    img = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise UploadError("corrupt_file", 422)
    return [img]


def blur_score(img: np.ndarray) -> float:
    """Variance of the Laplacian: low means blurry."""
    return float(cv2.Laplacian(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var())


def ocr(img: np.ndarray) -> str:
    ok, png = cv2.imencode(".png", img)
    if not ok:
        return ""
    try:
        proc = subprocess.run(  # noqa: S603 - fixed argv, image goes over stdin
            ["tesseract", "stdin", "stdout", "-l", "eng+hin", "--psm", "6"],
            input=png.tobytes(),
            capture_output=True,
            timeout=OCR_TIMEOUT_S,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        raise UploadError("ocr_unavailable", 503) from e
    return proc.stdout.decode("utf-8", errors="replace")


def process(data: bytes, doc_type: str, doc_types: dict[str, dict[str, Any]]) -> ExtractionResult:
    if len(data) > MAX_BYTES:
        raise UploadError("too_large", 413)
    if doc_type not in doc_types:
        raise UploadError("unknown_doc_type", 422)
    kind = sniff(data)
    spec = doc_types[doc_type]
    pages = _pages(data, kind)
    result = ExtractionResult(doc_type=doc_type)
    if any(p.shape[0] * p.shape[1] > MAX_PIXELS for p in pages):
        raise UploadError("too_large", 413)

    scores = [blur_score(p) for p in pages]
    heights = [p.shape[0] for p in pages]
    # A scan whose long side is under ~1100px is below roughly 100 dpi on an A5 page.
    result.quality = {"blur_score": round(min(scores), 1), "min_height_px": min(heights), "pages": len(pages)}
    if min(scores) < spec["quality"]["min_blur_score"]:
        result.findings.append(Finding("blurry"))
    if kind != "pdf" and max(max(p.shape[:2]) for p in pages) < spec["quality"]["min_dpi"] * 6:
        result.findings.append(Finding("low_resolution"))

    text = "\n".join(ocr(p) for p in pages)
    masked_text, _ = mask_pii(text)  # masked for logs/anything downstream; extractors see raw only for IDs
    if len(text.strip()) < 15:
        result.findings.insert(0, Finding("unreadable"))
        return result

    result.fields = EXTRACTORS[doc_type](text, masked_text)
    for name in spec["required_fields"]:
        if result.fields.get(name) in (None, ""):
            result.findings.append(Finding("missing_field", name))
    return result
