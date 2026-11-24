"""Fill the official flat PDF forms listed in data/forms/forms.json.

The form is a printed layout with no fillable fields, so values are overlaid at fixed positions with
PyMuPDF (English letters and digits only, a limit of the standard PDF fonts). Everything happens in
memory: the filled PDF is returned to the caller and never stored. The Aadhaar number is the one
value written in full, at fill time only. It is never stored or logged, and previews show the last 4.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pymupdf

from app.data.models import Allowlist
from app.safety.allowlist import is_allowed
from app.safety.pii import verhoeff_valid

FONT_SIZE = 9.5
ASCII_RE = re.compile(r"^[\x20-\x7e]*$")


class FormError(ValueError):
    pass


@dataclass(frozen=True)
class FormField:
    key: str
    page: int
    x: float
    y: float
    max_chars: int
    sensitive: bool = False
    type: str = "line"  # line: free text | cells: one character per printed box | box: one centred value
    edges: tuple[float, ...] = ()  # cells: x of every box edge, left to right
    x1: float = 0.0  # box: right edge
    clear_y0: float = 0.0  # box: area blanked first so printed hints do not clash
    clear_y1: float = 0.0


@dataclass(frozen=True)
class FormSpec:
    id: str
    service_id: str
    title: str
    source_url: str
    date_checked: str
    notes: str
    path: Path
    pages: int
    fields: dict[str, FormField]

    def public(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "service_id": self.service_id,
            "title": self.title,
            "source_url": self.source_url,
            "date_checked": self.date_checked,
            "fields": [
                {"key": f.key, "max_chars": f.max_chars, "sensitive": f.sensitive}
                for f in self.fields.values()
            ],
        }


def load_forms(data_dir: Path, allowlist: Allowlist) -> dict[str, FormSpec]:
    raw = json.loads((data_dir / "forms" / "forms.json").read_text("utf-8"))
    out: dict[str, FormSpec] = {}
    for f in raw["forms"]:
        path = data_dir / "forms" / f["file"]
        if not is_allowed(f["source_url"], allowlist):
            raise FormError(f"{f['id']}: source host is not on the allowlist")
        if hashlib.sha256(path.read_bytes()).hexdigest() != f["sha256"]:
            raise FormError(f"{f['id']}: PDF does not match the recorded checksum")
        with pymupdf.open(path) as doc:
            if len(doc) != f["pages"]:
                raise FormError(f"{f['id']}: page count changed")
        fields = {x["key"]: FormField(**{**x, "edges": tuple(x.get("edges", ()))}) for x in f["fields"]}
        out[f["id"]] = FormSpec(
            f["id"],
            f["service_id"],
            f["title"],
            f["source_url"],
            f["date_checked"],
            f["notes"],
            path,
            f["pages"],
            fields,
        )
    return out


def clean_values(spec: FormSpec, values: dict[str, str]) -> dict[str, str]:
    """Validate and normalise. The Aadhaar number must be 12 valid digits (spaces allowed)."""
    unknown = set(values) - set(spec.fields)
    if unknown:
        raise FormError(f"unknown_fields:{','.join(sorted(unknown))}")
    out: dict[str, str] = {}
    for key, raw in values.items():
        text = (raw or "").strip()
        if not text:
            continue
        field = spec.fields[key]
        if key == "uid":
            digits = re.sub(r"\s+", "", text)
            if not (digits.isdigit() and len(digits) == 12 and verhoeff_valid(digits)):
                raise FormError("invalid_aadhaar")
            text = digits
        if not ASCII_RE.match(text):
            raise FormError(f"ascii_only:{key}")
        if len(text) > field.max_chars:
            raise FormError(f"too_long:{key}:{field.max_chars}")
        out[key] = text
    if not out.get("name"):
        raise FormError("missing_required:name")
    return out


def shown(spec: FormSpec, values: dict[str, str]) -> dict[str, str]:
    """What the review screen displays: identity numbers cut to the last 4 digits."""
    return {k: ("XXXX XXXX " + v[-4:] if k == "uid" else v) for k, v in values.items()}


def content_hash(spec_id: str, values: dict[str, str]) -> str:
    blob = json.dumps({"form": spec_id, "values": values}, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()


def fill(spec: FormSpec, values: dict[str, str]) -> bytes:
    with pymupdf.open(spec.path) as doc:
        for key, text in values.items():
            f = spec.fields[key]
            page = doc[f.page]
            if f.type == "cells":
                for i, ch in enumerate(text[: len(f.edges) - 1]):
                    cx = (f.edges[i] + f.edges[i + 1]) / 2
                    w = pymupdf.get_text_length(ch, fontname="helv", fontsize=FONT_SIZE)
                    page.insert_text(
                        (cx - w / 2, f.y), ch, fontsize=FONT_SIZE, fontname="helv", color=(0, 0, 0)
                    )
            elif f.type == "box":
                page.draw_rect(
                    pymupdf.Rect(f.x + 1, f.clear_y0, f.x1 - 1, f.clear_y1 - 1), color=None, fill=(1, 1, 1)
                )
                w = pymupdf.get_text_length(text, fontname="helv", fontsize=FONT_SIZE)
                page.insert_text(
                    ((f.x + f.x1) / 2 - w / 2, f.y),
                    text,
                    fontsize=FONT_SIZE,
                    fontname="helv",
                    color=(0, 0, 0),
                )
            else:
                page.insert_text((f.x, f.y), text, fontsize=FONT_SIZE, fontname="helv", color=(0, 0, 0))
        return doc.tobytes(deflate=True)
