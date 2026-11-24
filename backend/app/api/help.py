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
from app.graph.websearch import _URL, run_web_search, web_card
from app.llm.client import BudgetExceeded, LLMError, RateLimited
from app.safety.claims import find_violations
from app.safety.pii import mask_pii

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
    """(card id, heading text, body text), each in every language."""
    out = []
    for topic in g.topics.values():
        for p in topic.points:
            head = " ".join(p.heading.get(lg) or "" for lg in LANGS)
            text = " ".join(p.body.get(lg) or "" for lg in LANGS)
            out.append((f"{topic.id}.{p.id}", head, text))
    return out


def match_cards(g: GuidanceSet, question: str, limit: int = 3) -> list[str]:
    q = _words(question)
    scored = []
    for cid, head, text in _all_cards(g):
        hay_h, hay_b = _words(head), _words(text)

        def hit(w: str, hay: set[str]) -> bool:
            return w in hay or (len(w) >= 4 and any(w in h for h in hay))

        # A word in the card's heading counts double.
        score = sum((2 if hit(w, hay_h) else 0) + (1 if hit(w, hay_b) else 0) for w in q)
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


def _clean(text: str | None) -> str | None:
    """Model text is shown only without links or identity numbers and without a forbidden claim."""
    if not text:
        return None
    out = _URL.sub("", mask_pii(text)[0]).strip()
    return None if not out or find_violations(out) else out


def _card_texts(g: GuidanceSet, ids: list[str], lang: Lang) -> list[tuple[str, str]]:
    out = []
    for cid in ids:
        topic_id, _, point_id = cid.partition(".")
        point = next(p for p in g.topics[topic_id].points if p.id == point_id)
        out.append((cid, f"{point.heading.get(lang)}\n{point.body.get(lang)}"))
    return out


@router.post("/help/ask")
def ask(body: AskRequest, request: Request, user: CurrentUser) -> dict[str, Any]:
    """Answer a free question. Order: live web answer, then the matching cards with labelled general
    guidance, then the top card's own text. A person with a matching card never gets a bare 'no answer'."""
    g: GuidanceSet = request.app.state.guidance
    question = mask_pii(body.question)[0].strip()
    matches = match_cards(g, question)
    llm = request.app.state.llm
    today = date.today().isoformat()
    answer: str | None = None
    web: dict[str, Any] | None = None
    basis = "none"
    if llm.web_enabled:
        # The question doubles as the search query: a long preamble drowns it and the search returns
        # unrelated government pages, so add only a short place hint.
        res = run_web_search(
            llm, request.app.state.catalog, help_query(question), body.language, user.id, today
        )
        if res.card is not None:
            answer, web, basis = res.text, res.card, "web"
    texts = _card_texts(g, matches, body.language)
    if answer is None:
        cards = "\n\n".join(f"[{cid}]\n{t}" for cid, t in texts) or "(no matching card)"
        try:
            answer = _clean(llm.help_answer(question, cards, body.language, user_id=user.id))
        except (RateLimited, BudgetExceeded, LLMError):
            answer = None
        if answer:
            basis = "cards"
        elif texts:
            answer, basis = texts[0][1].split("\n", 1)[1], "card_text"
    return {"answer": answer, "web": web, "matches": matches, "basis": basis, "state": basis}


class ExplainRequest(BaseModel):
    card_id: str = Field(max_length=80)
    language: Lang = "en"
    situation: str = Field(default="", max_length=200)


@router.post("/help/explain")
def explain(body: ExplainRequest, request: Request, user: CurrentUser) -> dict[str, Any]:
    """Without a situation: the card in plain words. With one: a practical answer to that situation,
    from the card text plus a web lookup (official pages first), with sources and the search date."""
    g: GuidanceSet = request.app.state.guidance
    topic_id, _, point_id = body.card_id.partition(".")
    topic = g.topics.get(topic_id)
    point = next((p for p in topic.points if p.id == point_id), None) if topic else None
    if point is None:
        raise HTTPException(404, "unknown_card")
    card_text = f"{point.heading.get(body.language)}\n{point.body.get(body.language)}"
    situation = mask_pii(body.situation)[0].strip()
    llm = request.app.state.llm
    text: str | None = None
    web: dict[str, Any] | None = None
    try:
        if situation:
            ans = llm.situation_answer(card_text, situation, body.language, user_id=user.id)
            text = _clean(ans.text) if ans else None
            if text and ans and ans.sources:
                web = web_card(ans.sources, request.app.state.catalog, date.today().isoformat())
        else:
            text = _clean(llm.explain_card(card_text, "", body.language, user_id=user.id))
    except (RateLimited, BudgetExceeded, LLMError):
        text = None
    if not text:
        raise HTTPException(503, "explain_unavailable")
    return {"text": text, "web": web, "basis": "web" if web else "card"}
