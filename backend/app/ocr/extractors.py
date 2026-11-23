"""Regex + label-proximity extractors. Pure functions over text.

Identity numbers are reduced to a masked form (last 4 only) here, before the result leaves this
module. Dates become ISO strings, money becomes integer rupees.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import date
from typing import Any

from app.safety.pii import mask_pii

DATE = re.compile(r"\b(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})\b")
AUTHORITY = re.compile(
    r"^.*\b(sdm|sub[- ]?divisional magistrate|district magistrate|tehsildar|revenue department|"
    r"deputy commissioner)\b.*$",
    re.I | re.M,
)


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip(" :-.,\t")


def _label_value(text: str, labels: str) -> str | None:
    m = re.search(rf"(?im)^\s*(?:{labels})\s*[:\-]\s*(.+)$", text)
    return _clean(m.group(1)) if m else None


def _name(text: str) -> str | None:
    value = _label_value(
        text,
        r"name of (?:the )?(?:applicant|holder|student|candidate|account holder)|"
        r"account holder|applicant|name",
    )
    if not value or len(value) > 60 or any(c.isdigit() for c in value):
        return None
    return value


def _iso(d: str, m: str, y: str) -> str | None:
    try:
        return date(int(y), int(m), int(d)).isoformat()
    except ValueError:
        return None


def _issue_date(text: str) -> str | None:
    labelled = re.search(
        r"(?i)(?:date of issue|issued on|issue date|dated?)\s*[:\-]?\s*"
        r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})",
        text,
    )
    if labelled:
        return _iso(*labelled.groups())
    m = DATE.search(text)
    return _iso(*m.groups()) if m else None


def income_certificate(text: str, masked: str) -> dict[str, Any]:
    income = re.search(
        r"(?i)(?:annual|yearly|total)\s+(?:family\s+)?income[^\d\n]{0,40}?(?:rs\.?|₹|inr)?\s*([\d,]{4,})",
        text,
    )
    authority = AUTHORITY.search(text)
    return {
        "holder_name": _name(text),
        "annual_income_inr": int(income.group(1).replace(",", "")) if income else None,
        "issue_date": _issue_date(text),
        "issuing_authority": _clean(authority.group(0)) if authority else None,
    }


def aadhaar(text: str, masked: str) -> dict[str, Any]:
    found = [f for f in mask_pii(text)[1] if f.kind == "aadhaar"]
    return {"aadhaar_masked": f"XXXX XXXX {found[0].last4}" if found else None}


def pan(text: str, masked: str) -> dict[str, Any]:
    found = [f for f in mask_pii(text)[1] if f.kind == "pan"]
    return {"pan_masked": f"XXXXXX{found[0].last4}" if found else None}


def bank_passbook(text: str, masked: str) -> dict[str, Any]:
    acct = re.search(r"(?i)(?:a/?c|account)\s*(?:no|number|num)?\.?\s*[:#\-]?\s*(\d[\d ]{7,20}\d)", text)
    # Tesseract often reads the zero in the 5th place as the letter O, so accept both and normalise.
    ifsc = re.search(r"\b([A-Z]{4})[0O]([A-Z0-9]{6})\b", text)
    digits = re.sub(r"\s", "", acct.group(1)) if acct else ""
    return {
        "holder_name": _name(text),
        "account_masked": "X" * (len(digits) - 4) + digits[-4:] if 9 <= len(digits) <= 18 else None,
        "ifsc": f"{ifsc.group(1)}0{ifsc.group(2)}" if ifsc else None,
    }


def marksheet(text: str, masked: str) -> dict[str, Any]:
    m = re.search(r"(?i)(?:percentage|percent|aggregate)[^\d\n]{0,20}(\d{1,3}(?:\.\d+)?)\s*%?", text)
    pct = float(m.group(1)) if m else None
    return {"holder_name": _name(text), "percentage": pct if pct is not None and pct <= 100 else None}


EXTRACTORS: dict[str, Callable[[str, str], dict[str, Any]]] = {
    "income_certificate": income_certificate,
    "aadhaar": aadhaar,
    "pan": pan,
    "bank_passbook": bank_passbook,
    "marksheet": marksheet,
}
