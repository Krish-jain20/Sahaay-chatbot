from __future__ import annotations

import logging
from dataclasses import asdict
from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from app.api.auth import CurrentUser
from app.api.cases import _all_documents, jsonable
from app.ocr import pipeline
from app.rules.custom_case import CUSTOM_SERVICE_ID
from app.rules.readiness import CheckStatus, Evaluated, readiness

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


_STATUS_ORDER = {CheckStatus.EXPIRED: 0, CheckStatus.TOO_OLD: 1, CheckStatus.MISSING: 2, CheckStatus.OK: 3}


@router.get("/documents/overview")
def documents_overview(user: CurrentUser, request: Request, lang: str = "en") -> dict[str, Any]:
    """One list of documents across all of the user's cases.

    A document is added once and counts for every case that needs it. Each row says which cases need it
    and how it stands for each (ready, missing, expired, too old). Services the user added themselves have
    their own tick list and are returned separately. Nothing here says a document is genuine.
    """
    store = request.app.state.store
    catalog = request.app.state.catalog
    lang_ = lang if lang in ("en", "hi", "hn") else "en"
    docs = _all_documents(store, user.id)
    today = date.today()
    rows: dict[str, dict[str, Any]] = {}
    custom: list[dict[str, Any]] = []
    for case in store.list_cases(user.id):
        if case["service_id"] == CUSTOM_SERVICE_ID:
            details = (case.get("state") or {}).get("custom") or {}
            custom.append(
                {
                    "case_id": case["id"],
                    "name": details.get("name", ""),
                    "documents": details.get("documents", []),
                }
            )
            continue
        record = catalog.services[case["service_id"]]
        for c in readiness(record, docs, today).checks:
            row = rows.setdefault(
                c.doc_type, {"doc_type": c.doc_type, "held": None, "needed_by": [], "scannable": False}
            )
            row["needed_by"].append(
                {
                    "case_id": case["id"],
                    "name": record.name.get(lang_),
                    "required": c.required,
                    "status": c.status.value,
                    "expires_on": c.expires_on.isoformat() if c.expires_on else None,
                }
            )
            if c.evaluated is not Evaluated.NONE and row["held"] is None:
                row["held"] = {
                    "doc_type": c.matched_doc_type or c.doc_type,
                    "evaluated": c.evaluated.value,
                    "issue_date": c.issue_date.isoformat() if c.issue_date else None,
                }
    for row in rows.values():
        row["scannable"] = row["doc_type"] in request.app.state.doc_types
        row["required_anywhere"] = any(n["required"] for n in row["needed_by"])
        row["needs_attention"] = any(n["required"] and n["status"] != "ok" for n in row["needed_by"])
    # What is missing first, then what is needed by the most cases.
    ordered = sorted(
        rows.values(),
        key=lambda r: (
            not r["needs_attention"],
            min(_STATUS_ORDER[CheckStatus(n["status"])] for n in r["needed_by"]),
            -len(r["needed_by"]),
            r["doc_type"],
        ),
    )
    return jsonable(
        {
            "documents": ordered,
            "missing_count": sum(r["needs_attention"] for r in ordered),
            "custom": custom,
        }
    )


@router.get("/services/{service_id}/readiness")
def service_readiness(service_id: str, user: CurrentUser, request: Request) -> dict[str, Any]:
    """What a service asks for, checked against documents the user already added. No case is created."""
    record = request.app.state.catalog.services.get(service_id)
    if record is None or record.status == "unverified":
        raise HTTPException(404, "Service not found")
    docs = _all_documents(request.app.state.store, user.id)
    return jsonable(asdict(readiness(record, docs, date.today())))


@router.delete("/documents/{doc_type}")
def remove_document(doc_type: str, user: CurrentUser, request: Request) -> dict[str, int]:
    """Remove a document the user added, from every case at once. The upload itself was never stored."""
    removed = request.app.state.store.delete_documents_of_type(user.id, doc_type)
    if not removed:
        raise HTTPException(404, "Document not found")
    return {"removed": removed}
