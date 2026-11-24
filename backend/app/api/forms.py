"""Pre-filled official forms with the same confirm gate as drafts.

`preview` echoes the values (identity numbers cut to the last 4) plus a hash. `pdf` returns the filled
form only if the user ticked "I checked every field" and the hash matches what they reviewed.
Values are used in memory for that one request: nothing is stored or logged.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.api.auth import CurrentUser
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
