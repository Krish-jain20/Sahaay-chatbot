"""Cases and their confirmed documents.

A case is one user's progress on one service. Only fields the user has reviewed and confirmed are
stored, and every string is masked again here so a full ID number can never be saved. The upload
itself is never stored. Readiness is computed from the stored documents by a pure function.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import asdict
from datetime import UTC, date, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.api.auth import CurrentUser
from app.rules.case_overview import MAX_FOLLOW_UP_DAYS, merge_documents, overview
from app.rules.journey import STEP_KEYS, journey
from app.rules.readiness import readiness
from app.safety.allowlist import is_allowed

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


class CasePatch(BaseModel):
    follow_up_days: int | None = Field(default=None, ge=1, le=MAX_FOLLOW_UP_DAYS)
    clear_follow_up: bool = False  # go back to the scheme's published timeline
    reply_received: bool | None = None


class NoteIn(BaseModel):
    text: str = Field(min_length=1, max_length=300)


MAX_NOTES = 50

# The draft that fits each launch service when it is late or refused. RTI and CPGRAMS are always offered.
DRAFT_FOR_SERVICE = {
    "delhi-income-certificate": "certificate_delay",
    "delhi-merit-scholarship-scstobc": "scholarship_delay",
    "delhi-old-age-pension": "pension_delay",
}


def _all_documents(store: Any, user_id: str) -> list[dict[str, Any]]:
    """Documents the user already added, in any case. One per type, so one upload ticks every case."""
    docs: list[dict[str, Any]] = []
    for c in store.list_cases(user_id):
        docs.extend(store.list_documents(user_id, c["id"]))
    return merge_documents(docs)


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


@router.get("/cases/overview")
def cases_overview(user: CurrentUser, request: Request, lang: str = "en") -> list[dict[str, Any]]:
    """All of the user's cases as cards, with documents counted from everything they have added."""
    store = request.app.state.store
    docs = _all_documents(store, user.id)
    return [_case_view(request, c, docs, lang) for c in store.list_cases(user.id)]


@router.patch("/cases/{case_id}")
def patch_case(
    case_id: str, body: CasePatch, user: CurrentUser, request: Request, lang: str = "en"
) -> dict[str, Any]:
    store = request.app.state.store
    case = store.get_case(user.id, case_id)
    if case is None:
        raise HTTPException(404, "Case not found")
    state = dict(case.get("state") or {})
    if body.clear_follow_up:
        state.pop("follow_up_days", None)
    elif body.follow_up_days is not None:
        state["follow_up_days"] = body.follow_up_days
    if body.reply_received is not None:
        state["reply_received"] = body.reply_received
    store.update_case_state(user.id, case_id, state)
    case["state"] = state
    return _case_view(request, case, _all_documents(store, user.id), lang)


@router.post("/cases/{case_id}/notes", status_code=201)
def add_note(
    case_id: str, body: NoteIn, user: CurrentUser, request: Request, lang: str = "en"
) -> dict[str, Any]:
    from app.safety.pii import mask_pii

    store = request.app.state.store
    case = store.get_case(user.id, case_id)
    if case is None:
        raise HTTPException(404, "Case not found")
    state = dict(case.get("state") or {})
    notes = list(state.get("notes", []))
    if len(notes) >= MAX_NOTES:
        raise HTTPException(422, "Too many notes")
    text, _ = mask_pii(body.text.strip())  # identity numbers are never kept, even in a note
    if not text:
        raise HTTPException(422, "Note is empty")
    notes.append({"id": uuid.uuid4().hex[:12], "at": datetime.now(UTC).isoformat(), "text": text})
    state["notes"] = notes
    store.update_case_state(user.id, case_id, state)
    case["state"] = state
    return _case_view(request, case, _all_documents(store, user.id), lang)


@router.delete("/cases/{case_id}/notes/{note_id}")
def delete_note(
    case_id: str, note_id: str, user: CurrentUser, request: Request, lang: str = "en"
) -> dict[str, Any]:
    store = request.app.state.store
    case = store.get_case(user.id, case_id)
    if case is None:
        raise HTTPException(404, "Case not found")
    state = dict(case.get("state") or {})
    state["notes"] = [n for n in state.get("notes", []) if n["id"] != note_id]
    store.update_case_state(user.id, case_id, state)
    case["state"] = state
    return _case_view(request, case, _all_documents(store, user.id), lang)


