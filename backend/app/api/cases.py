"""Cases and their confirmed documents.

A case is one user's progress on one service. Only fields the user has reviewed and confirmed are
stored, and every string is masked again here so a full ID number can never be saved. The upload
itself is never stored. Readiness is computed from the stored documents by a pure function.
"""

from __future__ import annotations

import copy
import re
import uuid
from dataclasses import asdict
from datetime import UTC, date, datetime
from typing import Any
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.api.auth import CurrentUser
from app.rules.case_overview import MAX_FOLLOW_UP_DAYS, merge_documents, overview
from app.rules.custom_case import (
    CUSTOM_SERVICE_ID,
    KEY_DATE_KINDS,
    custom_readiness,
    key_date,
    merge_document_list,
    todo_counts,
)
from app.rules.journey import STEP_KEYS, journey
from app.rules.readiness import readiness
from app.safety.allowlist import is_allowed
from app.safety.claims import find_violations
from app.safety.pii import mask_pii

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
    key_date: date | None = None  # the user's own last date or appointment
    key_date_kind: str = "deadline"
    key_date_label: str | None = Field(default=None, max_length=60)
    clear_key_date: bool = False


class NoteIn(BaseModel):
    text: str = Field(min_length=1, max_length=300)


class TodoIn(BaseModel):
    text: str = Field(min_length=1, max_length=120)


class TodoPatch(BaseModel):
    done: bool


class SourceIn(BaseModel):
    title: str = Field(default="", max_length=120)
    url: str = Field(max_length=500)


class CustomServiceIn(BaseModel):
    """A service the user adds themselves. All of it is theirs: labelled, never presented as fact."""

    name: str = Field(min_length=2, max_length=80)
    department: str = Field(default="", max_length=100)
    portal_url: str | None = Field(default=None, max_length=300)
    documents: list[str] = Field(default_factory=list, max_length=20)
    steps: list[str] = Field(default_factory=list, max_length=12)
    timeline_days: int | None = Field(default=None, ge=1, le=MAX_FOLLOW_UP_DAYS)
    ai_suggested: bool = False  # some of this came from the AI suggestion (the user may have edited it)
    sources: list[SourceIn] = Field(default_factory=list, max_length=6)


class CustomDocPatch(BaseModel):
    have: bool


class SuggestIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    lang: str = "en"


MAX_NOTES = 50
MAX_TODOS = 30

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


def _clean(text: str, limit: int) -> str:
    """User or AI text kept on a case: identity numbers masked, links removed, whitespace tidied."""
    text = re.sub(r"https?://\S+|www\.\S+", "", mask_pii(text)[0])
    return re.sub(r"\s+", " ", text).strip()[:limit]


def _http_url(url: str | None) -> str | None:
    url = (url or "").strip()
    if not url:
        return None
    if not re.fullmatch(r"https?://[^\s<>\"']+", url) or mask_pii(url)[1]:
        raise HTTPException(422, "Link must start with https:// or http://")
    return url


def _new_id() -> str:
    return uuid.uuid4().hex[:10]


def _custom_details(body: CustomServiceIn, old: dict[str, Any] | None) -> dict[str, Any]:
    name = _clean(body.name, 80)
    if len(name) < 2:
        raise HTTPException(422, "Service name is required")
    texts = [_clean(d, 80) for d in body.documents] + [_clean(st, 200) for st in body.steps] + [name]
    if any(find_violations(t) for t in texts):
        raise HTTPException(422, "Text promises an outcome Sahaay cannot promise")
    docs = [d for d in (_clean(x, 80) for x in body.documents) if d]
    return {
        "name": name,
        "department": _clean(body.department, 100),
        "portal_url": _http_url(body.portal_url),
        "documents": merge_document_list((old or {}).get("documents", []), docs, _new_id),
        "steps": [st for st in (_clean(x, 200) for x in body.steps) if st],
        "timeline_days": body.timeline_days,
        "ai_suggested": body.ai_suggested,
        "sources": [
            {"title": _clean(src.title, 120), "url": u}
            for src in body.sources
            if (u := (src.url if re.fullmatch(r"https?://[^\s<>\"']+", src.url) else None))
        ],
        "added_on": (old or {}).get("added_on") or date.today().isoformat(),
    }


@router.post("/cases/custom", status_code=201)
def create_custom_case(
    body: CustomServiceIn, user: CurrentUser, request: Request, lang: str = "en"
) -> dict[str, Any]:
    """Track a service Sahaay has no verified record for. The details are the user's own."""
    store = request.app.state.store
    details = _custom_details(body, None)
    case = store.create_case(user.id, CUSTOM_SERVICE_ID)
    state = {"custom": details}
    store.update_case_state(user.id, case["id"], state)
    case["state"] = state
    return _case_view(request, case, _all_documents(store, user.id), lang)


@router.put("/cases/{case_id}/custom")
def edit_custom_case(
    case_id: str, body: CustomServiceIn, user: CurrentUser, request: Request, lang: str = "en"
) -> dict[str, Any]:
    store, case, state = _custom_case(request, user.id, case_id)
    state["custom"] = _custom_details(body, state.get("custom"))
    return _save_state(request, store, case, state, lang)


