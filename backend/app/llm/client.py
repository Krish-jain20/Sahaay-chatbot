"""The single LLM wrapper. No other module may import a provider SDK.

Until GEMINI_API_KEY is set, a deterministic offline stub serves `extract`, so the
app runs end to end without a key. The Gemini provider lands in S0-07.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal, Protocol

from pydantic import BaseModel

from app.config import get_settings

PROMPTS = Path(__file__).parent / "prompts"

Intent = Literal[
    "find",
    "info",
    "compare",
    "eligibility",
    "documents",
    "form",
    "complaint",
    "term",
    "screenshot",
    "other",
]


class ExtractedFacts(BaseModel):
    state_of_residence: str | None = None
    annual_family_income_inr: int | None = None
    occupation: str | None = None


class Understanding(BaseModel):
    intent: Intent = "other"
    facts: ExtractedFacts = ExtractedFacts()
    service_query: str | None = None


def load_prompt(name: str) -> str:
    return (PROMPTS / f"{name}.md").read_text("utf-8")


class Provider(Protocol):
    name: str

    def understand(self, text: str) -> Understanding: ...


_LAKH = re.compile(r"(\d+(?:\.\d+)?)\s*(?:lakh|lac|लाख)", re.I)
_RUPEES = re.compile(r"(?:₹|rs\.?|inr)\s*([\d,]{4,})", re.I)
_OCCUPATIONS = {
    "student": ("student", "studying", "college", "छात्र", "padhai", "padhta", "padhti"),
    "retired": ("retired", "senior citizen", "रिटायर", "बुज़ुर्ग", "buzurg"),
    "farmer": ("farmer", "kisan", "किसान"),
    "unemployed": ("unemployed", "no job", "berozgar", "बेरोज़गार"),
}
_INTENT_WORDS: list[tuple[Intent, tuple[str, ...]]] = [
    ("compare", ("compare", "difference", "vs", "तुलना")),
    ("documents", ("document", "documents", "kagaz", "दस्तावेज़", "कागज़")),
    ("eligibility", ("eligible", "eligibility", "qualify", "patra", "पात्र", "yogya")),
    ("complaint", ("complaint", "shikayat", "शिकायत", "rti")),
    ("info", ("how", "what", "kaise", "kya", "कैसे", "क्या", "apply", "fee")),
]


class StubProvider:
    """Keyword and regex extraction. Good enough to exercise the pipeline offline."""

    name = "stub"

    def understand(self, text: str) -> Understanding:
        t = text.casefold()
        facts = ExtractedFacts()
        if "delhi" in t or "दिल्ली" in text or "dilli" in t:
            facts.state_of_residence = "Delhi"
        if m := _LAKH.search(t):
            facts.annual_family_income_inr = int(float(m.group(1)) * 100_000)
        elif m := _RUPEES.search(t):
            facts.annual_family_income_inr = int(m.group(1).replace(",", ""))
        for occ, words in _OCCUPATIONS.items():
            if any(w in t for w in words):
                facts.occupation = occ
                break
        intent: Intent = "find"
        for name, words in _INTENT_WORDS:
            if any(re.search(rf"(?<!\w){re.escape(w)}(?!\w)", t) for w in words):
                intent = name
                break
        return Understanding(intent=intent, facts=facts, service_query=text)


class LLM:
    def __init__(self, provider: Provider | None = None) -> None:
        settings = get_settings()
        if provider is None:
            # Gemini provider is added in S0-07; until then always use the stub.
            provider = StubProvider()
        self.provider = provider
        self.live = bool(settings.gemini_api_key) and provider.name != "stub"

    def understand(self, text: str) -> Understanding:
        """Intent + profile facts. Facts returned here are unconfirmed."""
        return self.provider.understand(text)
