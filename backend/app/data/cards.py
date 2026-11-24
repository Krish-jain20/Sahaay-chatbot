"""Service cards for the Compare page: the verified records and the directory, in one shape.

Every line carries `source_n`, the number of a citation on the same card. Missing facts are null and
the client shows "Verify locally".
"""

from __future__ import annotations

from datetime import date
from typing import Any

from app.data.models import InfoFact, InfoService, Lang, ServiceRecord, Source

DOC_LABELS: dict[str, dict[str, str]] = {
    "aadhaar": {"en": "Aadhaar", "hi": "आधार", "hn": "Aadhaar"},
    "address_proof": {"en": "Address proof", "hi": "पते का प्रमाण", "hn": "Address proof"},
    "age_proof": {"en": "Age proof", "hi": "उम्र का प्रमाण", "hn": "Age proof"},
    "bank_passbook": {"en": "Bank passbook", "hi": "बैंक पासबुक", "hn": "Bank passbook"},
    "caste_certificate": {"en": "Caste certificate", "hi": "जाति प्रमाण पत्र", "hn": "Caste certificate"},
    "domicile_certificate": {
        "en": "Domicile certificate",
        "hi": "निवास प्रमाण पत्र",
        "hn": "Domicile certificate",
    },
    "expenditure_proof": {
        "en": "Proof of monthly expenditure",
        "hi": "मासिक खर्च का प्रमाण",
        "hn": "Monthly kharche ka proof",
    },
    "income_certificate": {"en": "Income certificate", "hi": "आय प्रमाण पत्र", "hn": "Income certificate"},
    "income_proof": {
        "en": "Income proof (salary slip or similar)",
        "hi": "आय का प्रमाण (वेतन पर्ची आदि)",
        "hn": "Income proof (salary slip aadi)",
    },
    "income_self_declaration": {
        "en": "Income self-declaration",
        "hi": "आय का स्व-घोषणा पत्र",
        "hn": "Income self-declaration",
    },
    "passport_photo": {"en": "Passport size photo", "hi": "पासपोर्ट साइज़ फ़ोटो", "hn": "Passport size photo"},
    "self_declaration": {
        "en": "Self-declaration in the prescribed format",
        "hi": "निर्धारित प्रारूप में स्व-घोषणा",
        "hn": "Prescribed format mein self-declaration",
    },
    "study_gap_affidavit": {
        "en": "Affidavit for a gap in studies",
        "hi": "पढ़ाई में अंतराल का शपथ पत्र",
        "hn": "Padhai mein gap ka affidavit",
    },
}
IF_APPLICABLE = {"en": "(if applicable)", "hi": "(यदि लागू हो)", "hn": "(agar laagu ho)"}
NO_FEE = {"en": "No fee.", "hi": "कोई शुल्क नहीं।", "hn": "Koi fee nahi."}
DAYS = {"en": "{n} days.", "hi": "{n} दिन।", "hn": "{n} din."}
WORKING_DAYS = {"en": "{n} working days.", "hi": "{n} कार्य दिवस।", "hn": "{n} working days."}


def _cites(sources: list[Source]) -> tuple[dict[str, int], list[dict[str, Any]]]:
    n = {s.id: i + 1 for i, s in enumerate(sources)}
    out = [
        {
            "n": n[s.id],
            "title": s.title,
            "url": s.url,
            "publisher": s.publisher,
            "date_checked": s.date_checked.isoformat() if s.date_checked else None,
        }
        for s in sources
    ]
    return n, out


def _fact(text: str | None, ref: str, n: dict[str, int]) -> dict[str, Any] | None:
    return {"text": text, "source_n": n[ref]} if text else None


def _lines(items: list[InfoFact], lang: Lang, n: dict[str, int]) -> list[dict[str, Any]]:
    return [{"text": f.text.get(lang), "source_n": n[f.source_ref]} for f in items]


