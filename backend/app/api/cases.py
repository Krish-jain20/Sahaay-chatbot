"""Cases and their confirmed documents.

A case is one user's progress on one service. Only fields the user has reviewed and confirmed are
stored, and every string is masked again here so a full ID number can never be saved. The upload
itself is never stored. Readiness is computed from the stored documents by a pure function.
"""

from __future__ import annotations

import re
from dataclasses import asdict
from datetime import date
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.api.auth import CurrentUser
from app.rules.journey import STEP_KEYS, journey
from app.rules.readiness import readiness

router = APIRouter()


class CaseIn(BaseModel):
    service_id: str


class StepIn(BaseModel):
    step: int = Field(ge=1, le=len(STEP_KEYS))
    submitted_on: date | None = None  # step 4
    reference: str | None = Field(default=None, max_length=40)  # step 5; only the last 4 characters are kept


class DocumentIn(BaseModel):
    doc_type: str
    fields: dict[str, str | int | float | None] = Field(default_factory=dict)
    self_declared: bool = False  # "I have this", nothing was read


def _readiness(request: Request, case: dict[str, Any], documents: list[dict[str, Any]]) -> dict[str, Any]:
    record = request.app.state.catalog.services[case["service_id"]]
    result = readiness(record, documents, date.today())
    return jsonable(asdict(result))


def jsonable(v: Any) -> Any:
    if isinstance(v, dict):
        return {k: jsonable(x) for k, x in v.items()}
    if isinstance(v, list):
        return [jsonable(x) for x in v]
    if isinstance(v, date):
        return v.isoformat()
    return getattr(v, "value", v)


@router.post("/cases", status_code=201)
def create_case(body: CaseIn, user: CurrentUser, request: Request) -> dict[str, Any]:
    if body.service_id not in request.app.state.catalog.services:
        raise HTTPException(404, "Unknown service")
    store = request.app.state.store
    existing = next((c for c in store.list_cases(user.id) if c["service_id"] == body.service_id), None)
    return existing or store.create_case(user.id, body.service_id)


@router.get("/cases")
def list_cases(user: CurrentUser, request: Request) -> list[dict[str, Any]]:
    return request.app.state.store.list_cases(user.id)


@router.get("/cases/{case_id}")
def get_case(case_id: str, user: CurrentUser, request: Request) -> dict[str, Any]:
    store = request.app.state.store
    case = store.get_case(user.id, case_id)
    if case is None:
        raise HTTPException(404, "Case not found")
    docs = store.list_documents(user.id, case_id)
    return {
        **case,
        "documents": docs,
        "readiness": _readiness(request, case, docs),
        **_journey_view(store, user.id, case_id),
    }


def _journey_view(store: Any, user_id: str, case_id: str) -> dict[str, Any]:
    j = journey(store.list_events(user_id, case_id))
    return {
        "journey": jsonable(
            {
                "label": "your_own_progress",  # user-recorded steps only, never government status
                "steps": [asdict(s) for s in j.steps],
                "current": j.current,
                "completed": j.completed,
            }
        ),
        "submission": store.get_submission(user_id, case_id),
    }


def mask_reference(raw: str) -> str:
    """Keep only the last 4 letters/digits of a reference number."""
    chars = re.sub(r"[^A-Za-z0-9]", "", raw)
    if len(chars) < 4:
        raise HTTPException(422, "Reference number is too short")
    return "XXXX" + chars[-4:].upper()


@router.post("/cases/{case_id}/steps", status_code=201)
def record_step(case_id: str, body: StepIn, user: CurrentUser, request: Request) -> dict[str, Any]:
    store = request.app.state.store
    if store.get_case(user.id, case_id) is None:
        raise HTTPException(404, "Case not found")
    if body.submitted_on and body.submitted_on > date.today():
        raise HTTPException(422, "Submission date cannot be in the future")
    reference = None
    if body.step == 5:
        if not body.reference:
            raise HTTPException(422, "Reference number is required for this step")
        reference = mask_reference(body.reference)
    store.add_event(user.id, case_id, body.step, None)
    if reference or body.submitted_on:
        store.save_submission(
            user.id, case_id, reference, body.submitted_on.isoformat() if body.submitted_on else None
        )
    return _journey_view(store, user.id, case_id)


@router.delete("/cases/{case_id}/steps/{step}")
def undo_step(case_id: str, step: int, user: CurrentUser, request: Request) -> dict[str, Any]:
    store = request.app.state.store
    if not 1 <= step <= len(STEP_KEYS) or not store.delete_event(user.id, case_id, step):
        raise HTTPException(404, "Case or step not found")
    return _journey_view(store, user.id, case_id)


@router.post("/cases/{case_id}/documents", status_code=201)
def save_document(case_id: str, body: DocumentIn, user: CurrentUser, request: Request) -> dict[str, Any]:
    from app.safety.pii import mask_pii

    store = request.app.state.store
    case = store.get_case(user.id, case_id)
    if case is None:
        raise HTTPException(404, "Case not found")
    record = request.app.state.catalog.services[case["service_id"]]
    listed = {t for r in record.documents for t in (r.doc_type, *r.alternatives)}
    spec = request.app.state.doc_types.get(body.doc_type)
    if body.doc_type not in listed or (spec is None and not body.self_declared):
        raise HTTPException(422, "Unknown document type for this service")
    allowed = set(spec["extract_fields"]) if spec else set()
    unknown = set(body.fields) - allowed
    if unknown:
        raise HTTPException(422, f"Unknown fields: {', '.join(sorted(unknown))}")
    if body.self_declared and body.fields:
        raise HTTPException(422, "A declared document has no fields")
    if not body.self_declared and spec:
        missing = [f for f in spec["required_fields"] if body.fields.get(f) in (None, "")]
        if missing:
            raise HTTPException(422, f"Missing required fields: {', '.join(missing)}")
    fields = {
        k: (mask_pii(v)[0] if isinstance(v, str) else v)
        for k, v in body.fields.items()
        if v not in (None, "")
    }
    issue = fields.get("issue_date")
    if issue is not None:
        try:
            date.fromisoformat(str(issue))
        except ValueError as e:
            raise HTTPException(422, "issue_date must be YYYY-MM-DD") from e
    doc = store.save_document(user.id, case_id, body.doc_type, fields, str(issue) if issue else None)
    docs = store.list_documents(user.id, case_id)
    return {"document": doc, "readiness": _readiness(request, case, docs)}


@router.get("/cases/{case_id}/summary.pdf")
def summary_pdf(case_id: str, user: CurrentUser, request: Request, lang: str = "en") -> Response:
    from app.pdf import summary

    store = request.app.state.store
    case = store.get_case(user.id, case_id)
    if case is None:
        raise HTTPException(404, "Case not found")
    record = request.app.state.catalog.services[case["service_id"]]
    docs = store.list_documents(user.id, case_id)
    lang_ = "hi" if lang == "hi" else "en"
    doc_names = {
        d["id"]: (d["name"].get("hi") if lang_ == "hi" else d["name"].get("en")) or d["id"]
        for d in request.app.state.doc_types.values()
    }
    try:
        pdf = summary.render_pdf(
            record,
            lang_,
            readiness(record, docs, date.today()),
            journey(store.list_events(user.id, case_id)),
            store.get_submission(user.id, case_id),
            doc_names,
        )
    except Exception as e:  # noqa: BLE001 - WeasyPrint raises many types when system libraries are missing
        raise HTTPException(503, "pdf_unavailable") from e
    return Response(
        pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="sahaay-case-summary.pdf"',
            "Cache-Control": "no-store",
        },
    )
