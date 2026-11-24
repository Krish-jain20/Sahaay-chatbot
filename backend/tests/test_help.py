"""Help and rights: sourced cards, matching, guarded AI ask with fallbacks, and situation answers."""

import re

from app.config import get_settings
from app.llm.client import LLM, LLMRequest, LLMResponse, SearchHit, StubProvider, stub_understand

SRC = [
    {"title": "pgportal.gov.in", "url": "https://v.example/1"},
    {"title": "someblog.com", "url": "https://v.example/2"},
]


class Fake:
    """Routes by which prompt it was given and records every request."""

    name = "fake"

    def __init__(self, web=None, cards=None, situation=None, explain="Plain words. Verify locally."):
        self.web, self.cards, self.situation, self.explain = web, cards, situation, explain
        self.requests: list[LLMRequest] = []

    def generate(self, req: LLMRequest) -> LLMResponse:
        self.requests.append(req)
        sys = req.system or ""
        if "describes their own situation" in sys:
            return LLMResponse(self.situation or "NO_SOURCE", 10, 10, SRC if req.web else [])
        if "Matching cards from Sahaay" in sys:
            return LLMResponse(self.cards or "NO_SOURCE", 10, 10)
        if "explain one card" in sys or "explains one card" in sys:
            return LLMResponse(self.explain, 10, 10)
        if req.web or "<results>" in req.text:
            return LLMResponse(self.web or "NO_SOURCE", 10, 10, SRC if req.web else [])
        body = re.sub(r"^<message>\n?|\n?</message>$", "", req.text)
        return LLMResponse(stub_understand(body).model_dump_json())


def _use(client, provider, enabled=True, searcher=None):
    s = get_settings().model_copy(
        update={"web_search_enabled": enabled, "web_search_provider": "tavily" if searcher else "google"}
    )
    client.app.state.llm = LLM(provider=provider, settings=s, searcher=searcher)


def _ask(client, q, lang="en"):
    r = client.post("/help/ask", json={"question": q, "language": lang})
    assert r.status_code == 200
    return r.json()


def _searcher(sent):
    def search(query, domains):
        sent.append((query, domains))
        return [
            SearchHit("Pension", "https://swd.delhi.example.gov.in/p", "Rejected forms can be corrected."),
            SearchHit("Rules", "https://pgportal.gov.in/r", "Grievances can be filed on CPGRAMS."),
        ]

    return search


def test_sections_are_the_three_sourced_topics(client):
    body = client.get("/help?lang=hi").json()
    assert [s["id"] for s in body["sections"]] == ["complaints", "scams", "terms"]
    for s in body["sections"]:
        assert s["points"] and s["citations"]


def test_the_four_example_questions_match_the_right_cards(client):
    cases = {
        "How do I file an RTI?": "complaints.rti",
        "an agent wants money for my certificate": "scams.income_fee",
        "what does registration ID mean": "terms.registration_id",
    }
    for q, want in cases.items():
        assert want in _ask(client, q)["matches"], q
    assert _ask(client, "my pension form was rejected")["matches"] is not None


def test_ask_offline_still_answers_from_the_matching_card(client):
    body = _ask(client, "How do I file an RTI?")
    assert body["basis"] == "card_text" and body["web"] is None
    assert body["answer"] and "RTI" in body["answer"]
    assert any(m.endswith(".rti") for m in body["matches"])


def test_ask_with_no_web_result_answers_from_cards_and_labelled_general_guidance(client):
    p = Fake(cards="Cards: RTI is for records. General guidance (not from an official page): ask in writing.")
    _use(client, p)
    body = _ask(client, "How do I file an RTI?")
    assert body["basis"] == "cards" and "ask in writing" in body["answer"]
    sent = [r for r in p.requests if "Matching cards" in (r.system or "")][0]
    assert "<cards>" in sent.text and "RTI" in sent.text


