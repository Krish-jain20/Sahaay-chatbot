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


def _card(ev):
    return next(d for n, d in ev if n == "card")


def _chips(ev):
    return next((d["chips"] for n, d in ev if n == "chips"), [])


def test_income_certificate_card_tokens_and_citation(client):
    ev = _events(client, message="How do I get an income certificate in Delhi?", language="en")
    names = [n for n, _ in ev]
    assert "token" in names and "citation" in names and names[-1] == "done"
    card = _card(ev)
    assert card["service"]["id"] == "delhi-income-certificate"
    # Stated in chat = unconfirmed, so eligibility stays unknown and a confirm chip is offered.
    assert card["eligibility"]["verdict"] == "incomplete"
    assert _chips(ev)[0]["confirm"] == {"state_of_residence": "Delhi"}
    assert card["fee_strip"]["official_fee_inr"] == 0  # "NO FEE Required" on the official page
    assert card["fee_strip"]["csc_max_inr"] is None  # not stated: "Verify locally"
    text = "".join(d["text"] for n, d in ev if n == "token")
    assert "[1]" in text and "₹[" not in text


def test_acceptance_flow_student_finds_scholarship(client):
    msg = "I'm a student in Delhi, family income about 3 lakh"
    ev = _events(client, message=msg, language="en")
    card = _card(ev)
    assert card["service"]["id"] == "delhi-merit-scholarship-scstobc"
    assert card["prerequisites"] == [{"id": "delhi-income-certificate", "name": "Income Certificate"}]
    confirm = _chips(ev)[0]["confirm"]
    assert confirm == {"occupation": "student"}

    # Confirm, then answer the category question with OBC, then the income question.
    facts = dict(confirm)
    ev = _events(client, message=msg, language="en", confirmed_facts=facts)
    assert [c["confirm"] for c in _chips(ev)][2] == {"social_category": "obc"}
    facts.update(social_category="obc", previous_year_marks_percent=60, annual_family_income_inr=300000)
    ev = _events(client, message=msg, language="en", confirmed_facts=facts)
    assert _card(ev)["eligibility"]["verdict"] == "likely"
    facts["annual_family_income_inr"] = 400000
    assert (
        _card(_events(client, message=msg, confirmed_facts=facts))["eligibility"]["verdict"] == "not_eligible"
    )


def test_sc_student_has_no_income_rule(client):
    facts = {"occupation": "student", "social_category": "sc", "previous_year_marks_percent": 75}
    card = _card(_events(client, message="scholarship", confirmed_facts=facts))
    assert card["eligibility"]["verdict"] == "likely"
    assert all(r["rule_id"] != "r4" for r in card["eligibility"]["rules"])


def test_pension_in_hinglish_with_exclusion(client):
    ev = _events(client, message="meri umar 67 saal hai, budhapa pension chahiye", language="hn")
    card = _card(ev)
    assert card["service"]["id"] == "delhi-old-age-pension"
    assert card["eligibility"]["rules"][0]["label"] == "Umar 60 saal ya zyada"
    facts = {
        "age": 67,
        "years_resident_in_state": 10,
        "annual_family_income_inr": 50000,
        "has_bank_account_linked": True,
    }
    assert (
        _card(_events(client, message="old age pension", confirmed_facts=facts))["eligibility"]["verdict"]
        == "likely"
    )
    facts["receives_pension"] = True
    card = _card(_events(client, message="old age pension", confirmed_facts=facts))
    assert card["eligibility"]["verdict"] == "not_eligible"
    assert card["eligibility"]["exclusions_hit"][0]["id"] == "x1"


def test_refuses_without_source(client):
    ev = _events(client, message="tell me about passport renewal", language="en")
    assert not any(n == "card" for n, _ in ev)
    assert ev[-1] == ("done", {"refused": True})
