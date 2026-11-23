"""Fee strip. Null values become VERIFY_LOCALLY; never a guess."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.data.models import ServiceRecord

VERIFY_LOCALLY = None  # rendered as the "Verify locally" i18n string by the client


@dataclass(frozen=True)
class FeeStrip:
    official_fee_inr: int | None
    csc_max_inr: int | None
    processing_days: int | None
    day_type: str
    source_ref: str


def fee_strip(record: ServiceRecord) -> FeeStrip:
    return FeeStrip(
        official_fee_inr=record.fees.official_online_inr,
        csc_max_inr=record.fees.csc_max_inr,
        processing_days=record.timeline.sla_days,
        day_type=record.timeline.day_type,
        source_ref=record.fees.source_ref,
    )


def is_stale(record: ServiceRecord, today: date, freshness_days: int) -> bool:
    """A record is stale if no source has been checked within the freshness window."""
    checked = [s.date_checked for s in record.sources if s.date_checked]
    if not checked:
        return True
    return (today - max(checked)).days > freshness_days
