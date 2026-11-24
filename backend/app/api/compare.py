from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.api.auth import CurrentUser
from app.data.models import Lang, ServiceRecord
from app.graph.websearch import run_web_search
from app.rules.fees import fee_strip, is_stale
from app.safety.pii import mask

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


class WebCompareRequest(BaseModel):
    query: str = Field(min_length=2, max_length=80)
    language: Lang = "en"


@router.post("/compare/web")
def compare_web(body: WebCompareRequest, request: Request, user: CurrentUser) -> dict[str, Any]:
    """One unverified, web-found column for the Compare page. Never mixed into verified data."""
    llm = request.app.state.llm
    if not llm.web_enabled:
        raise HTTPException(503, "web_unavailable")
    name = mask(body.query).strip()
    question = (
        f"Summarise the Indian government service or scheme named '{name}': who can apply, "
        "the benefit, the main documents, and the fee, only if the results state them."
    )
    res = run_web_search(
        llm, request.app.state.catalog, question, body.language, user.id, date.today().isoformat()
    )
    if res.card is None:
        raise HTTPException(404, "no_answer")
    return {"name": name, "summary": res.text, "web": res.card}
