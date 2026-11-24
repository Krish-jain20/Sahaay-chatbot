"""Fill any uploaded blank form: detect the blanks, ask only for what is missing, write the answers.

Two paths, both in memory (the upload is never stored and values are never logged):
- fillable PDF: the AcroForm text fields and check boxes are read and set with PyMuPDF;
- flat PDF or photo/scan: each page is rendered to an image, a vision model lists the blanks with
  normalised positions, and the answers are written as text overlays.

Text with Devanagari (or any non-ASCII) is shaped by WeasyPrint (Pango) with the bundled Noto Sans
Devanagari and placed as vector art, because PyMuPDF cannot shape complex scripts. Everything the
model or the uploaded file says is untrusted data: labels are cleaned, keys must be on a fixed list,
positions are clamped, and nothing in the file chooses what the code does.

PyMuPDF does both the AcroForm work and the overlay, so pypdf and ReportLab (named in CLAUDE.md) are
not added as dependencies.
"""

from __future__ import annotations

import html
import math
import re
from pathlib import Path
from typing import Any

import pymupdf
from pydantic import BaseModel, Field

from app.safety.pii import mask_pii, verhoeff_valid

MAX_BYTES = 8 * 1024 * 1024
MAX_PAGES = 5
MAX_VISION_PAGES = 3  # each page is one model call, and free-tier limits are small
MAX_FIELDS = 80
MAX_VALUE_CHARS = 300
RENDER_DPI = 110
FONT_PATH = Path(__file__).parent / "fonts" / "NotoSansDevanagari-Regular.ttf"
MAGIC = {b"%PDF": "pdf", b"\x89PNG": "png", b"\xff\xd8\xff": "jpeg"}

SENSITIVE_KEYS = frozenset({"aadhaar", "pan", "mobile", "bank_account"})
# Profile facts a blank can be matched to: label in en, hi, hn.
PROFILE_KEYS: dict[str, dict[str, str]] = {
    "name": {"en": "Full name", "hi": "पूरा नाम", "hn": "Poora naam"},
    "father_name": {
        "en": "Father's or husband's name",
        "hi": "पिता या पति का नाम",
        "hn": "Pita ya pati ka naam",
    },
    "mother_name": {"en": "Mother's name", "hi": "माता का नाम", "hn": "Mata ka naam"},
    "dob": {"en": "Date of birth", "hi": "जन्म तिथि", "hn": "Janm tithi (date of birth)"},
    "gender": {"en": "Gender", "hi": "लिंग", "hn": "Ling (gender)"},
    "mobile": {"en": "Mobile number", "hi": "मोबाइल नंबर", "hn": "Mobile number"},
    "email": {"en": "Email address", "hi": "ईमेल पता", "hn": "Email address"},
    "aadhaar": {"en": "Aadhaar number", "hi": "आधार नंबर", "hn": "Aadhaar number"},
    "pan": {"en": "PAN", "hi": "PAN", "hn": "PAN"},
    "address": {"en": "Full address", "hi": "पूरा पता", "hn": "Poora pata"},
    "house": {"en": "House or flat number", "hi": "मकान या फ़्लैट नंबर", "hn": "Makaan ya flat number"},
    "locality": {"en": "Locality or colony", "hi": "मोहल्ला या कॉलोनी", "hn": "Mohalla ya colony"},
    "district": {"en": "District", "hi": "ज़िला", "hn": "Zila (district)"},
    "state": {"en": "State", "hi": "राज्य", "hn": "Rajya (state)"},
    "pin": {"en": "PIN code", "hi": "पिन कोड", "hn": "PIN code"},
    "occupation": {"en": "Occupation", "hi": "पेशा", "hn": "Peshaa (occupation)"},
    "annual_income": {"en": "Annual income", "hi": "वार्षिक आय", "hn": "Saalana aay (annual income)"},
    "bank_account": {"en": "Bank account number", "hi": "बैंक खाता नंबर", "hn": "Bank account number"},
}
ASK = {"en": "Please enter: {x}", "hi": "कृपया दर्ज करें: {x}", "hn": "Please darj karein: {x}"}

