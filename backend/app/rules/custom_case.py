"""Services the user adds themselves, and the extra planning fields every case can carry. Pure, no I/O.

A custom service has no verified record in data/, so nothing here is a rule or a fact: the document list,
steps and timeline are what the user typed (or accepted from an AI suggestion and could edit). Readiness is
the user's own tick list, every item counted as "you said you have it", never as checked.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from app.rules.readiness import Check, CheckStatus, Evaluated, Readiness

CUSTOM_SERVICE_ID = "custom"
KEY_DATE_KINDS = ("deadline", "appointment", "other")


def custom_readiness(documents: list[dict[str, Any]]) -> Readiness:
    """The user's own document list as checklist rows. Every item is required, none is checked by Sahaay."""
    checks = [
        Check(
            doc_type=str(d["id"]),
            required=True,
            status=CheckStatus.OK if d.get("have") else CheckStatus.MISSING,
            evaluated=Evaluated.DECLARED if d.get("have") else Evaluated.NONE,
            matched_doc_type=str(d["id"]) if d.get("have") else None,
        )
        for d in documents
    ]
    return Readiness(CUSTOM_SERVICE_ID, sum(c.status is CheckStatus.OK for c in checks), len(checks), checks)


def merge_document_list(old: list[dict[str, Any]], names: list[str], new_id: Any) -> list[dict[str, Any]]:
    """A new list of document names keeps the tick (and id) of any name that was already there."""
    by_name = {str(d["name"]).casefold(): d for d in old}
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for n in names:
        key = n.casefold()
        if key in seen:
            continue
        seen.add(key)
        prev = by_name.get(key)
        if prev:
            out.append({"id": prev["id"], "name": n, "have": bool(prev.get("have"))})
        else:
            out.append({"id": new_id(), "name": n, "have": False})
    return out


@dataclass(frozen=True)
class KeyDate:
    on: date
    kind: str  # deadline | appointment | other
    label: str
    days_left: int  # negative once it has passed
    soon: bool  # within the next 7 days, today included
    passed: bool


def key_date(raw: dict[str, Any] | None, today: date) -> KeyDate | None:
    """A date the user set on a case (a last date, an office visit). Their own reminder, not official."""
    if not raw:
        return None
    try:
        on = date.fromisoformat(str(raw.get("on")))
    except ValueError:
        return None
    kind = raw.get("kind") if raw.get("kind") in KEY_DATE_KINDS else "other"
    left = (on - today).days
    return KeyDate(on, kind, str(raw.get("label") or ""), left, 0 <= left <= 7, left < 0)


def todo_counts(todos: list[dict[str, Any]]) -> tuple[int, int]:
    return sum(bool(t.get("done")) for t in todos), len(todos)
