# ruff: noqa: E501  (long user-facing strings)
"""Case summary PDF: one page the user can keep or show at an office.

Contains the service, the user's own progress, the document checklist (how each item was evaluated),
fees and timeline exactly as in the record ("Verify locally" when unknown) and the sources with the
date they were checked. It never states or implies live government status or approval.
"""

from __future__ import annotations

import html
from datetime import date
from typing import Any, Literal

from app.data.models import ServiceRecord
from app.pdf.drafts import CSS
from app.rules.fees import fee_strip
from app.rules.journey import Journey
from app.rules.readiness import Readiness

Lang = Literal["en", "hi"]

T: dict[str, dict[str, Any]] = {
    "en": {
        "title": "Case summary",
        "own": "Your own progress, recorded by you. Not government status.",
        "steps": [
            "Eligibility checked",
            "Documents verified",
            "Form filled",
            "Submitted on official portal",
            "Reference saved",
        ],
        "done": "Done",
        "todo": "Not yet",
        "checklist": "Document checklist",
        "ready": "{done} of {total} required documents ready. Based on your checklist, not a prediction of approval.",
        "status": {"ok": "Ready", "missing": "Missing", "expired": "Expired", "too_old": "Too old"},
        "how": {
            "scanned_and_confirmed": "read from your upload, confirmed by you",
            "user_declared": "you said you have it, not checked",
            "not_provided": "not provided",
        },
        "required": "required",
        "optional": "optional",
        "fees": "Fees and time",
        "official_fee": "Official fee",
        "csc_fee": "Common Service Centre, at most",
        "days": "Processing time",
        "verify": "Verify locally",
        "days_unit": "{n} {kind} days",
        "working": "working",
        "calendar": "calendar",
        "submission": "Submission",
        "submitted_on": "Submitted on",
        "reference": "Reference (last 4 shown)",
        "sources": "Sources",
        "checked": "checked",
        "footer": "Drafted with Sahaay, an AI assistant, not an official government channel. Confirm details on the official source.",
        "rs": "Rs.",
    },
    "hi": {
        "title": "केस सारांश",
        "own": "आपकी अपनी प्रगति, जो आपने दर्ज की। सरकारी स्थिति नहीं।",
        "steps": ["पात्रता जाँची", "दस्तावेज़ जाँचे", "फ़ॉर्म भरा", "आधिकारिक पोर्टल पर जमा", "संदर्भ संख्या सहेजी"],
        "done": "हो गया",
        "todo": "अभी नहीं",
        "checklist": "दस्तावेज़ चेकलिस्ट",
        "ready": "{total} में से {done} ज़रूरी दस्तावेज़ तैयार। आपकी चेकलिस्ट पर आधारित, मंज़ूरी का अनुमान नहीं।",
        "status": {"ok": "तैयार", "missing": "कमी", "expired": "समाप्त", "too_old": "बहुत पुराना"},
        "how": {
            "scanned_and_confirmed": "आपके अपलोड से पढ़ा, आपने पुष्टि की",
            "user_declared": "आपने कहा आपके पास है, जाँचा नहीं",
            "not_provided": "दिया नहीं गया",
        },
        "required": "ज़रूरी",
        "optional": "वैकल्पिक",
        "fees": "शुल्क और समय",
        "official_fee": "आधिकारिक शुल्क",
        "csc_fee": "कॉमन सर्विस सेंटर, अधिकतम",
        "days": "प्रक्रिया का समय",
        "verify": "स्थानीय स्तर पर जाँचें",
        "days_unit": "{n} {kind} दिन",
        "working": "कार्य",
        "calendar": "कैलेंडर",
        "submission": "जमा करना",
        "submitted_on": "जमा करने की तारीख",
        "reference": "संदर्भ (अंतिम 4 अंक)",
        "sources": "स्रोत",
        "checked": "जाँचा",
        "footer": "यह सारांश सहाय (AI सहायक, सरकारी माध्यम नहीं) की मदद से बना है। विवरण आधिकारिक स्रोत से पक्का करें।",
        "rs": "रु.",
    },
}


