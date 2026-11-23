import json


def _events(client, **body):
    events = []
    with client.stream("POST", "/chat", json=body) as r:
        assert r.status_code == 200
        name = None
        for line in r.iter_lines():
            if line.startswith("event:"):
                name = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                events.append((name, json.loads(line.split(":", 1)[1])))
    return events


def test_streams_card_tokens_and_citation(client):
    ev = _events(client, message="How do I get an income certificate in Delhi?", language="en")
    names = [n for n, _ in ev]
    assert "card" in names and "token" in names and "citation" in names
    assert names[-1] == "done"
    card = next(d for n, d in ev if n == "card")
    assert card["service"]["id"] == "delhi-income-certificate"
    # Fact stated in chat is unconfirmed, so eligibility is unknown, and a confirm chip is offered.
    assert card["eligibility"]["verdict"] == "incomplete"
    chips = next(d for n, d in ev if n == "chips")["chips"]
    assert chips[0]["confirm"] == {"state_of_residence": "Delhi"}
    # Unverified fees are null (rendered as "Verify locally"), never invented.
    assert card["fee_strip"]["official_fee_inr"] is None
    text = "".join(d["text"] for n, d in ev if n == "token")
    assert "[1]" in text and "₹[" not in text


def test_confirmed_fact_gives_verdict(client):
    ev = _events(
        client, message="income certificate", language="hn", confirmed_facts={"state_of_residence": "Delhi"}
    )
    card = next(d for n, d in ev if n == "card")
    assert card["eligibility"]["verdict"] == "likely"
    assert card["eligibility"]["rules"][0]["label"] == "Delhi ka nivasi"


def test_refuses_without_source(client):
    ev = _events(client, message="tell me about passport renewal", language="en")
    assert not any(n == "card" for n, _ in ev)
    assert ev[-1] == ("done", {"refused": True})