@router.delete("/cases/{case_id}")
def delete_case(case_id: str, user: CurrentUser, request: Request) -> dict[str, bool]:
    if not request.app.state.store.delete_case(user.id, case_id):
        raise HTTPException(404, "Case not found")
    return {"ok": True}


@router.get("/cases/{case_id}")
def get_case(case_id: str, user: CurrentUser, request: Request, lang: str = "en") -> dict[str, Any]:
    store = request.app.state.store
    case = store.get_case(user.id, case_id)
    if case is None:
        raise HTTPException(404, "Case not found")
    docs = _all_documents(store, user.id)
    return {
        **_case_view(request, case, docs, lang),
        "documents": store.list_documents(user.id, case_id),
        **_journey_view(store, user.id, case_id),
    }


def _case_view(
    request: Request, case: dict[str, Any], docs: list[dict[str, Any]], lang: str
) -> dict[str, Any]:
    """Everything the My cases page shows for one case, computed from the user's own records."""
    store = request.app.state.store
    user_id = case["user_id"]
    record = request.app.state.catalog.services[case["service_id"]]
    ready = readiness(record, docs, date.today())
    j = journey(store.list_events(user_id, case["id"]))
    submission = store.get_submission(user_id, case["id"])
    state = case.get("state") or {}
    ov = overview(ready, j, submission, state, record.timeline.sla_days, date.today())
    lang_ = lang if lang in ("en", "hi", "hn") else "en"
    return {
        "id": case["id"],
        "service_id": case["service_id"],
        "service_name": record.name.get(lang_),
        "department": record.department.get(lang_),
        "created_at": case.get("created_at"),
        "readiness": jsonable(asdict(ready)),
        "journey": jsonable(
            {
                "label": "your_own_progress",
                "steps": [asdict(s) for s in j.steps],
                "current": j.current,
                "completed": j.completed,
            }
        ),
        "submission": submission,
        "overview": jsonable(asdict(ov)),
        "notes": state.get("notes", []),
        "steps_text": [{"n": st.n, "text": st.text.get(lang_)} for st in record.apply.steps],
        "prerequisites": [
            {"id": p, "name": request.app.state.catalog.services[p].name.get(lang_)}
            for p in record.prerequisites
        ],
        "links": _links(request, record, lang_),
    }


def _links(request: Request, record: Any, lang: str) -> dict[str, Any]:
    """Official links only: each host must be on the allowlist. Nothing is guessed."""
    allow = request.app.state.catalog.allowlist
    sources = [
        {
            "title": s.title,
            "url": s.url,
            "publisher": s.publisher,
            "date_checked": s.date_checked.isoformat() if s.date_checked else None,
        }
        for s in record.sources
        if is_allowed(s.url, allow)
    ]
    official = (
        record.apply.official_url
        if record.apply.official_url and is_allowed(record.apply.official_url, allow)
        else None
    )
    forms = [
        {"id": f.id, "title": f.title, "source_url": f.source_url, "date_checked": f.date_checked}
        for f in request.app.state.forms.values()
        if f.service_id == record.id
    ]
    return {
        "official_url": official,
        "sources": sources,
        "forms": forms,
        "draft_kind": DRAFT_FOR_SERVICE.get(record.id, "complaint"),
        "grievance": [
            {"type": c.type, "name": c.name, "url": c.url, "phone": c.phone}
            for c in record.grievance.channels
            if c.url is None or is_allowed(c.url, allow)
        ],
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
    return {"document": doc, "readiness": _readiness(request, case, _all_documents(store, user.id))}


@router.get("/cases/{case_id}/summary.pdf")
def summary_pdf(case_id: str, user: CurrentUser, request: Request, lang: str = "en") -> Response:
    from app.pdf import summary

    store = request.app.state.store
    case = store.get_case(user.id, case_id)
    if case is None:
        raise HTTPException(404, "Case not found")
    record = request.app.state.catalog.services[case["service_id"]]
    docs = _all_documents(store, user.id)
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
