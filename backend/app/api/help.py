"""Help and rights: sourced guidance cards, an AI "ask", and a plain-language "learn more" per card.

Cards come from data/guidance.json (verified, sourced). The answer to a free question is a live web
answer through the shared, guarded web search (masked input, no forbidden claims, injection fencing),
plus the verified cards that match the words. "Learn more" explains one card from that card's own text only.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.api.auth import CurrentUser
from app.data.guidance import GuidanceSet
from app.data.models import Lang
from app.graph.websearch import _URL, run_web_search
from app.llm.client import BudgetExceeded, LLMError, RateLimited
from app.safety.claims import find_violations
from app.safety.pii import mask, mask_pii

router = APIRouter()

LANGS: tuple[Lang, ...] = ("en", "hi", "hn")
STOP = {
    "the", "and", "for", "how", "what", "can", "does", "with", "that", "this", "are", "you", "not",
    "kya", "hai", "hain", "kaise", "ko", "ka", "ki", "ke", "mein", "se", "ya", "aur", "mujhe", "meri",
}
_WORD = re.compile(r"[\wऀ-ॿ]{3,}")


def _words(text: str) -> set[str]:
    return {w for w in _WORD.findall(text.lower()) if w not in STOP}


def _all_cards(g: GuidanceSet) -> list[tuple[str, str, str]]:
    """(card id, topic id, searchable text in every language)."""
    out = []
    for topic in g.topics.values():
        for p in topic.points:
            text = " ".join(f"{p.heading.get(lg) or ''} {p.body.get(lg) or ''}" for lg in LANGS)
            out.append((f"{topic.id}.{p.id}", topic.id, text))
    return out


def match_cards(g: GuidanceSet, question: str, limit: int = 3) -> list[str]:
    q = _words(question)
    scored = []
    for cid, _topic, text in _all_cards(g):
        hay = _words(text)
        score = sum(1 for w in q if w in hay or any(w in h for h in hay if len(w) >= 4))
        if score:
            scored.append((score, cid))
    scored.sort(key=lambda s: (-s[0], s[1]))
    return [cid for _, cid in scored[:limit]]


def help_query(question: str) -> str:
    """Search query for a help question: the user's words first, plus a short place hint."""
    return f"{question} (Delhi, India)"


@router.get("/help")
def help_sections(request: Request, lang: Lang = "en") -> dict[str, Any]:
    g: GuidanceSet = request.app.state.guidance
    return {"sections": [g.render(t, lang) for t in g.topics]}


class AskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=300)
    language: Lang = "en"


@router.post("/help/ask")
def ask(body: AskRequest, request: Request, user: CurrentUser) -> dict[str, Any]:
    g: GuidanceSet = request.app.state.guidance
    question = mask_pii(body.question)[0].strip()
    matches = match_cards(g, question)
    answer: str | None = None
    web: dict[str, Any] | None = None
    state = "unavailable"
    llm = request.app.state.llm
    if llm.web_enabled:
        # The question doubles as the search query: a long preamble drowns it and the search returns
        # unrelated government pages, so add only a short place hint.
        res = run_web_search(
            llm,
            request.app.state.catalog,
            help_query(question),
            body.language,
            user.id,
            date.today().isoformat(),
        )
        if res.card is None:
            state = "blocked" if res.blocked else "none"
        else:
            answer, web, state = res.text, res.card, "ok"
    return {"answer": answer, "web": web, "matches": matches, "state": state}


class ExplainRequest(BaseModel):
    card_id: str = Field(max_length=80)
    language: Lang = "en"
    situation: str = Field(default="", max_length=200)


@router.post("/help/explain")
def explain(body: ExplainRequest, request: Request, user: CurrentUser) -> dict[str, str]:
    g: GuidanceSet = request.app.state.guidance
    topic_id, _, point_id = body.card_id.partition(".")
    topic = g.topics.get(topic_id)
    point = next((p for p in topic.points if p.id == point_id), None) if topic else None
    if point is None:
        raise HTTPException(404, "unknown_card")
    card_text = f"{point.heading.get(body.language)}\n{point.body.get(body.language)}"
    try:
        out = request.app.state.llm.explain_card(
            card_text, mask(body.situation).strip(), body.language, user_id=user.id
        )
    except (RateLimited, BudgetExceeded, LLMError):
        out = None
    if not out:
        raise HTTPException(503, "explain_unavailable")
    text = _URL.sub("", mask_pii(out)[0]).strip()
    if not text or find_violations(text):
        raise HTTPException(503, "explain_unavailable")
    return {"text": text}
