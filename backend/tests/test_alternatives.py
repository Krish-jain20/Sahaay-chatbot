import json
import re


def _card(client, message, facts):
    r = client.post("/chat", json={"message": message, "language": "en", "confirmed_facts": facts})
    m = re.search(r"event: card\r\ndata: (\{.*?\})\r\n\r\n", r.text, re.S)
    assert m, r.text[:300]
    return json.loads(m.group(1))


def test_alternatives_exclude_ruled_out_and_prerequisite_services(client):
    facts = {
        "state_of_residence": "Delhi",
        "age": 65,
        "years_resident_in_state": 10,
        "annual_family_income_inr": 90000,
    }
    card = _card(client, "old age pension", facts)
    alts = card["alternatives"]
    assert alts and len(alts) <= 3
    assert all(a["id"] != card["service"]["id"] for a in alts)
    assert all(a["verdict"] in {"likely", "incomplete"} for a in alts)


def test_scholarship_card_does_not_offer_its_own_prerequisite_as_alternative(client):
    card = _card(client, "SC ST OBC merit scholarship", {"state_of_residence": "Delhi"})
    prereq = {p["id"] for p in card["prerequisites"]}
    assert prereq
    assert not prereq & {a["id"] for a in card["alternatives"]}


def test_unknown_facts_are_never_reported_as_likely(client):
    card = _card(client, "income certificate", {})
    assert all(a["verdict"] != "likely" for a in card["alternatives"])


def test_card_carries_sourced_grievance_channels(client):
    card = _card(client, "SC ST OBC merit scholarship", {})
    ch = card["grievance"]
    assert {c["type"] for c in ch} >= {"cpgrams", "state_portal", "helpline"}
    assert all(c["source_n"] for c in ch)
