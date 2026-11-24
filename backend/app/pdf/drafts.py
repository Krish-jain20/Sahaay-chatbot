"""Draft letters (see draft_catalog.py) rendered to PDF with WeasyPrint.

Only values the user typed or confirmed are used. Identity numbers are masked before anything is
rendered. Fees, deadlines and addresses are never filled in by us: if the user did not give a value
the draft says so. PDFs are returned to the caller and never stored. Devanagari is shaped by
WeasyPrint (Pango) using Noto Sans Devanagari.
"""

from __future__ import annotations

import hashlib
import html
import json
from datetime import date
from pathlib import Path
from typing import Literal

from app.pdf.draft_catalog import BY_ID, FIELDS, DraftKind
from app.safety.pii import mask_pii

Lang = Literal["en", "hi"]  # Hinglish drafts are written in English

MAX_FIELD = 2000

TEXT: dict[str, dict[str, str]] = {
    "en": {
        "to": "To,",
        "subject": "Subject",
        "respectfully": "Respectfully,",
        "yes": "Yes",
        "not_given": "Not provided",
        "footer": "Drafted with Sahaay, an AI assistant, not an official government channel. "
        "Check every detail before sending. Fees and addresses must be confirmed on the official source.",
        "rti_intro": "Under the Right to Information Act, 2005, please provide the following information:",
        "rti_fee": "I will pay the application fee in the manner prescribed (verify the current fee and mode "
        "with the public authority).",
        "rti_bpl": "I belong to the Below Poverty Line category (supporting proof attached).",
        "cpgrams_note": "Copy these fields into the official CPGRAMS portal. This page is only a draft.",
        "enclosures": "Keep ready to attach",
        "portal": "Official portal",
    },
    "hi": {
        "to": "सेवा में,",
        "subject": "विषय",
        "respectfully": "भवदीय,",
        "yes": "हाँ",
        "not_given": "दिया नहीं गया",
        "footer": "यह मसौदा सहाय (AI सहायक, सरकारी माध्यम नहीं) की मदद से बना है। भेजने से पहले हर "
        "जानकारी जाँच लें। शुल्क और पते आधिकारिक स्रोत से पक्के करें।",
        "rti_intro": "सूचना का अधिकार अधिनियम, 2005 के अंतर्गत कृपया निम्नलिखित जानकारी उपलब्ध कराएँ:",
        "rti_fee": "मैं आवेदन शुल्क निर्धारित तरीके से जमा करूँगा/करूँगी (वर्तमान शुल्क और तरीका लोक प्राधिकरण से पक्का करें)।",
        "rti_bpl": "मैं गरीबी रेखा से नीचे (BPL) श्रेणी का हूँ/हूँ (प्रमाण संलग्न)।",
        "cpgrams_note": "इन विवरणों को आधिकारिक CPGRAMS पोर्टल में भरें। यह पन्ना केवल मसौदा है।",
        "enclosures": "संलग्न करने के लिए तैयार रखें",
        "portal": "आधिकारिक पोर्टल",
    },
}

FONT_DIR = Path(__file__).parent / "fonts"

CSS = """
@font-face { font-family: 'Noto Sans Devanagari'; src: url('NotoSansDevanagari-Regular.ttf'); }
@page { size: A4; margin: 22mm 20mm; }
body { font-family: 'Noto Sans Devanagari', 'Noto Sans', 'DejaVu Sans', sans-serif; font-size: 11.5pt;
       line-height: 1.55; color: #1c2b33; }
h1 { font-size: 15pt; color: #0f4c5c; margin: 0 0 14pt; }
.meta { margin: 0 0 12pt; }
dl { margin: 0; } dt { font-weight: bold; margin-top: 9pt; } dd { margin: 2pt 0 0; }
.enc { margin-top: 14pt; font-size: 10pt; color: #3f4f57; }
.foot { margin-top: 26pt; padding-top: 8pt; border-top: 1px solid #c9bfa9; font-size: 9pt; color: #5b6b73; }
"""

# Fields that make up the sender block or the addressee, so they are not repeated in the detail list.
_SENDER = {"full_name", "address", "contact"}
_MASKED = {"consumer_no", "pension_ref", "txn_ref", "contact"}


