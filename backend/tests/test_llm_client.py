import os
from datetime import date

import pytest
from pydantic import BaseModel

from app.config import Settings
from app.llm.client import (
    LLM,
    BudgetExceeded,
    LLMError,
    LLMRequest,
    LLMResponse,
    RateLimited,
    StubProvider,
    Understanding,
)


class Fake:
    name = "fake"

    def __init__(self, replies, tokens=10):
        self.replies = list(replies)
        self.requests: list[LLMRequest] = []
        self.tokens = tokens

    def generate(self, req):
        self.requests.append(req)
        r = self.replies.pop(0)
        if isinstance(r, Exception):
            raise r
        return LLMResponse(r, self.tokens, self.tokens)


class Out(BaseModel):
    answer: str


def make(provider, **kw):
    s = Settings(
        gemini_api_key="",
        daily_token_budget=kw.pop("budget", 1000),
        llm_requests_per_minute=kw.pop("rpm", 100),
    )
    return LLM(provider, settings=s, backoff_s=0, **kw)


def test_structured_output_validated():
    llm = make(Fake(['{"answer": "ok"}']))
    assert llm.extract("hi", Out, user_id="u").answer == "ok"


def test_retries_bad_json_then_succeeds():
    fake = Fake(["not json", TimeoutError(), '{"answer": "ok"}'])
    assert make(fake, retries=2).extract("hi", Out, user_id="u").answer == "ok"
    assert len(fake.requests) == 3


def test_gives_up_with_clear_error():
    with pytest.raises(LLMError):
        make(Fake(["bad", "bad"]), retries=1).extract("hi", Out, user_id="u")


def test_pii_masked_before_provider_sees_it():
    fake = Fake(['{"answer": "ok"}'])
    make(fake).extract("my aadhaar 2345 6789 0124 and phone 9876543210", Out, user_id="u")
    sent = fake.requests[0].text
    assert "234567890124" not in sent and "2345 6789 0124" not in sent and "9876543210" not in sent
    assert "<message>" in sent  # user text is delimited


def test_daily_token_budget():
    llm = make(Fake(['{"answer": "a"}'] * 5, tokens=300), budget=1000)
    llm.extract("x", Out, user_id="u")  # 600 used
    llm.extract("x", Out, user_id="u")  # 1200 used
    with pytest.raises(BudgetExceeded):
        llm.extract("x", Out, user_id="u")
    llm.extract("x", Out, user_id="someone-else")  # budgets are per user


def test_budget_resets_next_day():
    llm = make(Fake(['{"answer": "a"}'] * 3, tokens=600), budget=1000)
    day = [date(2026, 11, 23)]
    llm.limits.today = lambda: day[0]
    llm.extract("x", Out, user_id="u")
    with pytest.raises(BudgetExceeded):
        llm.extract("x", Out, user_id="u")
    day[0] = date(2026, 11, 24)
    llm.extract("x", Out, user_id="u")


def test_rate_limit_per_minute():
    llm = make(Fake(['{"answer": "a"}'] * 5), rpm=2)
    now = [0.0]
    llm.limits.clock = lambda: now[0]
    llm.extract("x", Out, user_id="u")
    llm.extract("x", Out, user_id="u")
    with pytest.raises(RateLimited):
        llm.extract("x", Out, user_id="u")
    now[0] = 61.0
    llm.extract("x", Out, user_id="u")


def test_explain_no_source_returns_none():
    assert make(Fake(["NO_SOURCE"])).explain("khatauni", {}, "en", user_id="u") is None


def test_draft_uses_strong_model():
    fake = Fake(["Dear Sir"])
    llm = make(fake)
    assert llm.draft("complaint", {"name": "A"}, "en", user_id="u") == "Dear Sir"
    assert fake.requests[0].model == llm.settings.llm_model_strong


@pytest.mark.parametrize(
    ("text", "facts"),
    [
        (
            "I'm a student in Delhi, family income about 3 lakh",
            {"state_of_residence": "Delhi", "occupation": "student", "annual_family_income_inr": 300000},
        ),
        ("meri umar 65 saal hai, dilli mein rehta hoon", {"age": 65, "state_of_residence": "Delhi"}),
        ("main OBC hoon, college mein padhta hoon", {"social_category": "obc", "occupation": "student"}),
        ("मैं दिल्ली में रहता हूँ, आय 2 लाख", {"state_of_residence": "Delhi", "annual_family_income_inr": 200000}),
    ],
)
def test_stub_understand(text, facts):
    u = make(StubProvider()).understand(text)
    assert isinstance(u, Understanding)
    got = {k: v for k, v in u.facts.model_dump().items() if v is not None}
    assert got == facts


@pytest.mark.skipif(not os.getenv("GEMINI_API_KEY"), reason="live smoke test needs GEMINI_API_KEY")
def test_live_gemini_smoke():
    llm = LLM()
    assert llm.live
    u = llm.understand("I am a student in Delhi, family income 2 lakh")
    assert u.facts.state_of_residence == "Delhi"
