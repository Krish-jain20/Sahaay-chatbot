"""What a case needs next. Pure functions, no I/O.

Everything here is computed from the user's own records (documents they confirmed, steps they marked,
the date they say they submitted) and the scheme data. Nothing reads or implies live government status.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from app.rules.journey import Journey
from app.rules.readiness import CheckStatus, Readiness

MAX_FOLLOW_UP_DAYS = 365


@dataclass(frozen=True)
class FollowUp:
    days: int | None  # the user's own reminder, or the scheme's published timeline when they set none
    user_set: bool
    due_on: date | None
    due: bool  # the reminder date has passed and the user has not recorded a reply
    days_since_submitted: int | None
    reply_received: bool


@dataclass(frozen=True)
class Overview:
    next_action: str  # an i18n key on the frontend, never free text
    missing: list[str]  # required documents that are missing, expired or too old
    docs_ready: int
    docs_total: int
    steps_done: int
    steps_total: int
    follow_up: FollowUp


def merge_documents(docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One document per type across all of a user's cases: a scanned one beats a declaration, then newest."""
    best: dict[str, dict[str, Any]] = {}
    for d in docs:
        cur = best.get(d["doc_type"])
        key = (bool(d.get("fields")), str(d.get("confirmed_at") or ""))
        if cur is None or key > (bool(cur.get("fields")), str(cur.get("confirmed_at") or "")):
            best[d["doc_type"]] = d
    return list(best.values())


def _parse(v: Any) -> date | None:
    if isinstance(v, date):
        return v
    try:
        return date.fromisoformat(v) if isinstance(v, str) else None
    except ValueError:
        return None


def follow_up(
    submitted_on: Any, user_days: int | None, sla_days: int | None, reply_received: bool, today: date
) -> FollowUp:
    days = user_days if user_days is not None else sla_days
    sub = _parse(submitted_on)
    if sub is None:
        return FollowUp(days, user_days is not None, None, False, None, reply_received)
    due_on = sub + timedelta(days=days) if days is not None else None
    due = due_on is not None and today >= due_on and not reply_received
    return FollowUp(days, user_days is not None, due_on, due, (today - sub).days, reply_received)


def overview(
    ready: Readiness,
    j: Journey,
    submission: dict[str, Any] | None,
    state: dict[str, Any],
    sla_days: int | None,
    today: date,
) -> Overview:
    missing = [c.doc_type for c in ready.checks if c.required and c.status is not CheckStatus.OK]
    done = {s.n for s in j.steps if s.done}
    fu = follow_up(
        (submission or {}).get("submitted_on"),
        state.get("follow_up_days"),
        sla_days,
        bool(state.get("reply_received")),
        today,
    )
    if 4 in done and fu.due:
        action = "follow_up"
    elif 1 not in done:
        action = "check_eligibility"
    elif missing and 2 not in done:
        action = "add_documents"
    elif 2 not in done:
        action = "confirm_documents"
    elif 3 not in done:
        action = "fill_form"
    elif 4 not in done:
        action = "submit"
    elif 5 not in done:
        action = "save_reference"
    elif fu.reply_received:
        action = "done"
    else:
        action = "wait"
    return Overview(action, missing, ready.completed, ready.total, len(done), len(j.steps), fu)
