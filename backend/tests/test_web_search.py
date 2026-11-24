"""Web search fallback: only when no verified record matches, labelled, sourced, and still guarded."""

import json
import re

from app.config import get_settings
from app.llm.client import LLM, LLMRequest, LLMResponse, StubProvider, stub_understand


class FakeWeb:
    """Understands like the stub; answers web requests from a script and records what it was sent."""

    name = "fake"

    def __init__(self, answer, sources=None):
        self.answer = answer
        self.sources = sources if sources is not None else []
        self.web_requests: list[LLMRequest] = []

    def generate(self, req: LLMRequest) -> LLMResponse:
        if req.web:
            self.web_requests.append(req)
            return LLMResponse(self.answer, 10, 10, self.sources)
        body = re.sub(r"^<message>\n?|\n?</message>$", "", req.text)
        return LLMResponse(stub_understand(body).model_dump_json())


def _ask(client, provider, message, enabled=True):
    s = get_settings().model_copy(update={"web_search_enabled": enabled})
    client.app.state.llm = LLM(provider=provider, settings=s)
    r = client.post("/chat", json={"message": message, "language": "en"})
    events = re.findall(r"event: (\w+)\r\ndata: (.*?)\r\n\r\n", r.text, re.S)
    said = "".join(json.loads(d)["text"] for e, d in events if e == "token")
    cards = [json.loads(d) for e, d in events if e == "card"]
    done = [json.loads(d) for e, d in events if e == "done"]
    return said, cards, done


SRC = [
    {"title": "revenue.delhi.gov.in", "url": "https://vertexaisearch.example/redirect/1"},
    {"title": "somefakeblog.com", "url": "https://vertexaisearch.example/redirect/2"},
    {"title": "revenue.delhi.gov.in", "url": "https://vertexaisearch.example/redirect/3"},
]


def test_unknown_service_gets_labelled_web_answer_with_official_flags(client):
    p = FakeWeb(
        "The page says the domicile certificate needs proof of stay. Verify locally. See https://x.example/a",
        SRC,
    )
    said, cards, done = _ask(client, p, "domicile certificate for Delhi, what documents?")
    assert len(p.web_requests) == 1
    assert "proof of stay" in said and "http" not in said
    card = cards[0]
    assert card["type"] == "web" and "not a verified Sahaay record" in card["label"]
    assert card["retrieved_on"]
    flags = {s["title"]: s["official"] for s in card["sources"]}
    assert flags == {"revenue.delhi.gov.in": True, "somefakeblog.com": False}  # allowlist host only, deduped
    assert done[-1]["refused"] is False


def test_a_verified_record_is_never_replaced_by_the_web(client):
    p = FakeWeb("web answer")
    _, cards, _ = _ask(client, p, "income certificate")
    assert p.web_requests == [] and cards[0]["type"] == "service"


def test_forbidden_claim_in_web_answer_is_blocked(client):
    p = FakeWeb("Your application will be approved within a week.", SRC)
    said, cards, done = _ask(client, p, "some unknown benefit")
    assert "approved" not in said and "official page" in said
    assert not any(c["type"] == "web" for c in cards) and done[-1]["refused"] is True


def test_identity_numbers_never_reach_the_search_provider_or_the_answer(client):
    p = FakeWeb("Use number 2345 6789 0124 for lookups.", SRC)
    said, _, _ = _ask(client, p, "my aadhaar 2345 6789 0124 how to get a ration card?")
    assert "2345 6789 0124" not in p.web_requests[0].text
    assert "2345 6789 0124" not in said


def test_no_source_answer_falls_back_to_the_refusal(client):
    said, cards, done = _ask(client, FakeWeb("NO_SOURCE"), "who won the cricket match")
    assert "don't have verified information" in said and not cards and done[-1]["refused"] is True


def test_web_search_can_be_switched_off(client):
    p = FakeWeb("web answer", SRC)
    said, cards, _ = _ask(client, p, "domicile certificate", enabled=False)
    assert p.web_requests == [] and "don't have verified information" in said


def test_offline_stub_never_searches(client):
    said, cards, _ = _ask(client, StubProvider(), "domicile certificate")
    assert "don't have verified information" in said and not cards


def test_prompt_treats_pages_as_data_and_forbids_promises():
    from app.llm.client import load_prompt

    p = load_prompt("web_search")
    assert "data" in p and "NO_SOURCE" in p and "approved" in p
