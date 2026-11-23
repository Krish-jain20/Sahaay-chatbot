"""PII masking. Runs on input, before logs, and before any model call.

Keeps only the last 4 characters. Aadhaar is matched only when the Verhoeff
checksum passes, so ordinary 12-digit numbers are left alone. Bank account
numbers are matched only next to an account keyword, so amounts are left alone.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
]
_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
]


def verhoeff_valid(digits: str) -> bool:
    c = 0
    for i, ch in enumerate(reversed(digits)):
        c = _D[c][_P[i % 8][int(ch)]]
    return c == 0


_AADHAAR = re.compile(r"(?<![\d])([2-9]\d{3})[ -]?(\d{4})[ -]?(\d{4})(?![\d])")
_PAN = re.compile(r"(?<![A-Za-z0-9])([A-Za-z]{5}\d{4}[A-Za-z])(?![A-Za-z0-9])")
_PHONE = re.compile(r"(?<![\d+])(?:\+91[ -]?|0)?([6-9]\d{4})[ -]?(\d{5})(?![\d])")
_ACCOUNT = re.compile(
    r"((?:a/?c|acct|account|khata|खाता)(?:\s*(?:no|number|num|नंबर|संख्या))?\.?\s*[:#-]?\s*)(\d[\d -]{7,20}\d)",
    re.I,
)


@dataclass(frozen=True)
class Finding:
    kind: str
    last4: str


def _mask(value: str, prefix: str = "X") -> str:
    digits = re.sub(r"[ -]", "", value)
    return prefix * (len(digits) - 4) + digits[-4:]


def mask_pii(text: str) -> tuple[str, list[Finding]]:
    findings: list[Finding] = []

    def aadhaar(m: re.Match[str]) -> str:
        digits = "".join(m.groups())
        if not verhoeff_valid(digits):
            return m.group(0)
        findings.append(Finding("aadhaar", digits[-4:]))
        return f"XXXX XXXX {digits[-4:]}"

    def pan(m: re.Match[str]) -> str:
        v = m.group(1)
        if not re.fullmatch(r"[A-Z]{5}\d{4}[A-Z]", v.upper()) or v.upper()[3] not in "PCHFATBLJG":
            return m.group(0)
        findings.append(Finding("pan", v[-4:].upper()))
        return "XXXXXX" + v[-4:].upper()

    def phone(m: re.Match[str]) -> str:
        digits = "".join(m.groups())
        findings.append(Finding("phone", digits[-4:]))
        return _mask(digits)

    def account(m: re.Match[str]) -> str:
        digits = re.sub(r"[ -]", "", m.group(2))
        if not 9 <= len(digits) <= 18:
            return m.group(0)
        findings.append(Finding("bank_account", digits[-4:]))
        return m.group(1) + _mask(digits)

    text = _ACCOUNT.sub(account, text)
    text = _AADHAAR.sub(aadhaar, text)
    text = _PAN.sub(pan, text)
    text = _PHONE.sub(phone, text)
    return text, findings


def mask(text: str) -> str:
    return mask_pii(text)[0]