@router.patch("/cases/{case_id}/custom/documents/{doc_id}")
def tick_custom_document(
    case_id: str, doc_id: str, body: CustomDocPatch, user: CurrentUser, request: Request, lang: str = "en"
) -> dict[str, Any]:
    store, case, state = _custom_case(request, user.id, case_id)
    docs = state["custom"].get("documents", [])
    if not any(d["id"] == doc_id for d in docs):
        raise HTTPException(404, "Document not found")
    state["custom"]["documents"] = [{**d, "have": body.have} if d["id"] == doc_id else d for d in docs]
    return _save_state(request, store, case, state, lang)


@router.post("/cases/suggest")
def suggest_service(body: SuggestIn, user: CurrentUser, request: Request) -> dict[str, Any]:
    """AI-suggested starting checklist for a service the user named. Not checked by Sahaay, and editable."""
    from app.graph.websearch import web_card
    from app.llm.client import BudgetExceeded, LLMError, RateLimited

    llm = request.app.state.llm
    if not llm.web_enabled:
        raise HTTPException(503, "suggest_unavailable")
    lang = body.lang if body.lang in ("en", "hi", "hn") else "en"
    try:
        got = llm.suggest_service(body.name, lang, user_id=user.id)
    except RateLimited as e:
        raise HTTPException(429, "rate_limited") from e
    except (BudgetExceeded, LLMError) as e:
        raise HTTPException(503, "suggest_unavailable") from e
    if got is None:
        return {"found": False}
    sug, raw_sources = got
    keep = lambda items, n, cap: [  # noqa: E731
        x for x in (_clean(i, n) for i in items) if x and not find_violations(x)
    ][:cap]
    card = web_card(raw_sources, request.app.state.catalog, date.today().isoformat())
    official = next((s["url"] for s in card["sources"] if s["official"]), None)
    note = _clean(sug.note or "", 200)
    return {
        "found": True,
        "label": "ai_suggested_not_checked",
        "department": _clean(sug.department or "", 100),
        "documents": keep(sug.documents, 80, 12),
        "steps": keep(sug.steps, 200, 8),
        "timeline_days": sug.timeline_days if sug.timeline_days and 1 <= sug.timeline_days <= 365 else None,
        "note": "" if find_violations(note) else note,
        "portal_url": official,  # only ever a link whose exact host is on the allowlist
        "retrieved_on": card["retrieved_on"],
        "sources": card["sources"],
    }


@router.post("/cases/{case_id}/todos", status_code=201)
def add_todo(
    case_id: str, body: TodoIn, user: CurrentUser, request: Request, lang: str = "en"
) -> dict[str, Any]:
    store, case, state = _owned(request, user.id, case_id)
    todos = list(state.get("todos", []))
    if len(todos) >= MAX_TODOS:
        raise HTTPException(422, "Too many to-dos")
    text = _clean(body.text, 120)
    if not text:
        raise HTTPException(422, "To-do is empty")
    todos.append({"id": uuid.uuid4().hex[:12], "text": text, "done": False})
    state["todos"] = todos
    return _save_state(request, store, case, state, lang)


@router.patch("/cases/{case_id}/todos/{todo_id}")
def tick_todo(
    case_id: str, todo_id: str, body: TodoPatch, user: CurrentUser, request: Request, lang: str = "en"
) -> dict[str, Any]:
    store, case, state = _owned(request, user.id, case_id)
    todos = state.get("todos", [])
    if not any(t["id"] == todo_id for t in todos):
        raise HTTPException(404, "To-do not found")
    state["todos"] = [{**t, "done": body.done} if t["id"] == todo_id else t for t in todos]
    return _save_state(request, store, case, state, lang)


@router.delete("/cases/{case_id}/todos/{todo_id}")
def delete_todo(
    case_id: str, todo_id: str, user: CurrentUser, request: Request, lang: str = "en"
) -> dict[str, Any]:
    store, case, state = _owned(request, user.id, case_id)
    state["todos"] = [t for t in state.get("todos", []) if t["id"] != todo_id]
    return _save_state(request, store, case, state, lang)


def _owned(request: Request, user_id: str, case_id: str) -> tuple[Any, dict[str, Any], dict[str, Any]]:
    store = request.app.state.store
    case = store.get_case(user_id, case_id)
    if case is None:
        raise HTTPException(404, "Case not found")
    return store, case, copy.deepcopy(case.get("state") or {})


def _custom_case(request: Request, user_id: str, case_id: str) -> tuple[Any, dict[str, Any], dict[str, Any]]:
    store, case, state = _owned(request, user_id, case_id)
    if case["service_id"] != CUSTOM_SERVICE_ID or not state.get("custom"):
        raise HTTPException(404, "Not a service you added")
    return store, case, state


