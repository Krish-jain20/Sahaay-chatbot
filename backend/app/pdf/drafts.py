"""Complaint, RTI and CPGRAMS drafts rendered to PDF with WeasyPrint.

Only values the user typed or confirmed are used. Identity numbers are masked before anything is
rendered. Fees, deadlines and addresses are never filled in by us: if the user did not give a value
the draft says so. PDFs are returned to the caller and never stored. Devanagari is shaped by
WeasyPrint (Pango) using Noto Sans Devanagari.
"""

from __future__ import annotations

import hashlib
import html
import json
from dataclasses import dataclass
from typing import Literal

from app.safety.pii import mask_pii

Kind = Literal["complaint", "rti", "cpgrams"]
Lang = Literal["en", "hi"]  # Hinglish drafts are written in English

MAX_FIELD = 2000


@dataclass(frozen=True)
class FieldSpec:
    key: str
    required: bool
    multiline: bool = False


SPECS: dict[str, list[FieldSpec]] = {
    "complaint": [
        FieldSpec("full_name", True),
        FieldSpec("address", False, True),
        FieldSpec("addressed_to", True),
        FieldSpec("service_name", True),
        FieldSpec("application_ref", False),
        FieldSpec("applied_on", False),
        FieldSpec("issue", True, True),
        FieldSpec("requested_action", True, True),
    ],
    "rti": [
        FieldSpec("full_name", True),
        FieldSpec("address", True, True),
        FieldSpec("authority", True),
        FieldSpec("info_sought", True, True),
        FieldSpec("period", False),
        FieldSpec("bpl", False),
    ],
    "cpgrams": [
        FieldSpec("full_name", True),
        FieldSpec("contact", False),
        FieldSpec("department", True),
        FieldSpec("grievance", True, True),
        FieldSpec("requested_action", True, True),
    ],
}

TEXT: dict[str, dict[str, dict[str, str]]] = {
    "en": {
        "title": {
            "complaint": "Complaint about a delay or refusal of a service",
            "rti": "Application under the Right to Information Act, 2005",
            "cpgrams": "Public grievance (draft for the CPGRAMS portal)",
        },
        "label": {
            "full_name": "Name",
            "address": "Address",
            "addressed_to": "Addressed to (officer / office)",
            "service_name": "Service",
            "application_ref": "Application reference (last 4 shown)",
            "applied_on": "Applied on",
            "issue": "What happened",
            "requested_action": "What I am asking for",
            "authority": "Public authority",
            "info_sought": "Information sought",
            "period": "Period",
            "bpl": "Below Poverty Line applicant",
            "contact": "Contact (last 4 digits shown)",
            "department": "Ministry / department",
            "grievance": "Grievance",
        },
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
        "complaint_intro": "I am writing about the service named below.",
        "cpgrams_note": "Copy these fields into the official CPGRAMS portal. This page is only a draft.",
    },
    "hi": {
        "title": {
            "complaint": "सेवा में देरी या इनकार के बारे में शिकायत",
            "rti": "सूचना का अधिकार अधिनियम, 2005 के अंतर्गत आवेदन",
            "cpgrams": "जन शिकायत (CPGRAMS पोर्टल के लिए मसौदा)",
        },
        "label": {
            "full_name": "नाम",
            "address": "पता",
            "addressed_to": "किसे संबोधित (अधिकारी / कार्यालय)",
            "service_name": "सेवा",
            "application_ref": "आवेदन संदर्भ (अंतिम 4 अंक)",
            "applied_on": "आवेदन की तारीख",
            "issue": "क्या हुआ",
            "requested_action": "मेरा अनुरोध",
            "authority": "लोक प्राधिकरण",
            "info_sought": "माँगी गई जानकारी",
            "period": "अवधि",
            "bpl": "गरीबी रेखा से नीचे (BPL) आवेदक",
            "contact": "संपर्क (अंतिम 4 अंक)",
            "department": "मंत्रालय / विभाग",
            "grievance": "शिकायत",
        },
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
        "complaint_intro": "मैं नीचे बताई गई सेवा के संबंध में लिख रहा/रही हूँ।",
        "cpgrams_note": "इन विवरणों को आधिकारिक CPGRAMS पोर्टल में भरें। यह पन्ना केवल मसौदा है।",
    },
}

CSS = """
@page { size: A4; margin: 22mm 20mm; }
body { font-family: 'Noto Sans Devanagari', 'Noto Sans', 'DejaVu Sans', sans-serif; font-size: 11.5pt;
       line-height: 1.55; color: #1c2b33; }
h1 { font-size: 15pt; color: #0f4c5c; margin: 0 0 14pt; }
.meta { margin: 0 0 12pt; }
dl { margin: 0; } dt { font-weight: bold; margin-top: 9pt; } dd { margin: 2pt 0 0; }
footer { position: running(foot); }
.foot { margin-top: 26pt; padding-top: 8pt; border-top: 1px solid #c9bfa9; font-size: 9pt; color: #5b6b73; }
"""