def test_ask_answers_from_web_with_sources_and_guards(client):
    p = Fake(web="File it on the RTI portal. Verify locally. https://x.example")
    _use(client, p)
    body = _ask(client, "RTI kaise karein 2345 6789 0124", "hn")
    assert body["basis"] == "web" and "RTI portal" in body["answer"] and "http" not in body["answer"]
    assert {s["title"]: s["official"] for s in body["web"]["sources"]}["someblog.com"] is False
    assert "2345 6789 0124" not in p.requests[0].text


def test_ask_sends_the_question_first_with_only_a_short_place_hint(client):
    p = Fake(web="Use the Delhi RTI portal. Verify locally.")
    _use(client, p)
    _ask(client, "How do I file an RTI in Delhi?")
    assert "<question>\nHow do I file an RTI in Delhi? (Delhi, India)\n</question>" in p.requests[0].text


def test_ask_blocked_web_and_card_answers_fall_back_to_the_card_text(client):
    _use(client, Fake(web="Your complaint will be approved.", cards="It is guaranteed to work."))
    body = _ask(client, "How do I file an RTI?")
    assert body["basis"] == "card_text" and "approved" not in body["answer"]


def test_ask_with_no_card_and_no_ai_is_honest(client):
    body = _ask(client, "zzzz qqqq")
    assert body["answer"] is None and body["basis"] == "none"


def test_situation_answer_uses_the_card_and_a_web_lookup_with_sources(client):
    sent = []
    p = Fake(situation="1. Check the reason for rejection. 2. Fix it and reapply. Verify locally.")
    _use(client, p, searcher=_searcher(sent))
    r = client.post(
        "/help/explain",
        json={"card_id": "scams.income_fee", "language": "en", "situation": "my pension form was rejected"},
    )
    assert r.status_code == 200
    body = r.json()
    assert "reapply" in body["text"] and body["basis"] == "web"
    assert body["web"]["retrieved_on"] and len(body["web"]["sources"]) == 2
    assert sent[0][0] == "my pension form was rejected (Delhi, India)"
    req = [x for x in p.requests if "describes their own situation" in (x.system or "")][0]
    assert "<card>" in req.text and "<results>" in req.text and "<situation>" in req.text


def test_situation_answer_without_web_still_answers_from_card_and_general_guidance(client):
    p = Fake(situation="General guidance (not from an official page): ask for the reason in writing.")
    _use(client, p, enabled=False)
    r = client.post(
        "/help/explain",
        json={"card_id": "complaints.rti", "language": "en", "situation": "my pension form was rejected"},
    )
    assert r.status_code == 200 and r.json()["basis"] == "card" and r.json()["web"] is None
    assert "<results>" not in [x for x in p.requests if x.web is False][-1].text


def test_situation_is_masked_before_it_leaves(client):
    sent = []
    p = Fake(situation="Do this. Verify locally.")
    _use(client, p, searcher=_searcher(sent))
    client.post(
        "/help/explain",
        json={"card_id": "complaints.rti", "situation": "my phone is 9876543210 and form rejected"},
    )
    assert "9876543210" not in sent[0][0]
    assert all("9876543210" not in r.text for r in p.requests)


def test_explain_without_situation_is_the_card_in_plain_words(client):
    p = Fake()
    _use(client, p)
    r = client.post("/help/explain", json={"card_id": "complaints.rti", "language": "en"})
    assert r.status_code == 200 and "Plain words" in r.json()["text"]


def test_explain_unknown_card_unavailable_and_blocked(client):
    _use(client, Fake())
    assert client.post("/help/explain", json={"card_id": "nope.x"}).status_code == 404
    _use(client, StubProvider())
    assert client.post("/help/explain", json={"card_id": "complaints.rti"}).status_code == 503
    _use(client, Fake(situation="You are guaranteed a reply."))
    r = client.post("/help/explain", json={"card_id": "complaints.rti", "situation": "stuck"})
    assert r.status_code == 503
