"""Chat flow: understand -> retrieve -> eligibility -> ask_missing -> compose.

Plain functions for now; S2-01 wraps these as LangGraph nodes with MemorySaver.
Emits the SSE event types defined in docs/ARCHITECTURE.md §10.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from typing import Any

from app.data.loader import Catalog
from app.data.models import Lang, ServiceRecord
from app.graph.templates import t
from app.llm.client import Understanding

Event = tuple[str, dict[str, Any]]

CATEGORY_WORDS = {
    "certificate": ("certificate", "praman patra", "प्रमाण पत्र"),
    "scholarship": ("scholarship", "chhatravritti", "छात्रवृत्ति", "वजीफा", "wazifa"),
    "pension": ("pension", "पेंशन"),
}
STOPWORDS = {"certificate", "for", "and", "of", "the", "in", "students", "old", "age"}

# Quick-reply options per profile key: (template key, confirmed value).
# Range options carry a representative value that sits inside the range the user picked.
ASK_OPTIONS: dict[str, list[tuple[str, Any]]] = {
    "state_of_residence": [("opt.state.delhi", "Delhi"), ("opt.state.other", "Other")],
    "social_category": [
        ("opt.cat.sc", "sc"),
        ("opt.cat.st", "st"),
        ("opt.cat.obc", "obc"),
        ("opt.cat.general", "general"),
    ],
    "occupation": [("opt.occ.student", "student"), ("opt.occ.other", "other")],
    "age": [("opt.age.60", 65), ("opt.age.70", 75), ("opt.age.under", 50)],
    "years_resident_in_state": [("opt.res.5", 5), ("opt.res.less", 0)],
    "annual_family_income_inr": [("opt.inc.1", 90_000), ("opt.inc.3", 200_000), ("opt.inc.more", 400_000)],
    "previous_year_marks_percent": [("opt.marks.60", 60), ("opt.marks.less", 50)],
    "has_bank_account_linked": [("opt.bank.yes", True), ("opt.bank.no", False)],
}


def retrieve(catalog: Catalog, message: str, u: Understanding) -> list[ServiceRecord]:
    """Keyword lookup over served records, plus hints from stated facts. No embeddings."""
    text = message.casefold()
    words = set(re.findall(r"\w+", text))
    scored: list[tuple[int, ServiceRecord]] = []
    for rec in catalog.served():
        names = [rec.name.en or "", rec.name.hi or "", rec.name.hn or "", *rec.aliases]
        score = sum(3 for n in names if n and n.casefold() in text)
        name_words = set(re.findall(r"\w+", " ".join(names).casefold())) - STOPWORDS
        score += len(words & name_words)
        # A bare category word ("certificate") is not enough: "domicile certificate" must not
        # match the income certificate. A record needs its own name, or a stated fact that fits it.
        evidence = score > 0
        for cat in rec.category:
            score += sum(2 for w in CATEGORY_WORDS.get(cat, ()) if w in text)
            if cat == "scholarship" and u.facts.occupation == "student":
                score += 2
                evidence = True
            if cat == "pension" and ((u.facts.age or 0) >= 60 or u.facts.occupation == "retired"):
                score += 2
                evidence = True
        if score and evidence:
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


def _fmt(key: str, value: Any) -> str:
    if key == "annual_family_income_inr":
        return f"₹{value:,}"
    return str(value)


def ask_missing(u: Understanding, unknown: list[str], lang: Lang) -> list[dict[str, Any]]:
    """Chips for facts that change the verdict. Facts the user stated are offered for confirmation first."""
    said = {k: v for k, v in u.facts.model_dump().items() if v is not None and k in unknown}
    if said:
        label = t("chip.confirm_said", lang, facts=", ".join(_fmt(k, v) for k, v in said.items()))
        return [{"label": label, "confirm": said}]
    for key in unknown:
        if key in ASK_OPTIONS:
            return [{"label": t(tk, lang), "confirm": {key: v}} for tk, v in ASK_OPTIONS[key]][:4]
    return []


def stream_words(text: str) -> Iterator[Event]:
    for piece in re.findall(r"\S+\s*", text):
        yield "token", {"text": piece}
