"""The Sahaay conversation graph (LangGraph, kept thin).

    understand -> search -> (eligibility -> ask_missing ->) compose

Nodes are plain functions. Deterministic work (retrieval, eligibility, fees, chips) never calls the
LLM; only `understand` does. Events for the client (SSE types in docs/ARCHITECTURE.md §10) are
emitted through the LangGraph custom stream writer. Heavy objects (catalog, llm) travel in the
run config, not in the checkpointed state, so state stays small and serialisable.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import asdict
from datetime import date
from typing import Any, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph
from langgraph.types import RunnableConfig

from app.data.loader import Catalog
from app.data.models import Lang
from app.graph.pipeline import _citations, ask_missing, retrieve, stream_words
from app.graph.templates import t
from app.graph.websearch import run_web_search
from app.llm.client import LLM, BudgetExceeded, LLMError, RateLimited, Understanding
from app.rules.eligibility import Fact, check
from app.rules.fees import fee_strip, is_stale
from app.safety.claims import find_violations
from app.safety.pii import mask_pii

Event = tuple[str, dict[str, Any]]


class CaseState(TypedDict, total=False):
    # inputs
    message: str
    language: Lang
    user_id: str
    confirmed_facts: dict[str, Any]
    today: str
    freshness_days: int
    # working state
    understanding: dict[str, Any]
    service_id: str | None
    unknown_fields: list[str]
    verdict: str
    card: dict[str, Any]
    chips: list[dict[str, Any]]
    failed: bool


def _emit(name: str, data: dict[str, Any]) -> None:
    get_stream_writer()((name, data))


def _status(key: str, lang: Lang, state: str) -> None:
    _emit("status", {"id": key, "label": t(f"status.{key}", lang), "state": state})


def _deps(config: RunnableConfig) -> tuple[Catalog, LLM]:
    c = config["configurable"]
    return c["catalog"], c["llm"]


def understand(state: CaseState, config: RunnableConfig) -> CaseState:
    _, llm = _deps(config)
    lang = state["language"]
    _status("understand", lang, "running")
    try:
        u = llm.understand(state["message"], user_id=state["user_id"])
    except (RateLimited, BudgetExceeded, LLMError):
        _emit("error", {"message": t("error.busy", lang)})
        return {"failed": True}
    _status("understand", lang, "done")
    return {"understanding": u.model_dump()}


def search(state: CaseState, config: RunnableConfig) -> CaseState:
    catalog, _ = _deps(config)
    lang = state["language"]
    _status("search", lang, "running")
    matches = retrieve(catalog, state["message"], Understanding(**state["understanding"]))
    _status("search", lang, "done")
    return {"service_id": matches[0].id if matches else None}


def _alternatives(
    catalog: Catalog, rec: Any, facts: dict[str, Fact], today: date, lang: Lang
) -> list[dict[str, Any]]:
    """Other verified services the person is not ruled out of. Unknown stays 'incomplete', never 'likely'."""
    out = []
    for other in catalog.served():
        if other.id == rec.id or other.id in rec.prerequisites:
            continue
        verdict = check(other, facts, today).verdict.value
        if verdict != "not_eligible":
            out.append({"id": other.id, "name": other.name.get(lang), "verdict": verdict})
    return sorted(out, key=lambda a: a["verdict"] != "likely")[:3]


def web(state: CaseState, config: RunnableConfig) -> CaseState:
    """No verified record matched: answer from a live web search, clearly labelled as unverified."""
    catalog, llm = _deps(config)
    lang = state["language"]
    _status("web", lang, "running")
    res = run_web_search(llm, catalog, state["message"], lang, state["user_id"], state["today"])
    _status("web", lang, "done")
    if res.card is None:
        for ev in stream_words(t("guard.blocked" if res.blocked else "refusal.no_source", lang)):
            _emit(*ev)
        _emit("done", {"refused": True})
        return {}
    _emit("card", res.card)
    for ev in stream_words(res.text):
        _emit(*ev)
    _emit("done", {"refused": False})
    return {}


def eligibility(state: CaseState, config: RunnableConfig) -> CaseState:
    catalog, _ = _deps(config)
    lang = state["language"]
    rec = catalog.services[state["service_id"]]
    today = date.fromisoformat(state["today"])
    _status("eligibility", lang, "running")
    facts = {k: Fact(v, confirmed=True) for k, v in state["confirmed_facts"].items()}
    result = check(rec, facts, today)
    _status("eligibility", lang, "done")

    labels = {r.id: r.label.get(lang) for r in rec.eligibility.rules}
    xlabels = {x.id: x.label.get(lang) for x in rec.exclusions}
    citations = _citations(rec)
    cite_n = {c["id"]: c["n"] for c in citations}
    card = {
        "type": "service",
        "service": {
            "id": rec.id,
            "name": rec.name.get(lang),
            "department": rec.department.get(lang),
            "summary": rec.summary.get(lang),
            "benefit": rec.benefit.amount_text.get(lang),
            "status": rec.status,
            "stale": is_stale(rec, today, state["freshness_days"]),
            "official_url": rec.apply.official_url,
            "source_n": cite_n[rec.benefit.source_ref],
        },
        "eligibility": {
            "verdict": result.verdict.value,
            "rules": [
                {
                    **asdict(o),
                    "result": o.result.value,
                    "label": labels[o.rule_id],
                    "source_n": cite_n[o.source_ref],
                }
                for o in result.rules
            ],
            "exclusions_hit": [{"id": x, "label": xlabels[x]} for x in result.exclusions_hit],
        },
        "prerequisites": [{"id": p, "name": catalog.services[p].name.get(lang)} for p in rec.prerequisites],
        "alternatives": _alternatives(catalog, rec, facts, today, lang),
        "grievance": [
            {"type": c.type, "name": c.name, "url": c.url, "phone": c.phone, "source_n": cite_n[c.source_ref]}
            for c in rec.grievance.channels
        ],
        "fee_strip": {**asdict(fee_strip(rec)), "source_n": cite_n[rec.fees.source_ref]},
    }
    _emit("card", card)
    return {"card": card, "verdict": result.verdict.value, "unknown_fields": result.unknown_fields}


def ask_missing_node(state: CaseState, config: RunnableConfig) -> CaseState:
    u = Understanding(**state["understanding"])
    return {"chips": ask_missing(u, state["unknown_fields"], state["language"])}


def compose(state: CaseState, config: RunnableConfig) -> CaseState:
    catalog, _ = _deps(config)
    lang = state["language"]
    if state.get("failed"):
        _emit("done", {"refused": True})
        return {}
    if not state.get("service_id"):
        for ev in stream_words(t("refusal.no_source", lang)):
            _emit(*ev)
        _emit("done", {"refused": True})
        return {}
    rec = catalog.services[state["service_id"]]
    card = state["card"]
    citations = _citations(rec)
    text = t("answer.found", lang, name=rec.name.get(lang), summary=rec.summary.get(lang))
    text += " " + t(f"verdict.{state['verdict']}", lang)
    if card["prerequisites"]:
        text += " " + t("prereq.note", lang, names=", ".join(p["name"] for p in card["prerequisites"]))
    if rec.fees.official_online_inr is None or rec.timeline.sla_days is None:
        text += " " + t("verify_locally_note", lang)
    text += f" [{card['service']['source_n']}]"
    if find_violations(text):
        # A forbidden claim (e.g. "approved") must never reach the user, even from our own data.
        for ev in stream_words(t("guard.blocked", lang)):
            _emit(*ev)
        _emit("done", {"refused": True})
        return {}
    for ev in stream_words(text):
        _emit(*ev)
    for c in citations:
        _emit("citation", c)
    if state["chips"]:
        _emit("chips", {"chips": state["chips"]})
    _emit("done", {"refused": False})
    return {}


GUIDE_INTENTS = {"complaint": "complaints", "scam": "scams"}


def guidance(state: CaseState, config: RunnableConfig) -> CaseState:
    """General sourced guidance (not tied to one service): streams a short lead-in and a guide card."""
    c = config["configurable"]
    lang = state["language"]
    topic = GUIDE_INTENTS[state["understanding"]["intent"]]
    card = c["guidance"].render(topic, lang)
    for ev in stream_words(t("guide.lead.scam" if topic == "scams" else "guide.lead", lang)):
        _emit(*ev)
    _emit("card", card)
    for cite in card["citations"]:
        _emit("citation", cite)
    _emit("done", {"refused": False})
    return {}


def _after_understand(s: CaseState) -> str:
    if s.get("failed"):
        return "compose"
    if s["understanding"]["intent"] in GUIDE_INTENTS:
        return "guidance"
    return "search"


def _after_search(s: CaseState, config: RunnableConfig) -> str:
    if s.get("service_id"):
        return "eligibility"
    _, llm = _deps(config)
    return "web" if llm.web_enabled else "compose"


def build_graph(checkpointer: Any | None = None):
    g = StateGraph(CaseState)
    g.add_node("understand", understand)
    g.add_node("search", search)
    g.add_node("eligibility", eligibility)
    g.add_node("ask_missing", ask_missing_node)
    g.add_node("compose", compose)
    g.add_node("guidance", guidance)
    g.add_node("web", web)
    g.add_edge(START, "understand")
    g.add_conditional_edges("understand", _after_understand)
    g.add_edge("guidance", END)
    g.add_conditional_edges("search", _after_search)
    g.add_edge("web", END)
    g.add_edge("eligibility", "ask_missing")
    g.add_edge("ask_missing", "compose")
    g.add_edge("compose", END)
    return g.compile(checkpointer=checkpointer or MemorySaver())


def run_turn(
    graph: Any,
    catalog: Catalog,
    llm: LLM,
    message: str,
    lang: Lang,
    confirmed_facts: dict[str, Any],
    today: date,
    freshness_days: int,
    user_id: str = "anonymous",
    thread_id: str | None = None,
    guidance_set: Any = None,
) -> Iterator[Event]:
    """Run one turn and yield client events. `thread_id` keys the checkpoint (a case, later)."""
    config = {
        "configurable": {
            "catalog": catalog,
            "llm": llm,
            "guidance": guidance_set,
            "thread_id": thread_id or f"{user_id}",
        },
    }
    state: CaseState = {
        # Masked before it enters the graph, so identity numbers are never checkpointed or stored.
        "message": mask_pii(message)[0],
        "language": lang,
        "user_id": user_id,
        "confirmed_facts": confirmed_facts,
        "today": today.isoformat(),
        "freshness_days": freshness_days,
        "failed": False,
        "service_id": None,
    }
    yield from graph.stream(state, config, stream_mode="custom")
