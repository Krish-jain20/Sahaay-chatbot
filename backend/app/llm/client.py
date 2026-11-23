"""The single LLM wrapper. No other module may import a provider SDK.

- Gemini via google-genai when GEMINI_API_KEY is set; otherwise an offline stub,
  so the app always runs end to end.
- Every request is PII-masked first; uploaded/user text goes inside delimiters.
- Structured output is validated against a Pydantic schema; retries with backoff.
- Per-user rate limit and daily token budget; logs hold sizes and counts only.
"""

from __future__ import annotations

import logging
import re
import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Literal, Protocol, TypeVar

from pydantic import BaseModel, ValidationError

from app.config import Settings, get_settings
from app.safety.pii import mask

log = logging.getLogger("sahaay.llm")
PROMPTS = Path(__file__).parent / "prompts"
M = TypeVar("M", bound=BaseModel)

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
    age: int | None = None
    social_category: str | None = None


class Understanding(BaseModel):
    intent: Intent = "other"
    facts: ExtractedFacts = ExtractedFacts()
    service_query: str | None = None


class VisionResult(BaseModel):
    explanation: str
    field_name: str | None = None
    likely_document: str | None = None


def load_prompt(name: str) -> str:
    return (PROMPTS / f"{name}.md").read_text("utf-8")


# ---------------------------------------------------------------- errors


class LLMError(RuntimeError):
    pass


class BudgetExceeded(LLMError):
    """Daily token budget for this user is used up."""


class RateLimited(LLMError):
    """Too many requests from this user in the last minute."""


# ---------------------------------------------------------------- provider layer


@dataclass
class LLMRequest:
    model: str
    system: str
    text: str
    schema: type[BaseModel] | None = None
    image: bytes | None = None
    image_mime: str = "image/png"


@dataclass
class LLMResponse:
    text: str
    tokens_in: int = 0
    tokens_out: int = 0


class Provider(Protocol):
    name: str

    def generate(self, req: LLMRequest) -> LLMResponse: ...


class GeminiProvider:
    name = "gemini"

    def __init__(self, api_key: str, timeout_s: float = 30.0) -> None:
        from google import genai  # the only provider SDK import in the codebase
        from google.genai import types

        self._types = types
        self._client = genai.Client(
            api_key=api_key, http_options=types.HttpOptions(timeout=int(timeout_s * 1000))
        )

    def generate(self, req: LLMRequest) -> LLMResponse:
        t = self._types
        config: dict[str, Any] = {"system_instruction": req.system, "temperature": 0.2}
        if req.schema is not None:
            config["response_mime_type"] = "application/json"
            config["response_schema"] = req.schema
        contents: list[Any] = [req.text]
        if req.image is not None:
            contents.insert(0, t.Part.from_bytes(data=req.image, mime_type=req.image_mime))
        resp = self._client.models.generate_content(
            model=req.model, contents=contents, config=t.GenerateContentConfig(**config)
        )
        usage = resp.usage_metadata
        return LLMResponse(
            text=resp.text or "",
            tokens_in=(usage.prompt_token_count or 0) if usage else 0,
            tokens_out=(usage.candidates_token_count or 0) if usage else 0,
        )


_LAKH = re.compile(r"(\d+(?:\.\d+)?)\s*(?:lakh|lac|लाख)", re.I)
_RUPEES = re.compile(r"(?:₹|rs\.?|inr)\s*([\d,]{4,})", re.I)
_AGE = re.compile(
    r"(?:\b(?:age|aged|umar|umra)\s*(?:is\s*)?(\d{2,3})\b|\b(\d{2,3})\s*(?:years?|yrs?|saal|साल|वर्ष))", re.I
)
_OCCUPATIONS = {
    "student": ("student", "studying", "college", "छात्र", "padhai", "padhta", "padhti"),
    "retired": ("retired", "रिटायर"),
    "farmer": ("farmer", "kisan", "किसान"),
    "unemployed": ("unemployed", "no job", "berozgar", "बेरोज़गार"),
}
_CATEGORIES = {"sc": ("sc", "scheduled caste"), "st": ("st", "scheduled tribe"), "obc": ("obc",)}
_INTENT_WORDS: list[tuple[Intent, tuple[str, ...]]] = [
    ("compare", ("compare", "difference", "vs", "तुलना")),
    ("documents", ("document", "documents", "kagaz", "दस्तावेज़", "कागज़")),
    ("eligibility", ("eligible", "eligibility", "qualify", "patra", "पात्र", "yogya")),
    ("complaint", ("complaint", "shikayat", "शिकायत", "rti")),
    ("info", ("how", "what", "kaise", "kya", "कैसे", "क्या", "apply", "fee")),
]


def _has_word(text: str, w: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(w)}(?!\w)", text) is not None


def stub_understand(text: str) -> Understanding:
    t = text.casefold()
    f = ExtractedFacts()
    if "delhi" in t or "दिल्ली" in text or "dilli" in t:
        f.state_of_residence = "Delhi"
    if m := _LAKH.search(t):
        f.annual_family_income_inr = int(float(m.group(1)) * 100_000)
    elif m := _RUPEES.search(t):
        f.annual_family_income_inr = int(m.group(1).replace(",", ""))
    if (m := _AGE.search(t)) and 0 < int(m.group(1) or m.group(2)) < 120:
        f.age = int(m.group(1) or m.group(2))
    for occ, words in _OCCUPATIONS.items():
        if any(w in t for w in words):
            f.occupation = occ
            break
    for cat, words in _CATEGORIES.items():
        if any(_has_word(t, w) for w in words):
            f.social_category = cat
            break
    intent: Intent = "find"
    for name, words in _INTENT_WORDS:
        if any(_has_word(t, w) for w in words):
            intent = name
            break
    return Understanding(intent=intent, facts=f, service_query=text)


