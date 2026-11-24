from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.api.auth import CurrentUser
from app.data.loader import PROFILE_KEYS
from app.safety.pii import mask_pii

router = APIRouter()


class FactIn(BaseModel):
    key: str
    value: Any
    source: Literal["user_said", "form_input", "document_extracted"] = "user_said"
    confirmed: bool = True
    consent: bool = False  # facts are saved only after the user agrees


class CorrectionIn(BaseModel):
    service_id: str
    note: str = Field(min_length=3, max_length=1000)


@router.get("/me/facts")
def list_facts(user: CurrentUser, request: Request) -> list[dict[str, Any]]:
    return request.app.state.store.list_facts(user.id)


@router.put("/me/facts")
def save_fact(body: FactIn, user: CurrentUser, request: Request) -> dict[str, bool]:
    if not body.consent:
        raise HTTPException(400, "Consent is required before saving personal details")
    if body.key not in PROFILE_KEYS:
        raise HTTPException(422, f"Unknown profile key '{body.key}'")
    if isinstance(body.value, str) and mask_pii(body.value)[1]:
        raise HTTPException(422, "Identity numbers are never saved")
    request.app.state.store.upsert_fact(user.id, body.key, body.value, body.source, body.confirmed)
    return {"ok": True}


@router.get("/me/data")
def export_my_data(user: CurrentUser, request: Request) -> dict[str, Any]:
    """Everything stored for this user, as it is stored (already masked). For the privacy page."""
    store = request.app.state.store
    cases = []
    for c in store.list_cases(user.id):
        cid = c["id"]
        cases.append(
            {
                "id": cid,
                "service_id": c["service_id"],
                "created_at": c.get("created_at"),
                "documents": store.list_documents(user.id, cid),
                "steps": store.list_events(user.id, cid),
                "submission": store.get_submission(user.id, cid),
                "notes": (c.get("state") or {}).get("notes", []),
                "follow_up_days": (c.get("state") or {}).get("follow_up_days"),
            }
        )
    return {"facts": store.list_facts(user.id), "cases": cases}


@router.delete("/me/data")
def delete_my_data(user: CurrentUser, request: Request) -> dict[str, bool]:
    request.app.state.store.delete_user_data(user.id)
    return {"ok": True}


@router.post("/reports/incorrect", status_code=201)
def report_incorrect(body: CorrectionIn, user: CurrentUser, request: Request) -> dict[str, bool]:
    if body.service_id not in request.app.state.catalog.services:
        raise HTTPException(404, "Unknown service")
    note, _ = mask_pii(body.note)  # reports never keep identity numbers
    request.app.state.store.add_correction(user.id, body.service_id, note)
    return {"ok": True}
