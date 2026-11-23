"""Application readiness checklist. Pure function, no I/O.

Readiness is `completed_checks / total_checks` with each check listed and how it was evaluated.
It is never a probability of approval. Only the user's confirmed documents count.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import Any

from app.data.models import DocumentReq, ServiceRecord


class CheckStatus(StrEnum):
    OK = "ok"
    MISSING = "missing"
    EXPIRED = "expired"
    TOO_OLD = "too_old"  # issued before the scheme's `issued_after` date


class Evaluated(StrEnum):
    SCANNED = "scanned_and_confirmed"  # fields read from the upload and confirmed by the user
    DECLARED = "user_declared"  # the user said they have it; nothing was read
    NONE = "not_provided"


@dataclass(frozen=True)
class Check:
    doc_type: str
    required: bool
    status: CheckStatus
    evaluated: Evaluated
    matched_doc_type: str | None  # which of doc_type / alternatives satisfied it
    issue_date: date | None = None
    expires_on: date | None = None


@dataclass(frozen=True)
class Readiness:
    service_id: str
    completed: int
    total: int
    checks: list[Check]


def _add_months(d: date, months: int) -> date:
    y, m = divmod(d.month - 1 + months, 12)
    year, month = d.year + y, m + 1
    last = [
        31,
        29 if year % 4 == 0 and (year % 100 or year % 400 == 0) else 28,
        31,
        30,
        31,
        30,
        31,
        31,
        30,
        31,
        30,
        31,
    ][month - 1]
    return date(year, month, min(d.day, last))


def _parse(v: Any) -> date | None:
    if isinstance(v, date):
        return v
    try:
        return date.fromisoformat(v) if isinstance(v, str) else None
    except ValueError:
        return None


def _check(req: DocumentReq, docs: list[dict[str, Any]], today: date) -> Check:
    accepted = [req.doc_type, *req.alternatives]
    held = [d for d in docs if d["doc_type"] in accepted]
    if not held:
        return Check(req.doc_type, req.required, CheckStatus.MISSING, Evaluated.NONE, None)
    # Prefer a scanned document (it has facts we can check) over a declaration.
    held.sort(key=lambda d: 0 if d.get("fields") else 1)
    best = held[0]
    scanned = bool(best.get("fields"))
    issue = _parse(best.get("issue_date") or (best.get("fields") or {}).get("issue_date"))
    status, expires = CheckStatus.OK, None
    if scanned and issue is not None:
        if req.validity_months is not None:
            expires = _add_months(issue, req.validity_months)
            if today > expires:
                status = CheckStatus.EXPIRED
        if req.issued_after is not None and issue < req.issued_after:
            status = CheckStatus.TOO_OLD
    return Check(
        req.doc_type,
        req.required,
        status,
        Evaluated.SCANNED if scanned else Evaluated.DECLARED,
        best["doc_type"],
        issue,
        expires,
    )


def readiness(record: ServiceRecord, documents: list[dict[str, Any]], today: date) -> Readiness:
    checks = [_check(r, documents, today) for r in record.documents]
    required = [c for c in checks if c.required]
    return Readiness(
        service_id=record.id,
        completed=sum(c.status is CheckStatus.OK for c in required),
        total=len(required),
        checks=checks,
    )
