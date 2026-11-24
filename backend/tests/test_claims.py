import pytest

from app.safety.claims import find_violations


@pytest.mark.parametrize(
    "text",
    [
        "Your application has been approved.",
        "You will be approved within a week.",
        "Approval is guaranteed.",
        "आपका आवेदन मंज़ूर हो जाएगा।",
        "Aapka application approve ho jayega.",
        "This certificate is genuine.",
    ],
)
def test_forbidden_claims_are_caught(text):
    assert find_violations(text)


@pytest.mark.parametrize(
    "text",
    [
        "This is not an approval.",
        "Based on what you confirmed, you meet the listed conditions. This is not an approval.",
        "यह मंज़ूरी नहीं है।",
        "Yeh approval nahi hai.",
    ],
)
def test_honest_wording_passes(text):
    assert not find_violations(text)


def test_all_service_data_is_clean(client):
    catalog = client.app.state.catalog
    for rec in catalog.services.values():
        for lang in ("en", "hi", "hn"):
            blob = " ".join([rec.summary.get(lang) or "", rec.benefit.amount_text.get(lang) or ""])
            assert not find_violations(blob), (rec.id, lang)


def test_compose_blocks_a_planted_approved(client, monkeypatch):
    import app.graph.graph as g

    monkeypatch.setattr(
        g,
        "t",
        lambda key, lang, **kw: (
            "Your application has been approved."
            if key == "answer.found"
            else __import__("app.graph.templates", fromlist=["t"]).t(key, lang, **kw)
        ),
    )
    r = client.post("/chat", json={"message": "income certificate", "language": "en"})
    import json
    import re

    tokens = re.findall(r"event: token\r\ndata: (\{.*?\})\r\n", r.text)
    said = "".join(json.loads(x)["text"] for x in tokens)
    assert "approved" not in said
    assert "official page" in said