# Order matters: the specific names come before the bare "name".
_GUESS: list[tuple[str, re.Pattern[str]]] = [
    ("aadhaar", re.compile(r"aadhaar|aadhar|\buid\b|आधार", re.I)),
    ("pan", re.compile(r"\bpan\b|permanent account", re.I)),
    ("bank_account", re.compile(r"bank.*(account|a/c)|account\s*(no|number)|खाता", re.I)),
    ("mobile", re.compile(r"mobile|phone|contact\s*(no|number)|मोबाइल|फ़ोन|फोन", re.I)),
    ("email", re.compile(r"e-?mail|ईमेल", re.I)),
    ("father_name", re.compile(r"father|husband|guardian|पिता|पति", re.I)),
    ("mother_name", re.compile(r"mother|माता", re.I)),
    ("dob", re.compile(r"date of birth|birth date|\bdob\b|जन्म", re.I)),
    ("gender", re.compile(r"gender|\bsex\b|लिंग", re.I)),
    ("pin", re.compile(r"pin\s*code|pincode|postal|\bpin\b|पिन", re.I)),
    ("district", re.compile(r"district|ज़िला|जिला", re.I)),
    ("state", re.compile(r"\bstate\b|राज्य", re.I)),
    ("locality", re.compile(r"locality|colony|mohalla|sub.?locality|मोहल्ला|कॉलोनी", re.I)),
    ("house", re.compile(r"house|flat|door\s*no|plot|मकान", re.I)),
    ("address", re.compile(r"address|पता", re.I)),
    ("occupation", re.compile(r"occupation|profession|पेशा|व्यवसाय", re.I)),
    ("annual_income", re.compile(r"income|आय", re.I)),
    ("name", re.compile(r"\bname\b|नाम", re.I)),
]
_CONTROL = re.compile(r"[\x00-\x1f\x7f]+")
_TRUE = {"yes", "true", "1", "on", "y", "x", "✓"}


class FormError(ValueError):
    """`code` is a short machine string the API returns as is."""

    def __init__(self, code: str, status: int = 422) -> None:
        super().__init__(code)
        self.code = code
        self.status = status


class DetectedField(BaseModel):
    id: str = Field(max_length=40)
    label: str = Field(max_length=120)
    mapped_profile_key: str | None = None
    page: int = Field(ge=0, le=MAX_PAGES - 1)
    x_norm: float = Field(ge=0, le=1)
    y_norm: float = Field(ge=0, le=1)
    required: bool = False
    w_norm: float | None = Field(default=None, ge=0, le=1)
    acro_name: str | None = Field(default=None, max_length=200)  # set for fillable-PDF fields
    kind: str = "text"  # text | checkbox


# ------------------------------------------------------------------ opening the upload


def sniff(data: bytes) -> str:
    for magic, kind in MAGIC.items():
        if data.startswith(magic):
            return kind
    raise FormError("unsupported_type", 415)


def open_upload(data: bytes) -> pymupdf.Document:
    """A PDF, or a photo/scan wrapped as a one-page PDF. Raises FormError for anything else."""
    if len(data) > MAX_BYTES:
        raise FormError("file_too_large", 413)
    kind = sniff(data)
    try:
        if kind == "pdf":
            doc = pymupdf.open(stream=data, filetype="pdf")
        else:
            img = pymupdf.open(stream=data, filetype=kind)
            if img[0].rect.width * img[0].rect.height > 40_000_000:
                raise FormError("image_too_large", 413)
            doc = pymupdf.open("pdf", img.convert_to_pdf())
    except FormError:
        raise
    except Exception as e:  # noqa: BLE001 - PyMuPDF raises several types for damaged files
        raise FormError("unreadable_file") from e
    if doc.needs_pass or doc.is_encrypted:
        raise FormError("encrypted_pdf")
    if len(doc) == 0 or len(doc) > MAX_PAGES:
        raise FormError("too_many_pages")
    return doc


# ------------------------------------------------------------------ detecting fields


def clean_label(raw: str, fallback: str) -> str:
    """Labels come from an untrusted file or model: no control characters, no identity numbers."""
    text = re.sub(r"\s+", " ", _CONTROL.sub(" ", mask_pii(raw or "")[0])).strip()[:100]
    return text or fallback


def guess_key(label: str) -> str | None:
    for key, pattern in _GUESS:
        if pattern.search(label):
            return key
    return None