class DraftError(ValueError):
    pass


def clean_fields(kind: str, fields: dict[str, str | bool | None]) -> dict[str, str]:
    """Keep only known keys, trim, mask identity numbers, drop empties."""
    if kind not in SPECS:
        raise DraftError("unknown_kind")
    known = {s.key for s in SPECS[kind]}
    extra = set(fields) - known
    if extra:
        raise DraftError(f"unknown_fields:{','.join(sorted(extra))}")
    out: dict[str, str] = {}
    for k, v in fields.items():
        if isinstance(v, bool):
            if v:
                out[k] = "yes"
            continue
        text = (v or "").strip()
        if not text:
            continue
        if len(text) > MAX_FIELD:
            raise DraftError(f"too_long:{k}")
        out[k] = mask_pii(text)[0]
    return out


def missing_required(kind: str, fields: dict[str, str]) -> list[str]:
    return [s.key for s in SPECS[kind] if s.required and not fields.get(s.key)]


def content_hash(kind: str, lang: str, fields: dict[str, str]) -> str:
    blob = json.dumps({"kind": kind, "lang": lang, "fields": fields}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode()).hexdigest()


def preview(kind: str, lang: Lang, fields: dict[str, str]) -> list[dict[str, str]]:
    t = TEXT[lang]
    rows = []
    for s in SPECS[kind]:
        v = fields.get(s.key)
        shown = t["yes"] if v == "yes" and s.key == "bpl" else v
        rows.append({"key": s.key, "label": t["label"][s.key], "value": shown or t["not_given"]})
    return rows


def _p(text: str) -> str:
    return html.escape(text).replace("\n", "<br>")


def build_html(kind: str, lang: Lang, fields: dict[str, str]) -> str:
    t = TEXT[lang]
    parts = [f"<h1>{_p(t['title'][kind])}</h1>"]
    if kind == "rti":
        parts.append(f"<p>{_p(t['to'])}<br>{_p(fields['authority'])}</p>")
        parts.append(f"<p>{_p(t['rti_intro'])}</p>")
        parts.append(f"<p>{_p(fields['info_sought'])}</p>")
        if fields.get("period"):
            parts.append(f"<p><b>{_p(t['label']['period'])}:</b> {_p(fields['period'])}</p>")
        parts.append(f"<p>{_p(t['rti_fee'])}</p>")
        if fields.get("bpl"):
            parts.append(f"<p>{_p(t['rti_bpl'])}</p>")
        parts.append(
            f"<p>{_p(t['respectfully'])}<br>{_p(fields['full_name'])}<br>{_p(fields['address'])}</p>"
        )
    elif kind == "complaint":
        parts.append(f"<p>{_p(t['to'])}<br>{_p(fields['addressed_to'])}</p>")
        parts.append(
            f"<p><b>{_p(t['subject'])}:</b> {_p(t['title'][kind])} · {_p(fields['service_name'])}</p>"
        )
        parts.append(f"<p>{_p(t['complaint_intro'])}</p><dl>")
        for key in ("application_ref", "applied_on", "issue", "requested_action"):
            if fields.get(key):
                parts.append(f"<dt>{_p(t['label'][key])}</dt><dd>{_p(fields[key])}</dd>")
        parts.append("</dl>")
        sig = f"{_p(t['respectfully'])}<br>{_p(fields['full_name'])}"
        if fields.get("address"):
            sig += f"<br>{_p(fields['address'])}"
        parts.append(f"<p>{sig}</p>")
    else:
        parts.append(f"<p class='meta'>{_p(t['cpgrams_note'])}</p><dl>")
        for s in SPECS["cpgrams"]:
            if fields.get(s.key):
                parts.append(f"<dt>{_p(t['label'][s.key])}</dt><dd>{_p(fields[s.key])}</dd>")
        parts.append("</dl>")
    parts.append(f"<div class='foot'>{_p(t['footer'])}</div>")
    return (
        f"<!doctype html><html lang='{lang}'><head><meta charset='utf-8'><style>{CSS}</style></head>"
        f"<body>{''.join(parts)}</body></html>"
    )


def render_pdf(kind: str, lang: Lang, fields: dict[str, str]) -> bytes:
    from weasyprint import HTML  # imported late: heavy, and needs system libraries

    return HTML(string=build_html(kind, lang, fields)).write_pdf()