class StubProvider:
    """Offline provider: regex extraction for Understanding, a fixed note otherwise."""

    name = "stub"

    def generate(self, req: LLMRequest) -> LLMResponse:
        if req.schema is Understanding:
            body = re.sub(r"^<message>\n?|\n?</message>$", "", req.text)
            return LLMResponse(stub_understand(body).model_dump_json())
        if req.schema is not None:
            raise LLMError("stub provider cannot produce this schema")
        return LLMResponse("NO_SOURCE")


# ---------------------------------------------------------------- limits


@dataclass
class Limits:
    per_minute: int
    daily_tokens: int
    clock: Callable[[], float] = time.monotonic
    today: Callable[[], date] = date.today
    _hits: dict[str, deque[float]] = field(default_factory=lambda: defaultdict(deque))
    _used: dict[tuple[str, date], int] = field(default_factory=lambda: defaultdict(int))
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def check(self, user_id: str) -> None:
        with self._lock:
            if self._used[(user_id, self.today())] >= self.daily_tokens:
                raise BudgetExceeded("daily token budget used up")
            now = self.clock()
            hits = self._hits[user_id]
            while hits and now - hits[0] > 60:
                hits.popleft()
            if len(hits) >= self.per_minute:
                raise RateLimited("too many requests, try again in a minute")
            hits.append(now)

    def record(self, user_id: str, tokens: int) -> None:
        with self._lock:
            self._used[(user_id, self.today())] += tokens

    def used(self, user_id: str) -> int:
        return self._used[(user_id, self.today())]


# ---------------------------------------------------------------- wrapper


class LLM:
    def __init__(
        self,
        provider: Provider | None = None,
        settings: Settings | None = None,
        retries: int = 2,
        backoff_s: float = 0.5,
    ) -> None:
        self.settings = settings or get_settings()
        if provider is None:
            key = self.settings.gemini_api_key
            provider = GeminiProvider(key) if key else StubProvider()
        self.provider = provider
        self.live = provider.name != "stub"
        self.retries = retries
        self.backoff_s = backoff_s
        self.limits = Limits(self.settings.llm_requests_per_minute, self.settings.daily_token_budget)

    # -- core
    def _call(self, user_id: str, req: LLMRequest) -> LLMResponse:
        self.limits.check(user_id)
        req.text = mask(req.text)
        last: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                started = time.monotonic()
                resp = self.provider.generate(req)
                self.limits.record(user_id, resp.tokens_in + resp.tokens_out)
                if req.schema is not None:
                    req.schema.model_validate_json(resp.text)  # raises on bad output
                log.info(
                    "llm call provider=%s model=%s chars_in=%d tokens_in=%d tokens_out=%d ms=%d",
                    self.provider.name,
                    req.model,
                    len(req.text),
                    resp.tokens_in,
                    resp.tokens_out,
                    (time.monotonic() - started) * 1000,
                )
                return resp
            except (BudgetExceeded, RateLimited):
                raise
            except (ValidationError, Exception) as e:  # noqa: BLE001 - provider errors vary
                last = e
                log.warning("llm attempt %d failed: %s", attempt + 1, type(e).__name__)
                if attempt < self.retries:
                    time.sleep(self.backoff_s * (2**attempt))
        raise LLMError(f"LLM call failed after {self.retries + 1} attempts") from last

    # -- public API (docs/ARCHITECTURE.md §4)
    def extract(self, text: str, schema: type[M], *, user_id: str, system: str | None = None) -> M:
        req = LLMRequest(
            model=self.settings.llm_model_fast,
            system=system or load_prompt("understand"),
            text=f"<message>\n{text}\n</message>",
            schema=schema,
        )
        return schema.model_validate_json(self._call(user_id, req).text)

    def understand(self, text: str, *, user_id: str = "anonymous") -> Understanding:
        """Intent + profile facts (unconfirmed). Falls back to the offline stub if the model fails."""
        try:
            return self.extract(text, Understanding, user_id=user_id)
        except LLMError:
            if not self.live:
                raise
            log.warning("understand fell back to stub")
            return stub_understand(mask(text))

    def explain(self, term_or_text: str, context: dict[str, Any], lang: str, *, user_id: str) -> str | None:
        """Glossary-grounded explanation. Returns None when there is no source."""
        req = LLMRequest(
            model=self.settings.llm_model_fast,
            system=load_prompt("explain") + f"\nLanguage: {lang}\nGlossary context: {context}",
            text=f"<document>\n{term_or_text}\n</document>",
        )
        out = self._call(user_id, req).text.strip()
        return None if out == "NO_SOURCE" or not out else out

    def vision(
        self, image: bytes, question: str, lang: str, *, user_id: str, mime: str = "image/png"
    ) -> VisionResult:
        req = LLMRequest(
            model=self.settings.llm_model_fast,
            system=load_prompt("vision") + f"\nLanguage: {lang}",
            text=f"<document>\n{question}\n</document>",
            schema=VisionResult,
            image=image,
            image_mime=mime,
        )
        return VisionResult.model_validate_json(self._call(user_id, req).text)

    def draft(self, kind: str, facts: dict[str, Any], lang: str, *, user_id: str) -> str:
        req = LLMRequest(
            model=self.settings.llm_model_strong,
            system=load_prompt("draft").replace("{kind}", kind) + f"\nLanguage: {lang}",
            text=f"<facts>\n{facts}\n</facts>",
        )
        return self._call(user_id, req).text