class DraftError(ValueError):
    pass


def _kind(kind: str) -> DraftKind:
    if kind not in BY_ID:
        raise DraftError("unknown_kind")
    return BY_ID[kind]


def _parse_date(text: str) -> date | None:
    text = text.strip()
    for sep in ("-", "/", "."):
        parts = text.split(sep)
        if len(parts) != 3 or not all(p.isdigit() for p in parts):
            continue
        a, b, c = (int(p) for p in parts)
        try:
            return date(a, b, c) if len(parts[0]) == 4 else date(c, b, a)
        except ValueError:
            return None
    return None


def clean_fields(kind: str, fields: dict[str, str | bool | None]) -> dict[str, str]:
    """Keep only known keys, trim, mask identity numbers, validate dates and choices, drop empties."""
    k = _kind(kind)
    allowed = {f.key for f in k.fields}
    extra = set(fields) - allowed
    if extra:
        raise DraftError(f"unknown_fields:{','.join(sorted(extra))}")
    out: dict[str, str] = {}
    for key, v in fields.items():
        spec = FIELDS[key]
        if isinstance(v, bool):
            if v and spec.type == "checkbox":
                out[key] = "yes"
            continue
        text = (v or "").strip()
        if not text:
            continue
        if len(text) > MAX_FIELD:
            raise DraftError(f"too_long:{key}")
        if spec.type == "date":
            d = _parse_date(text)
            if d is None:
                raise DraftError(f"invalid_date:{key}")
            if d > date.today():
                raise DraftError(f"future_date:{key}")
            text = d.isoformat()
        elif spec.type == "choice":
            if text not in {o for o, _ in spec.options}:
                raise DraftError(f"invalid_choice:{key}")
        elif spec.type == "checkbox":
            if text.lower() in {"yes", "true"}:
                out[key] = "yes"
            continue
        else:
            text = mask_pii(text)[0]
            if key in _MASKED:
                text = _last4(text)
        out[key] = text
    return out


def _last4(text: str) -> str:
    """Reference numbers keep only their last 4 characters when long, like other identity numbers."""
    compact = text.replace(" ", "")
    if len(compact) <= 6 or "*" in compact or "@" in compact:
        return text
    return "XXXX" + compact[-4:]


def missing_required(kind: str, fields: dict[str, str]) -> list[str]:
    return [key for key in _kind(kind).required_keys if not fields.get(key)]


def content_hash(kind: str, lang: str, fields: dict[str, str]) -> str:
    blob = json.dumps({"kind": kind, "lang": lang, "fields": fields}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode()).hexdigest()


def label(key: str, lang: Lang) -> str:
    return FIELDS[key].label.get(lang)


def shown(key: str, value: str | None, lang: Lang) -> str:
    """The value as a reader sees it: choice ids become words, dates dd/mm/yyyy."""
    t = TEXT[lang]
    if not value:
        return t["not_given"]
    spec = FIELDS[key]
    if spec.type == "checkbox":
        return t["yes"]
    if spec.type == "choice":
        return dict(spec.options)[value].get(lang)
    if spec.type == "date":
        d = date.fromisoformat(value)
        return f"{d.day:02d}/{d.month:02d}/{d.year}"
    return value


def preview(kind: str, lang: Lang, fields: dict[str, str]) -> list[dict[str, str]]:
    return [
        {"key": f.key, "label": label(f.key, lang), "value": shown(f.key, fields.get(f.key), lang)}
        for f in _kind(kind).fields
    ]


def _p(text: str) -> str:
    return html.escape(text).replace("\n", "<br>")


def _row(key: str, lang: Lang, fields: dict[str, str]) -> str:
    return f"<dt>{_p(label(key, lang))}</dt><dd>{_p(shown(key, fields[key], lang))}</dd>"


def _sender(t: dict[str, str], fields: dict[str, str]) -> str:
    sig = f"{_p(t['respectfully'])}<br>{_p(fields['full_name'])}"
    for key in ("address", "contact"):
        if fields.get(key):
            sig += f"<br>{_p(fields[key])}"
    return f"<p>{sig}</p>"


