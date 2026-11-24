from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request

from app.data.models import Lang

router = APIRouter()


@router.get("/guidance/{topic}")
def get_guidance(topic: str, request: Request, lang: Lang = "en") -> dict[str, Any]:
    """A sourced guidance topic (e.g. complaint vs RTI vs appeal) in the requested language."""
    g = request.app.state.guidance
    if topic not in g.topics:
        raise HTTPException(404, "unknown_topic")
    return g.render(topic, lang)
