import re

from app.config import get_settings
from app.data.guidance import load_guidance


def test_guidance_endpoint_is_sourced_in_every_language(client):
    for lang in ("en", "hi", "hn"):
        r = client.get("/guidance/complaints", params={"lang": lang})
        assert r.status_code == 200
        card = r.json()
        assert {p["id"] for p in card["points"]} >= {"grievance", "appeal", "rti"}
        for p in card["points"]:
            assert p["heading"] and p["body"]
            assert any(c["n"] == p["source_n"] for c in card["citations"])
        for c in card["citations"]:
            assert c["url"].startswith("https://") and c["date_checked"]


def test_unknown_topic_404(client):
    assert client.get("/guidance/nope").status_code == 404


def test_rti_point_warns_delhi_is_not_on_the_central_portal(client):
    body = client.get("/guidance/complaints").json()
    rti = next(p for p in body["points"] if p["id"] == "rti")
    assert "Delhi" in rti["body"] and "verify locally" in rti["body"].lower()


def test_loader_rejects_unallowlisted_source(tmp_path, catalog):
    import json

    d = tmp_path
    src = get_settings().data_dir / "guidance.json"
    data = json.loads(src.read_text("utf-8"))
    data["sources"][0]["url"] = "https://pgportal.gov.in.evil.example/"
    (d / "guidance.json").write_text(json.dumps(data), "utf-8")
    try:
        load_guidance(d, catalog.allowlist)
    except Exception as e:
        assert "allowlist" in str(e)
    else:
        raise AssertionError("expected DataError")


def test_chat_complaint_question_returns_guide_card_not_a_refusal(client):
    r = client.post("/chat", json={"message": "how is RTI different from a complaint", "language": "en"})
    assert "event: card" in r.text
    assert '"type": "guide"' in r.text
    assert '"refused": false' in r.text
    assert re.search(r"event: citation", r.text)


def test_scam_topic_cites_official_fee_pages_and_marks_sahaay_statements(client):
    for lang in ("en", "hi", "hn"):
        card = client.get("/guidance/scams", params={"lang": lang}).json()
        ids = {p["id"]: p for p in card["points"]}
        assert {"income_fee", "grievance_fee", "sahaay_never"} <= set(ids)
        assert ids["income_fee"]["source_n"] and ids["grievance_fee"]["source_n"]
        # statements about Sahaay itself carry no external source and make no fee claim
        assert ids["sahaay_never"]["source_n"] is None
        assert all(c["url"].startswith("https://") for c in card["citations"])
    en = client.get("/guidance/scams").json()
    assert "NO FEE Required" in next(p for p in en["points"] if p["id"] == "income_fee")["body"]


def test_unsourced_point_must_be_about_sahaay(tmp_path, catalog):
    import json

    from app.data.guidance import load_guidance

    data = json.loads((get_settings().data_dir / "guidance.json").read_text("utf-8"))
    data["topics"][1]["points"][0]["source_ref"] = None
    data["topics"][1]["points"][0]["about_sahaay"] = False
    (tmp_path / "guidance.json").write_text(json.dumps(data), "utf-8")
    try:
        load_guidance(tmp_path, catalog.allowlist)
    except Exception as e:
        assert "no source" in str(e)
    else:
        raise AssertionError("expected DataError")


def test_chat_scam_question_returns_scam_guide(client):
    r = client.post(
        "/chat",
        json={"message": "an agent is asking money for income certificate, is it fraud?", "language": "en"},
    )
    assert '"id": "scams"' in r.text and '"refused": false' in r.text