def _enclosures(k: DraftKind, lang: Lang, t: dict[str, str]) -> str:
    if not k.enclose:
        return ""
    return f"<p class='enc'><b>{_p(t['enclosures'])}:</b> {_p(k.enclose.get(lang))}</p>"


def build_html(kind: str, lang: Lang, fields: dict[str, str]) -> str:
    k = _kind(kind)
    t = TEXT[lang]
    title = k.subject.get(lang)
    parts = [f"<h1>{_p(title)}</h1>"]
    if k.style == "rti":
        parts.append(f"<p>{_p(t['to'])}<br>{_p(fields['authority'])}</p>")
        parts.append(f"<p>{_p(t['rti_intro'])}</p>")
        parts.append(f"<p>{_p(fields['info_sought'])}</p>")
        if fields.get("period"):
            parts.append(f"<p><b>{_p(label('period', lang))}:</b> {_p(fields['period'])}</p>")
        parts.append(f"<p>{_p(t['rti_fee'])}</p>")
        if fields.get("bpl"):
            parts.append(f"<p>{_p(t['rti_bpl'])}</p>")
        parts.append(_sender(t, fields))
    elif k.style == "portal":
        parts.append(f"<p class='meta'>{_p(t['cpgrams_note'])}</p><dl>")
        for f in k.fields:
            if fields.get(f.key):
                parts.append(_row(f.key, lang, fields))
        parts.append("</dl>")
    else:
        if k.to_key and fields.get(k.to_key):
            parts.append(f"<p>{_p(t['to'])}<br>{_p(fields[k.to_key])}</p>")
        parts.append(f"<p><b>{_p(t['subject'])}:</b> {_p(title)}</p>")
        if k.intro:
            parts.append(f"<p>{_p(k.intro.get(lang))}</p>")
        parts.append("<dl>")
        for f in k.fields:
            if f.key in _SENDER or f.key == k.to_key or not fields.get(f.key):
                continue
            parts.append(_row(f.key, lang, fields))
        parts.append("</dl>")
        if k.closing:
            parts.append(f"<p>{_p(k.closing.get(lang))}</p>")
        parts.append(_sender(t, fields))
        parts.append(_enclosures(k, lang, t))
    if k.style == "rti":
        parts.append(_enclosures(k, lang, t))
    parts.append(f"<div class='foot'>{_p(t['footer'])}</div>")
    return (
        f"<!doctype html><html lang='{lang}'><head><meta charset='utf-8'><style>{CSS}</style></head>"
        f"<body>{''.join(parts)}</body></html>"
    )


def render_pdf(kind: str, lang: Lang, fields: dict[str, str]) -> bytes:
    from weasyprint import HTML  # imported late: heavy, and needs system libraries

    return HTML(string=build_html(kind, lang, fields), base_url=str(FONT_DIR) + "/").write_pdf()


def catalog(lang: str, portals: dict[str, str | None]) -> dict[str, object]:
    """Everything the Drafts page needs, localised. `portals` maps allowlisted host -> date checked."""
    from app.pdf.draft_catalog import GROUPS, KINDS

    def field(ref) -> dict[str, object]:  # noqa: ANN001
        s = ref.spec
        return {
            "key": s.key,
            "type": s.type,
            "required": ref.required,
            "label": s.label.get(lang),
            "hint": s.hint.get(lang) if s.hint else None,
            "options": [{"id": oid, "label": ol.get(lang)} for oid, ol in s.options],
        }

    def card(k: DraftKind) -> dict[str, object]:
        host = k.portal_host
        return {
            "id": k.id,
            "group": k.group,
            "icon": k.icon,
            "title": k.title.get(lang),
            "blurb": k.blurb.get(lang),
            "tags": list(k.tags),
            "enclose": k.enclose.get(lang) if k.enclose else None,
            "portal": (
                {"host": host, "url": f"https://{host}/", "date_checked": portals.get(host)} if host else None
            ),
            "fields": [field(r) for r in k.fields],
        }

    return {
        "groups": [{"id": gid, "title": g.get(lang)} for gid, g in GROUPS],
        "kinds": [card(k) for k in KINDS],
    }
