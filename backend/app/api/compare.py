from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from app.data.models import Lang, ServiceRecord
from app.rules.fees import fee_strip, is_stale

router = APIRouter()


def _row(rec: ServiceRecord, lang: Lang, stale: bool) -> dict[str, Any]:
    cites = {s.id: i + 1 for i, s in enumerate(rec.sources)}
    fee = fee_strip(rec)
    return {
        "id": rec.id,
        "name": rec.name.get(lang),
        "department": rec.department.get(lang),
        "status": rec.status,
        "stale": stale,
        "benefit": rec.benefit.amount_text.get(lang),
        "eligibility": [r.label.get(lang) for r in rec.eligibility.rules if r.required],
        "exclusions": [x.label.get(lang) for x in rec.exclusions],
        "documents": [
            {"doc_type": d.doc_type, "required": d.required, "alternatives": d.alternatives}
            for d in rec.documents
        ],
        "prerequisites": [p for p in rec.prerequisites],
        "fee_strip": {**fee.__dict__, "source_n": cites[rec.fees.source_ref]},
        "official_url": rec.apply.official_url,
        "citations": [
            {
                "n": cites[s.id],
                "title": s.title,
                "url": s.url,
                "publisher": s.publisher,
                "date_checked": s.date_checked.isoformat() if s.date_checked else None,
            }
            for s in rec.sources
        ],
    }


@router.get("/compare")
def compare(
    request: Request,
    ids: str = Query(description="Two or three service ids, comma separated"),
    lang: Lang = "en",
) -> dict[str, Any]:
    wanted = [i.strip() for i in ids.split(",") if i.strip()]
    if not 2 <= len(wanted) <= 3 or len(set(wanted)) != len(wanted):
        raise HTTPException(422, "Pick two or three different services")
    catalog = request.app.state.catalog
    served = {s.id: s for s in catalog.served()}
    missing = [i for i in wanted if i not in served]
    if missing:
        raise HTTPException(404, f"Unknown service: {', '.join(missing)}")
    from app.config import get_settings

    days = get_settings().freshness_days
    today = date.today()
    return {"services": [_row(served[i], lang, is_stale(served[i], today, days)) for i in wanted]}
