from __future__ import annotations

import asyncio
import json
import uuid
from datetime import date
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from app.api.auth import CurrentUser
from app.config import get_settings
from app.data.models import Lang
from app.graph.graph import run_turn
from app.safety.pii import mask

router = APIRouter()
_cancelled: set[str] = set()
TOKEN_DELAY_S = 0.02  # paces the stream so the UI can show it arriving


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    language: Lang = "en"
    confirmed_facts: dict[str, Any] = {}
    stream_id: str | None = None


class StopRequest(BaseModel):
    stream_id: str


@router.post("/chat")
async def chat(body: ChatRequest, request: Request, user: CurrentUser) -> EventSourceResponse:
    catalog = request.app.state.catalog
    llm = request.app.state.llm
    settings = get_settings()
    stream_id = body.stream_id or uuid.uuid4().hex

    async def events():
        yield {
            "event": "status",
            "data": json.dumps({"id": "stream", "stream_id": stream_id, "state": "open"}),
        }
        for name, data in run_turn(
            request.app.state.graph,
            catalog,
            llm,
            mask(body.message),
            body.language,
            body.confirmed_facts,
            date.today(),
            settings.freshness_days,
            user.id,
        ):
            if stream_id in _cancelled or await request.is_disconnected():
                _cancelled.discard(stream_id)
                yield {"event": "done", "data": json.dumps({"stopped": True})}
                return
            yield {"event": name, "data": json.dumps(data, ensure_ascii=False)}
            if name == "token":
                await asyncio.sleep(TOKEN_DELAY_S)

    return EventSourceResponse(events())


@router.post("/chat/stop")
async def stop(body: StopRequest, _: CurrentUser) -> dict[str, bool]:
    _cancelled.add(body.stream_id)
    return {"ok": True}
