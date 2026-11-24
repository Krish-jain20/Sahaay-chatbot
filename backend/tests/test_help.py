"""Help and rights: sourced cards, matching, guarded AI ask, and card-grounded explanations."""

import re

from app.config import get_settings
from app.llm.client import LLM, LLMRequest, LLMResponse, StubProvider, stub_understand

SRC = [
    {"title": "pgportal.gov.in", "url": "https://v.example/1"},
    {"title": "someblog.com", "url": "https://v.example/2"},
]


class Fake:
    name = "fake"

    def __init__(self, answer):
        self.answer = answer
        self.requests: list[LLMRequest] = []

    def generate(self, req: LLMRequest) -> LLMResponse:
        self.requests.append(req)
        if req.web:
            return LLMResponse(self.answer, 10, 10, SRC)
        if req.system and "help page" in req.system:
            return LLMResponse(self.answer, 10, 10)
        body = re.sub(r"^<message>\n?|\n?</message>$", "", req.text)
        return LLMResponse(stub_understand(body).model_dump_json())


def _use(client, provider, enabled=True):
    s = get_settings().model_copy(update={"web_search_enabled": enabled, "web_search_provider": "google"})
    client.app.state.llm = LLM(provider=provider, settings=s)


def test_sections_are_the_three_sourced_topics(client):
    body = client.get("/help?lang=hi").json()
    assert [s["id"] for s in body["sections"]] == ["complaints", "scams", "terms"]
    for s in body["sections"]:
        assert s["points"] and s["citations"]


def test_ask_matches_cards_even_offline(client):
    r = client.post("/help/ask", json={"question": "how do I file an RTI?", "language": "en"})
    assert r.status_code == 200
    body = r.json()
    assert body["answer"] is None and body["state"] == "unavailable"
    assert any(m.endswith(".rti") for m in body["matches"])


def test_ask_answers_from_web_with_sources_and_guards(client):
    p = Fake("File it on the RTI portal. Verify locally. https://x.example")
    _use(client, p)
    q = {"question": "RTI kaise karein 2345 6789 0124", "language": "hn"}
    body = client.post("/help/ask", json=q).json()
    assert body["state"] == "ok" and "RTI portal" in body["answer"] and "http" not in body["answer"]
    assert {s["title"]: s["official"] for s in body["web"]["sources"]}["someblog.com"] is False
    assert "2345 6789 0124" not in p.requests[0].text


def test_ask_blocks_forbidden_claims(client):
    _use(client, Fake("Your complaint will be approved."))
    body = client.post("/help/ask", json={"question": "complaint status", "language": "en"}).json()
    assert body["answer"] is None and body["state"] == "blocked"


def test_explain_uses_only_the_card_and_masks_the_situation(client):
    p = Fake("It is a way to ask a department for records. Verify locally.")
    _use(client, p)
    r = client.post(
        "/help/explain",
        json={"card_id": "complaints.rti", "language": "en", "situation": "my phone is 9876543210"},
    )
    assert r.status_code == 200 and "records" in r.json()["text"]
    sent = p.requests[0]
    assert "9876543210" not in sent.text and "<card>" in sent.text and not sent.web


def test_explain_unknown_card_and_unavailable_and_blocked(client):
    _use(client, Fake("x"))
    assert client.post("/help/explain", json={"card_id": "nope.x"}).status_code == 404
    _use(client, StubProvider())
    assert client.post("/help/explain", json={"card_id": "complaints.rti"}).status_code == 503
    _use(client, Fake("You are guaranteed a reply."))
    assert client.post("/help/explain", json={"card_id": "complaints.rti"}).status_code == 503
