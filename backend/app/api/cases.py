"""Cases and their confirmed documents.

A case is one user's progress on one service. Only fields the user has reviewed and confirmed are
stored, and every string is masked again here so a full ID number can never be saved. The upload
itself is never stored. Readiness is computed from the stored documents by a pure function.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import date
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.api.auth import CurrentUser
from app.rules.readiness import readiness

router = APIRouter()


class CaseIn(BaseModel):
    service_id: str


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
    return {**case, "documents": docs, "readiness": _readiness(request, case, docs)}


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