def acro_fields(doc: pymupdf.Document) -> list[DetectedField]:
    """Text fields and check boxes of a fillable PDF, with the field's position on its page."""
    out: list[DetectedField] = []
    for pno, page in enumerate(doc):
        w, h = page.rect.width, page.rect.height
        for widget in page.widgets() or []:
            kind = {"Text": "text", "CheckBox": "checkbox"}.get(widget.field_type_string)
            if kind is None or not widget.field_name or len(out) >= MAX_FIELDS:
                continue
            label = clean_label(widget.field_label or widget.field_name, f"Field {len(out) + 1}")
            r = widget.rect
            out.append(
                DetectedField(
                    id=f"a{len(out)}",
                    label=label,
                    mapped_profile_key=guess_key(f"{label} {widget.field_name}") if kind == "text" else None,
                    page=pno,
                    x_norm=min(max(r.x0 / w, 0), 1),
                    y_norm=min(max((r.y0 + r.y1) / 2 / h, 0), 1),
                    w_norm=min(max(r.width / w, 0), 1),
                    required=bool(widget.field_flags & 2),
                    acro_name=widget.field_name[:200],
                    kind=kind,
                )
            )
    return out


def render_pages(doc: pymupdf.Document, limit: int = MAX_VISION_PAGES) -> list[bytes]:
    for page in list(doc)[:limit]:
        if page.rotation:
            raise FormError("rotated_page")
    return [page.get_pixmap(dpi=RENDER_DPI).tobytes("png") for page in list(doc)[:limit]]


def finite01(v: float | None) -> float | None:
    return None if v is None or not math.isfinite(v) else min(max(float(v), 0.0), 1.0)


def from_vision(pages: list[list[Any]]) -> list[DetectedField]:
    """Turn per-page model output into safe, id-stamped fields. Ids are ours, never the model's."""
    out: list[DetectedField] = []
    for pno, items in enumerate(pages):
        for item in items[:40]:
            x, y = finite01(item.x_norm), finite01(item.y_norm)
            if x is None or y is None or len(out) >= MAX_FIELDS:
                continue
            label = clean_label(item.label, f"Field {len(out) + 1}")
            key = item.mapped_profile_key if item.mapped_profile_key in PROFILE_KEYS else None
            out.append(
                DetectedField(
                    id=f"p{pno}f{len(out)}",
                    label=label,
                    mapped_profile_key=key or guess_key(label),
                    page=pno,
                    x_norm=x,
                    y_norm=y,
                    required=bool(item.required),
                    w_norm=finite01(item.w_norm),
                )
            )
    return out


# ------------------------------------------------------------------ prefill and questions


