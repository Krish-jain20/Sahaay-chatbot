"""Complaint / RTI / CPGRAMS drafts with a human confirmation gate.

Step 1 (`/drafts/preview`): the user sees every field exactly as it will appear, plus a content hash.
Step 2 (`/drafts/pdf`): the PDF is produced only if the user ticked "I checked every field" and sent
back the hash of what they reviewed. Change a field after review and the hash no longer matches.
"""

from __future__ import annotations

import logging
from typing import Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.api.auth import CurrentUser
from app.pdf import drafts

router = APIRouter()
log = logging.getLogger("sahaay.drafts")


class DraftIn(BaseModel):
    kind: Literal["complaint", "rti", "cpgrams"]
    lang: Literal["en", "hi", "hn"] = "en"
    fields: dict[str, str | bool | None] = Field(default_factory=dict)


class DownloadIn(DraftIn):
    confirmed_hash: str
    checked_all_fields: bool = False


def _prepare(body: DraftIn) -> tuple[drafts.Lang, dict[str, str]]:
    lang: drafts.Lang = "hi" if body.lang == "hi" else "en"
    try:
        fields = drafts.clean_fields(body.kind, body.fields)
    except drafts.DraftError as e:
        raise HTTPException(422, str(e)) from e
    missing = drafts.missing_required(body.kind, fields)
    if missing:
        raise HTTPException(422, f"missing_required:{','.join(missing)}")
    return lang, fields


@router.post("/drafts/preview")
def preview(body: DraftIn, user: CurrentUser) -> dict[str, object]:
    lang, fields = _prepare(body)
    return {
        "rows": drafts.preview(body.kind, lang, fields),
        "hash": drafts.content_hash(body.kind, lang, fields),
        "confirmed": False,
    }


@router.post("/drafts/pdf")
def download(body: DownloadIn, user: CurrentUser) -> Response:
    lang, fields = _prepare(body)
    if not body.checked_all_fields:
        raise HTTPException(409, "confirmation_required")
    if body.confirmed_hash != drafts.content_hash(body.kind, lang, fields):
        raise HTTPException(409, "changed_since_review")
    try:
        pdf = drafts.render_pdf(body.kind, lang, fields)
    except Exception as e:  # noqa: BLE001 - WeasyPrint raises many types when system libs are missing
        log.error("draft render failed kind=%s err=%s", body.kind, type(e).__name__)
        raise HTTPException(503, "pdf_unavailable") from e
    log.info("draft downloaded kind=%s lang=%s", body.kind, lang)  # never the content
    return Response(
        pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="sahaay-{body.kind}.pdf"',
            "Cache-Control": "no-store",
        },
    )