def _e(s: object) -> str:
    return html.escape(str(s))


def build_html(
    record: ServiceRecord,
    lang: Lang,
    ready: Readiness,
    jr: Journey,
    submission: dict[str, Any] | None,
    doc_names: dict[str, str],
) -> str:
    t = T[lang]
    name = record.name.get("hi" if lang == "hi" else "en") or record.id
    dept = record.department.get("hi" if lang == "hi" else "en") or ""
    p = [
        f"<h1>{_e(t['title'])}: {_e(name)}</h1>",
        f"<p>{_e(dept)}</p>",
        f"<p><b>{_e(t['own'])}</b></p>",
        "<dl>",
    ]
    for s in jr.steps:
        when = f" ({s.done_at.date().isoformat()})" if s.done and s.done_at else ""
        mark = t["done"] if s.done else t["todo"]
        p.append(f"<dt>{s.n}. {_e(t['steps'][s.n - 1])}</dt><dd>{_e(mark)}{_e(when)}</dd>")
    p.append("</dl>")
    if submission and (submission.get("submitted_on") or submission.get("reference_no_masked")):
        p.append(f"<h2>{_e(t['submission'])}</h2><dl>")
        if submission.get("submitted_on"):
            p.append(f"<dt>{_e(t['submitted_on'])}</dt><dd>{_e(submission['submitted_on'])}</dd>")
        if submission.get("reference_no_masked"):
            p.append(f"<dt>{_e(t['reference'])}</dt><dd>{_e(submission['reference_no_masked'])}</dd>")
        p.append("</dl>")
    p.append(
        f"<h2>{_e(t['checklist'])}</h2><p>{_e(t['ready'].format(done=ready.completed, total=ready.total))}</p><dl>"
    )
    for c in ready.checks:
        label = doc_names.get(c.doc_type, c.doc_type)
        req = t["required"] if c.required else t["optional"]
        p.append(
            f"<dt>{_e(label)} ({_e(req)})</dt><dd>{_e(t['status'][c.status.value])}, {_e(t['how'][c.evaluated.value])}</dd>"
        )
    p.append("</dl>")
    fs = fee_strip(record)
    fee = lambda v: f"{t['rs']} {v}" if v is not None else t["verify"]  # noqa: E731
    days = (
        t["days_unit"].format(
            n=fs.processing_days, kind=t[fs.day_type] if fs.day_type in ("working", "calendar") else ""
        )
        if fs.processing_days is not None
        else t["verify"]
    )
    p.append(
        f"<h2>{_e(t['fees'])}</h2><dl><dt>{_e(t['official_fee'])}</dt><dd>{_e(fee(fs.official_fee_inr))}</dd>"
        f"<dt>{_e(t['csc_fee'])}</dt><dd>{_e(fee(fs.csc_max_inr))}</dd><dt>{_e(t['days'])}</dt><dd>{_e(days)}</dd></dl>"
    )
    p.append(f"<h2>{_e(t['sources'])}</h2><ul>")
    for src in record.sources:
        d = src.date_checked.isoformat() if src.date_checked else t["verify"]
        p.append(f"<li>{_e(src.title)}, {_e(src.url)} ({_e(t['checked'])}: {_e(d)})</li>")
    p.append("</ul>")
    p.append(f"<div class='foot'>{_e(t['footer'])} {date.today().isoformat()}</div>")
    css = (
        CSS
        + " h2 { font-size: 12.5pt; color: #0f4c5c; margin: 14pt 0 4pt; } ul { padding-left: 14pt; font-size: 9.5pt; }"
    )
    return f"<!doctype html><html lang='{lang}'><head><meta charset='utf-8'><style>{css}</style></head><body>{''.join(p)}</body></html>"


def render_pdf(*args: Any, **kwargs: Any) -> bytes:
    from weasyprint import HTML

    return HTML(string=build_html(*args, **kwargs)).write_pdf()