def split_known(
    fields: list[DetectedField], known: dict[str, str]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """(prefilled, missing, questions). Only blanks with no known fact are asked about."""
    facts = {k: v.strip() for k, v in known.items() if k in PROFILE_KEYS and isinstance(v, str) and v.strip()}
    prefilled: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    questions: list[dict[str, str]] = []
    for f in fields:
        base = {
            "id": f.id,
            "label": f.label,
            "mapped_profile_key": f.mapped_profile_key,
            "page": f.page,
            "required": f.required,
            "kind": f.kind,
            "sensitive": f.mapped_profile_key in SENSITIVE_KEYS,
        }
        key = f.mapped_profile_key
        if key and key in facts and f.kind == "text":
            prefilled.append({**base, "value": facts[key][:MAX_VALUE_CHARS]})
            continue
        names = PROFILE_KEYS.get(key or "", {})
        i18n = {lang: names.get(lang, f.label) for lang in ("en", "hi", "hn")}
        missing.append({**base, "label_i18n": i18n})
        questions.append({"id": f.id, **{lang: ASK[lang].format(x=i18n[lang]) for lang in ASK}})
    return prefilled, missing, questions


# ------------------------------------------------------------------ writing the answers


def clean_value(field: DetectedField, raw: str) -> str:
    text = re.sub(r"\s+", " ", _CONTROL.sub(" ", raw or "")).strip()[:MAX_VALUE_CHARS]
    key = field.mapped_profile_key
    if text and key == "aadhaar":
        digits = re.sub(r"[\s-]", "", text)
        if not (digits.isdigit() and len(digits) == 12 and verhoeff_valid(digits)):
            raise FormError("invalid_aadhaar")
        return digits
    if text and key == "pan":
        pan = text.replace(" ", "").upper()
        if not re.fullmatch(r"[A-Z]{5}[0-9]{4}[A-Z]", pan):
            raise FormError("invalid_pan")
        return pan
    return text


def _plain(text: str) -> bool:
    return all(0x20 <= ord(c) <= 0x7E for c in text)


def _shaped(text: str, size: float) -> tuple[pymupdf.Document, pymupdf.Rect]:
    """The text as a tiny vector PDF, shaped by Pango, plus the box that holds the ink."""
    from weasyprint import HTML  # heavy import, only needed for non-ASCII values

    css = (
        f'@font-face {{ font-family: "NotoDeva"; src: url("{FONT_PATH.as_uri()}"); }}'
        f"@page {{ size: 1400pt {size * 2.4:.1f}pt; margin: 0 }}"
        f'body {{ margin: {size * 0.4:.1f}pt 0 0 4pt; font-family: "NotoDeva", "Noto Sans", sans-serif; '
        f"font-size: {size:.1f}pt; white-space: nowrap; color: #000 }}"
    )
    page_html = f"<html><head><style>{css}</style></head><body>{html.escape(text)}</body></html>"
    pdf = HTML(string=page_html).write_pdf()
    src = pymupdf.open("pdf", pdf)
    words = src[0].get_text("words")
    box = pymupdf.Rect(words[0][:4]) if words else pymupdf.Rect(0, 0, size * len(text), size * 1.6)
    for w in words[1:]:
        box |= pymupdf.Rect(w[:4])
    return src, box + (-1, -size * 0.2, 1, size * 0.25)


def _draw(page: pymupdf.Page, text: str, x: float, y_mid: float, max_w: float, size: float) -> None:
    if _plain(text):
        fs = size
        width = pymupdf.get_text_length(text, fontname="helv", fontsize=fs)
        if width > max_w > 0:
            fs = max(6.0, size * max_w / width)
        page.insert_text((x, y_mid + fs * 0.35), text, fontsize=fs, fontname="helv", color=(0, 0, 0))
        return
    src, box = _shaped(text, size)
    scale = min(1.0, max_w / box.width) if max_w > 0 else 1.0
    half = box.height * scale / 2
    target = pymupdf.Rect(x, y_mid - half, x + box.width * scale, y_mid + half)
    page.show_pdf_page(target, src, 0, clip=box)


def _widget(page: pymupdf.Page, name: str) -> pymupdf.Widget | None:
    """Looked up while its page is alive: a widget keeps only a weak reference to the page."""
    return next((w for w in page.widgets() or [] if w.field_name == name), None)


def fill(data: bytes, fields: list[DetectedField], values: dict[str, str]) -> bytes:
    """The uploaded form with the answers written in. Raises FormError on a bad value."""
    doc = open_upload(data)
    try:
        for f in fields:
            if f.page >= len(doc):
                continue
            text = clean_value(f, values.get(f.id, ""))
            if not text:
                continue
            page = doc[f.page]
            width, height = page.rect.width, page.rect.height
            size = min(max(height * 0.0125, 8.0), 24.0)
            widget = _widget(page, f.acro_name) if f.acro_name else None
            if widget is not None:
                if widget.field_type_string == "CheckBox":
                    if text.lower() in _TRUE:
                        widget.field_value = widget.on_state()
                        widget.update()
                elif _plain(text):
                    widget.field_value = text
                    widget.update()
                else:  # an AcroForm text field cannot show shaped Devanagari: write it over the box
                    r = widget.rect
                    _draw(page, text, r.x0 + 2, (r.y0 + r.y1) / 2, r.width - 4, min(size, r.height * 0.8))
                continue
            if f.acro_name:  # the field name no longer exists in this file
                continue
            x = f.x_norm * width
            max_w = (f.w_norm * width) if f.w_norm else max(width * 0.97 - x, 20)
            _draw(page, text, x, f.y_norm * height, max_w, size)
        return doc.tobytes(deflate=True)
    finally:
        doc.close()
