"""Pre-filled official forms with the same confirm gate as drafts.

`preview` echoes the values (identity numbers cut to the last 4) plus a hash. `pdf` returns the filled
form only if the user ticked "I checked every field" and the hash matches what they reviewed.
Values are used in memory for that one request: nothing is stored or logged.
"""

from __future__ import annotations

import json
import logging
from typing import Annotated, Any

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response
from pydantic import BaseModel, Field, ValidationError

from app.api.auth import CurrentUser
from app.llm.client import BudgetExceeded, LLMError, RateLimited
from app.pdf import dynamic_filler as dyn
from app.pdf import forms as engine

router = APIRouter()
log = logging.getLogger("sahaay.forms")


class FormIn(BaseModel):
    values: dict[str, str] = Field(default_factory=dict)


class FormDownloadIn(FormIn):
    confirmed_hash: str
    checked_all_fields: bool = False


def _spec(request: Request, form_id: str) -> engine.FormSpec:
    spec = request.app.state.forms.get(form_id)
    if spec is None:
        raise HTTPException(404, "Unknown form")
    return spec


def _clean(spec: engine.FormSpec, values: dict[str, str]) -> dict[str, str]:
    try:
        return engine.clean_values(spec, values)
    except engine.FormError as e:
        raise HTTPException(422, str(e)) from e


def _json(raw: str, what: str) -> Any:
    try:
        return json.loads(raw or "null")
    except ValueError as e:
        raise HTTPException(422, f"bad_{what}") from e


@router.post("/forms/analyze")
async def analyze(
    request: Request,
    user: CurrentUser,
    file: Annotated[UploadFile, File()],
    known: Annotated[str, Form()] = "{}",
    language: Annotated[str, Form()] = "en",
) -> dict[str, Any]:
    """Find the blanks of any uploaded blank form and ask only for the ones with no known fact.

    The upload is processed in memory and never stored. A fillable PDF is read directly. A flat PDF or
    a photo is sent, page by page and nothing else, to the vision model. Tell users to upload a blank form.
    """
    data = await file.read(dyn.MAX_BYTES + 1)
    facts = _json(known, "known")
    if not isinstance(facts, dict):
        raise HTTPException(422, "bad_known")
    lang = language if language in ("en", "hi", "hn") else "en"
    llm = request.app.state.llm

    def work() -> dict[str, Any]:
        doc = dyn.open_upload(data)
        try:
            fields = dyn.acro_fields(doc)
            kind = "fillable"
            if not fields:
                kind = "flat"
                pages = dyn.render_pages(doc)
                try:
                    per_page = [llm.detect_form_fields(png, lang, user_id=user.id).fields for png in pages]
                except RateLimited as e:
                    raise dyn.FormError("rate_limited", 429) from e
                except (BudgetExceeded, LLMError) as e:
                    raise dyn.FormError("vision_unavailable", 503) from e
                fields = dyn.from_vision(per_page)
            if not fields:
                raise dyn.FormError("no_fields_found")
            prefilled, missing, questions = dyn.split_known(fields, {k: v for k, v in facts.items()})
            return {
                "kind": kind,
                "pages": len(doc),
                "fields": [f.model_dump() for f in fields],
                "prefilled_fields": prefilled,
                "missing_fields": missing,
                "questions": questions,
                "sensitive_keys": sorted(dyn.SENSITIVE_KEYS),
            }
        finally:
            doc.close()

    try:
        out = await run_in_threadpool(work)
    except dyn.FormError as e:
        raise HTTPException(e.status, e.code) from e
    # Counts only: never labels, values or the file.
    log.info(
        "form analyzed kind=%s pages=%d fields=%d missing=%d",
        out["kind"],
        out["pages"],
        len(out["fields"]),
        len(out["missing_fields"]),
    )
    return out


@router.post("/forms/render")
async def render(
    user: CurrentUser,
    file: Annotated[UploadFile, File()],
    fields: Annotated[str, Form()],
    values: Annotated[str, Form()],
    checked_all_fields: Annotated[bool, Form()] = False,
) -> Response:
    """Write the confirmed values into the uploaded form and return the PDF. Nothing is stored."""
    if not checked_all_fields:
        raise HTTPException(409, "confirmation_required")
    data = await file.read(dyn.MAX_BYTES + 1)
    raw_fields, raw_values = _json(fields, "fields"), _json(values, "values")
    ok = isinstance(raw_fields, list) and isinstance(raw_values, dict)
    if not ok or len(raw_fields) > dyn.MAX_FIELDS:
        raise HTTPException(422, "bad_fields")
    try:
        detected = [dyn.DetectedField.model_validate(f) for f in raw_fields]
    except ValidationError as e:
        raise HTTPException(422, "bad_fields") from e
    vals = {str(k): v for k, v in raw_values.items() if isinstance(v, str)}
    try:
        pdf = await run_in_threadpool(dyn.fill, data, detected, vals)
    except dyn.FormError as e:
        raise HTTPException(e.status, e.code) from e
    log.info("form rendered fields=%d filled=%d", len(detected), sum(1 for v in vals.values() if v.strip()))
    return Response(
        pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="filled-form.pdf"',
            "Cache-Control": "no-store",
        },
    )


@router.get("/forms")
def list_forms(request: Request) -> list[dict[str, Any]]:
    return [f.public() for f in request.app.state.forms.values()]


@router.post("/forms/{form_id}/preview")
def preview(form_id: str, body: FormIn, request: Request, user: CurrentUser) -> dict[str, Any]:
    spec = _spec(request, form_id)
    values = _clean(spec, body.values)
    return {
        "values": engine.shown(spec, values),
        "hash": engine.content_hash(spec.id, values),
        "source_url": spec.source_url,
        "date_checked": spec.date_checked,
        "confirmed": False,
    }


@router.post("/forms/{form_id}/pdf")
def download(form_id: str, body: FormDownloadIn, request: Request, user: CurrentUser) -> Response:
    spec = _spec(request, form_id)
    values = _clean(spec, body.values)
    if not body.checked_all_fields:
        raise HTTPException(409, "confirmation_required")
    if body.confirmed_hash != engine.content_hash(spec.id, values):
        raise HTTPException(409, "changed_since_review")
    pdf = engine.fill(spec, values)
    log.info("form downloaded form=%s fields=%d", spec.id, len(values))  # never the values
    return Response(
        pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{spec.id}.pdf"', "Cache-Control": "no-store"},
    )
