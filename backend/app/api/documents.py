from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Annotated, Any

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from app.api.auth import CurrentUser
from app.ocr import pipeline

router = APIRouter()
log = logging.getLogger("sahaay.documents")


@router.post("/documents")
async def upload_document(
    request: Request,
    user: CurrentUser,
    file: Annotated[UploadFile, File()],
    doc_type: Annotated[str, Form()],
) -> dict[str, Any]:
    """Process an upload in memory. The file is never stored; only masked fields are returned."""
    data = await file.read(pipeline.MAX_BYTES + 1)
    doc_types = request.app.state.doc_types
    try:
        result = pipeline.process(data, doc_type, doc_types)
    except pipeline.UploadError as e:
        raise HTTPException(e.status, e.code) from e
    finally:
        del data
    log.info("document processed type=%s findings=%d", doc_type, len(result.findings))  # no content
    return {
        "doc_type": result.doc_type,
        "fields": result.fields,
        "findings": [asdict(f) for f in result.findings],
        "quality": result.quality,
        "confirmed": False,  # the user must confirm before anything is used or saved
    }
