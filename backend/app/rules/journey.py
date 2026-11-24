"""Application journey: five steps the user records themselves. Pure function, no I/O.

This is the user's own progress. Nothing here reads or implies live government status.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

STEP_KEYS = ("eligibility_checked", "documents_verified", "form_filled", "submitted", "reference_saved")


@dataclass(frozen=True)
class JourneyStep:
    n: int  # 1..5
    key: str
    done: bool
    done_at: datetime | None


@dataclass(frozen=True)
class Journey:
    steps: list[JourneyStep]
    current: int | None  # first step not done, None when all five are done
    completed: int


def _at(v: Any) -> datetime | None:
    if isinstance(v, datetime):
        return v
    try:
        return datetime.fromisoformat(v) if isinstance(v, str) else None
    except ValueError:
        return None


def journey(events: list[dict[str, Any]]) -> Journey:
    first: dict[int, datetime | None] = {}
    for e in sorted(events, key=lambda e: str(e.get("at", ""))):
        first.setdefault(int(e["step"]), _at(e.get("at")))
    steps = [JourneyStep(i + 1, k, (i + 1) in first, first.get(i + 1)) for i, k in enumerate(STEP_KEYS)]
    current = next((s.n for s in steps if not s.done), None)
    return Journey(steps, current, sum(s.done for s in steps))
