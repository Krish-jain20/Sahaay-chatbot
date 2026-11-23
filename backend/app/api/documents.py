from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Annotated, Any

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from app.api.auth import CurrentUser
from app.ocr import pipeline

router = APIRouter()
log = logging.getLogger("sahaay.documents")


@router.get("/doc-types")
def list_doc_types(request: Request) -> list[dict[str, Any]]:
    """Document types that can be scanned, with the fields a user will review."""
    return [
        {"id": d["id"], "extract_fields": d["extract_fields"], "required_fields": d["required_fields"]}
        for d in request.app.state.doc_types.values()
    ]


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