def _save_state(
    request: Request, store: Any, case: dict[str, Any], state: dict[str, Any], lang: str
) -> dict[str, Any]:
    store.update_case_state(case["user_id"], case["id"], state)
    case["state"] = state
    return _case_view(request, case, _all_documents(store, case["user_id"]), lang)


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
    if body.clear_key_date:
        state.pop("key_date", None)
    elif body.key_date is not None:
        if body.key_date_kind not in KEY_DATE_KINDS:
            raise HTTPException(422, "Unknown date kind")
        state["key_date"] = {
            "on": body.key_date.isoformat(),
            "kind": body.key_date_kind,
            "label": _clean(body.key_date_label or "", 60),
        }
    store.update_case_state(user.id, case_id, state)
    case["state"] = state
    return _case_view(request, case, _all_documents(store, user.id), lang)


@router.post("/cases/{case_id}/notes", status_code=201)
def add_note(
    case_id: str, body: NoteIn, user: CurrentUser, request: Request, lang: str = "en"
) -> dict[str, Any]:
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
    state = case.get("state") or {}
    lang_ = lang if lang in ("en", "hi", "hn") else "en"
    custom = state.get("custom") if case["service_id"] == CUSTOM_SERVICE_ID else None
    if custom is not None:
        ready = custom_readiness(custom.get("documents", []))
        sla_days = custom.get("timeline_days")
    else:
        record = request.app.state.catalog.services[case["service_id"]]
        ready = readiness(record, docs, date.today())
        sla_days = record.timeline.sla_days
    j = journey(store.list_events(user_id, case["id"]))
    submission = store.get_submission(user_id, case["id"])
    ov = overview(ready, j, submission, state, sla_days, date.today())
    todos = state.get("todos", [])
    kd = key_date(state.get("key_date"), date.today())
    common = {
        "id": case["id"],
        "service_id": case["service_id"],
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
        "todos": todos,
        "todos_done": todo_counts(todos)[0],
        "key_date": jsonable(asdict(kd)) if kd else None,
    }
    if custom is not None:
        allow = request.app.state.catalog.allowlist
        portal = custom.get("portal_url")
        return {
            **common,
            "service_name": custom["name"],
            "department": custom.get("department") or None,
            "custom": {
                "label": "added_by_you",
                "ai_suggested": bool(custom.get("ai_suggested")),
                "portal_url": portal,
                # Shown as official only on an exact allowlist host; otherwise it is "a link you added".
                "portal_official": bool(portal and is_allowed(portal, allow)),
                "documents": custom.get("documents", []),
                "timeline_days": custom.get("timeline_days"),
                "sources": [_source_view(src, allow) for src in custom.get("sources", [])],
                "added_on": custom.get("added_on"),
            },
            "steps_text": [{"n": i + 1, "text": st} for i, st in enumerate(custom.get("steps", []))],
            "prerequisites": [],
            "links": {
                "official_url": portal if portal and is_allowed(portal, allow) else None,
                "sources": [],
                "forms": [],
                "draft_kind": "complaint",
                "grievance": [],
            },
        }
    return {
        **common,
        "service_name": record.name.get(lang_),
        "department": record.department.get(lang_),
        "custom": None,
        "steps_text": [{"n": st.n, "text": st.text.get(lang_)} for st in record.apply.steps],
        "prerequisites": [
            {"id": p, "name": request.app.state.catalog.services[p].name.get(lang_)}
            for p in record.prerequisites
        ],
        "links": _links(request, record, lang_),
    }


def _source_view(src: dict[str, Any], allow: Any) -> dict[str, Any]:
    official = is_allowed(src["url"], allow)
    host = (urlparse(src["url"]).hostname or "").lower()
    gov = host.endswith((".gov.in", ".nic.in"))  # a suffix alone is never proof: only "not yet checked"
    kind = "official" if official else ("gov_unchecked" if gov else "other")
    return {**src, "official": official, "kind": kind}


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
    store = request.app.state.store
    case = store.get_case(user.id, case_id)
    if case is None:
        raise HTTPException(404, "Case not found")
    if case["service_id"] == CUSTOM_SERVICE_ID:
        raise HTTPException(422, "A service you added uses its own checklist")
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
    lang_ = "hi" if lang == "hi" else "en"
    custom = (case.get("state") or {}).get("custom") if case["service_id"] == CUSTOM_SERVICE_ID else None
    if custom is not None:
        try:
            pdf = summary.render_custom_pdf(
                custom,
                lang_,
                custom_readiness(custom.get("documents", [])),
                journey(store.list_events(user.id, case_id)),
                store.get_submission(user.id, case_id),
                case.get("state") or {},
            )
        except Exception as e:  # noqa: BLE001 - WeasyPrint raises many types when system libraries are missing
            raise HTTPException(503, "pdf_unavailable") from e
        return _pdf_response(pdf)
    record = request.app.state.catalog.services[case["service_id"]]
    docs = _all_documents(store, user.id)
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
    return _pdf_response(pdf)


def _pdf_response(pdf: bytes) -> Response:
    return Response(
        pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="sahaay-case-summary.pdf"',
            "Cache-Control": "no-store",
        },
    )