def _l(d: dict[str, str], lang: Lang) -> str:
    return d.get(lang) or d["en"]


def _checked_on(sources: list[Source]) -> str | None:
    days = [s.date_checked for s in sources if s.date_checked]
    return max(days).isoformat() if days else None


def _stale(sources: list[Source], today: date, freshness_days: int) -> bool:
    days = [s.date_checked for s in sources if s.date_checked]
    return not days or (today - max(days)).days > freshness_days


def info_card(info: InfoService, lang: Lang, today: date, freshness_days: int) -> dict[str, Any]:
    n, cites = _cites(info.sources)
    return {
        "id": info.id,
        "kind": "directory",
        "name": info.name.get(lang),
        "department": info.department.get(lang),
        "summary": info.summary.get(lang),
        "benefit": _fact(info.benefit.text.get(lang), info.benefit.source_ref, n) if info.benefit else None,
        "who": _lines(info.who, lang, n),
        "not_if": [],
        "documents": _lines(info.documents, lang, n),
        "fee": _fact(info.fee.text.get(lang), info.fee.source_ref, n) if info.fee else None,
        "time": _fact(info.time.text.get(lang), info.time.source_ref, n) if info.time else None,
        "steps": _lines(info.steps, lang, n),
        "apply_url": info.apply_url,
        "citations": cites,
        "checked_on": _checked_on(info.sources),
        "stale": _stale(info.sources, today, freshness_days),
        "notes": info.notes,
    }


def record_card(rec: ServiceRecord, lang: Lang, today: date, freshness_days: int) -> dict[str, Any]:
    n, cites = _cites(rec.sources)
    fee_text: str | None = None
    fees = rec.fees
    note = fees.notes.get(lang)
    if fees.official_online_inr is not None:
        fee_text = _l(NO_FEE, lang) if fees.official_online_inr == 0 else f"₹{fees.official_online_inr:,}."
        if note:
            fee_text += f" {note}"
    elif note:
        fee_text = note
    time_text: str | None = None
    if rec.timeline.sla_days is not None:
        table = WORKING_DAYS if rec.timeline.day_type == "working" else DAYS
        time_text = _l(table, lang).format(n=rec.timeline.sla_days)
    docs = []
    for d in rec.documents:
        label = _l(DOC_LABELS[d.doc_type], lang) if d.doc_type in DOC_LABELS else d.doc_type.replace("_", " ")
        docs.append(
            {
                "text": label if d.required else f"{label} {_l(IF_APPLICABLE, lang)}",
                "source_n": n[d.source_ref],
            }
        )
    return {
        "id": rec.id,
        "kind": "record",
        "name": rec.name.get(lang),
        "department": rec.department.get(lang),
        "summary": rec.summary.get(lang),
        "benefit": _fact(rec.benefit.amount_text.get(lang), rec.benefit.source_ref, n),
        "who": [
            {"text": r.label.get(lang), "source_n": n[r.source_ref]}
            for r in rec.eligibility.rules
            if r.required
        ],
        "not_if": [{"text": x.label.get(lang), "source_n": n[x.source_ref]} for x in rec.exclusions],
        "documents": docs,
        "fee": _fact(fee_text, fees.source_ref, n),
        "time": _fact(time_text, rec.timeline.source_ref, n),
        "steps": [{"text": s.text.get(lang), "source_n": n[s.source_ref]} for s in rec.apply.steps],
        "apply_url": rec.apply.official_url,
        "citations": cites,
        "checked_on": _checked_on(rec.sources),
        "stale": _stale(rec.sources, today, freshness_days),
        "notes": None,
    }


def all_cards(catalog: Any, lang: Lang, today: date, freshness_days: int) -> list[dict[str, Any]]:
    cards = [record_card(r, lang, today, freshness_days) for r in catalog.served()]
    cards += [info_card(i, lang, today, freshness_days) for i in catalog.directory.values()]
    return cards
