"""Walking-skeleton chat flow: understand -> retrieve -> eligibility -> compose.

Plain functions for now; S2-01 wraps these as LangGraph nodes with MemorySaver.
Emits the SSE event types defined in docs/ARCHITECTURE.md §10.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import asdict
from datetime import date
from typing import Any

from app.data.loader import Catalog
from app.data.models import Lang, ServiceRecord
from app.graph.templates import t
from app.llm.client import LLM, Understanding
from app.rules.eligibility import Fact, check
from app.rules.fees import fee_strip, is_stale

Event = tuple[str, dict[str, Any]]

CATEGORY_WORDS = {
    "certificate": ("certificate", "praman patra", "प्रमाण पत्र"),
    "scholarship": ("scholarship", "chhatravritti", "छात्रवृत्ति"),
    "pension": ("pension", "पेंशन"),
}


def retrieve(catalog: Catalog, message: str, u: Understanding) -> list[ServiceRecord]:
    """Keyword lookup over served records. No embeddings (see ARCHITECTURE §5)."""
    text = message.casefold()
    words = set(re.findall(r"\w+", text))
    scored: list[tuple[int, ServiceRecord]] = []
    for rec in catalog.served():
        score = 0
        names = [rec.name.en or "", rec.name.hi or "", rec.name.hn or "", *rec.aliases]
        score += sum(3 for n in names if n and n.casefold() in text)
        name_words = set(re.findall(r"\w+", " ".join(names).casefold())) - {"certificate"}
        score += len(words & name_words)
        for cat in rec.category:
            score += sum(2 for w in CATEGORY_WORDS.get(cat, ()) if w in text)
        if score:
            scored.append((score, rec))
    scored.sort(key=lambda x: -x[0])
    return [r for _, r in scored]


def _citations(rec: ServiceRecord) -> list[dict[str, Any]]:
    return [
        {
            "n": i + 1,
            "id": s.id,
            "title": s.title,
            "url": s.url,
            "publisher": s.publisher,
            "date_checked": s.date_checked.isoformat() if s.date_checked else None,
        }
        for i, s in enumerate(rec.sources)
    ]


def _chips(
    u: Understanding, confirmed: dict[str, Any], unknown: list[str], lang: Lang
) -> list[dict[str, Any]]:
    chips: list[dict[str, Any]] = []
    if "state_of_residence" in unknown:
        said = u.facts.state_of_residence
        if said:
            chips.append(
                {
                    "label": t("chip.confirm.state_of_residence", lang, value=said),
                    "confirm": {"state_of_residence": said},
                }
            )
        else:
            chips.append(
                {"label": t("chip.ask.state_of_residence", lang), "confirm": {"state_of_residence": "Delhi"}}
            )
            chips.append(
                {"label": t("chip.ask.state_other", lang), "confirm": {"state_of_residence": "Other"}}
            )
    return chips[:3]


def stream_words(text: str) -> Iterator[Event]:
    for piece in re.findall(r"\S+\s*", text):
        yield "token", {"text": piece}


def run_turn(
    catalog: Catalog,
    llm: LLM,
    message: str,
    lang: Lang,
    confirmed_facts: dict[str, Any],
    today: date,
    freshness_days: int,
) -> Iterator[Event]:
    yield "status", {"id": "understand", "label": t("status.understand", lang), "state": "running"}
    u = llm.understand(message)
    yield "status", {"id": "understand", "label": t("status.understand", lang), "state": "done"}

    yield "status", {"id": "search", "label": t("status.search", lang), "state": "running"}
    matches = retrieve(catalog, message, u)
    yield "status", {"id": "search", "label": t("status.search", lang), "state": "done"}

    if not matches:
        yield from stream_words(t("refusal.no_source", lang))
        yield "done", {"refused": True}
        return

    rec = matches[0]
    yield "status", {"id": "eligibility", "label": t("status.eligibility", lang), "state": "running"}
    facts = {k: Fact(v, confirmed=True) for k, v in confirmed_facts.items()}
    result = check(rec, facts, today)
    yield "status", {"id": "eligibility", "label": t("status.eligibility", lang), "state": "done"}

    stale = is_stale(rec, today, freshness_days)
    labels = {r.id: r.label.get(lang) for r in rec.eligibility.rules}
    citations = _citations(rec)
    cite_n = {c["id"]: c["n"] for c in citations}
    yield (
        "card",
        {
            "type": "service",
            "service": {
                "id": rec.id,
                "name": rec.name.get(lang),
                "department": rec.department.get(lang),
                "summary": rec.summary.get(lang),
                "status": rec.status,
                "stale": stale,
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
                "exclusions_hit": result.exclusions_hit,
            },
            "fee_strip": {**asdict(fee_strip(rec)), "source_n": cite_n[rec.fees.source_ref]},
        },
    )

    text = t("answer.found", lang, name=rec.name.get(lang), summary=rec.summary.get(lang))
    text += " " + t(f"verdict.{result.verdict.value}", lang)
    if rec.fees.official_online_inr is None or rec.timeline.sla_days is None:
        text += " " + t("verify_locally_note", lang)
    yield from stream_words(text + f" [{cite_n[rec.benefit.source_ref]}]")

    for c in citations:
        yield "citation", c
    chips = _chips(u, confirmed_facts, result.unknown_fields, lang)
    if chips:
        yield "chips", {"chips": chips}
    yield "done", {"refused": False}
