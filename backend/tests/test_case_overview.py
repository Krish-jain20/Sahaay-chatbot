from datetime import date, timedelta

from app.rules.case_overview import follow_up, merge_documents, overview
from app.rules.journey import journey
from app.rules.readiness import readiness

PENSION = "delhi-old-age-pension"
TODAY = date(2026, 11, 24)


# ---- pure rules ---------------------------------------------------------------------------


def test_merge_prefers_scanned_then_newest():
    docs = [
        {"doc_type": "aadhaar", "fields": {}, "confirmed_at": "2026-01-01"},
        {"doc_type": "aadhaar", "fields": {"aadhaar_masked": "XXXX1234"}, "confirmed_at": "2025-01-01"},
        {"doc_type": "passport_photo", "fields": {}, "confirmed_at": "2026-01-01"},
    ]
    merged = {d["doc_type"]: d for d in merge_documents(docs)}
    assert merged["aadhaar"]["fields"]
    assert set(merged) == {"aadhaar", "passport_photo"}


def test_follow_up_uses_user_days_then_scheme_days():
    sub = (TODAY - timedelta(days=20)).isoformat()
    assert follow_up(sub, 10, 45, False, TODAY).due is True
    assert follow_up(sub, None, 45, False, TODAY).due is False
    assert follow_up(sub, None, 45, False, TODAY).days == 45
    assert follow_up(sub, 10, 45, True, TODAY).due is False  # a reply was recorded
    assert follow_up(None, 10, 45, False, TODAY).due is False  # nothing submitted yet
    assert follow_up(sub, None, None, False, TODAY).due_on is None  # unknown timeline: never invented


def test_next_action_order(catalog):
    rec = catalog.services[PENSION]
    ready = readiness(rec, [], TODAY)
    none = journey([])
    assert overview(ready, none, None, {}, 45, TODAY).next_action == "check_eligibility"
    one = journey([{"step": 1, "at": "2026-11-01T00:00:00+00:00"}])
    ov = overview(ready, one, None, {}, 45, TODAY)
    assert ov.next_action == "add_documents" and ov.missing
    all5 = journey([{"step": n, "at": f"2026-11-0{n}T00:00:00+00:00"} for n in range(1, 6)])
    sub = {"submitted_on": (TODAY - timedelta(days=60)).isoformat()}
    assert overview(ready, all5, sub, {}, 45, TODAY).next_action == "follow_up"
    assert overview(ready, all5, sub, {"reply_received": True}, 45, TODAY).next_action == "done"


# ---- API ----------------------------------------------------------------------------------


def _case(client, service=PENSION):
    return client.post("/cases", json={"service_id": service}).json()["id"]


def test_overview_lists_cases_with_links_and_next_action(client):
    _case(client)
    cards = client.get("/cases/overview?lang=en").json()
    assert len(cards) == 1
    c = cards[0]
    assert c["overview"]["next_action"] == "check_eligibility"
    assert c["links"]["draft_kind"] == "pension_delay"
    assert c["service_name"]
    # Every link shown as official is on the allowlist (https, known host).
    assert all(s["url"].startswith("https://") for s in c["links"]["sources"])
    assert c["journey"]["label"] == "your_own_progress"


def test_income_certificate_case_lists_its_form(client):
    _case(client, "delhi-income-certificate")
    c = client.get("/cases/overview").json()[0]
    assert [f["id"] for f in c["links"]["forms"]] == ["delhi-income-certificate-application"]


def test_document_added_in_one_case_ticks_in_another(client):
    a = _case(client)
    b = _case(client, "delhi-income-certificate")
    client.post(f"/cases/{a}/documents", json={"doc_type": "aadhaar", "self_declared": True})
    cards = {c["id"]: c for c in client.get("/cases/overview").json()}
    for cid in (a, b):
        chk = next(x for x in cards[cid]["readiness"]["checks"] if x["doc_type"] == "aadhaar")
        assert chk["status"] == "ok"


def test_follow_up_and_reply(client):
    cid = _case(client)
    r = client.patch(f"/cases/{cid}", json={"follow_up_days": 30})
    assert r.status_code == 200 and r.json()["overview"]["follow_up"]["days"] == 30
    assert r.json()["overview"]["follow_up"]["user_set"] is True
    r = client.patch(f"/cases/{cid}", json={"clear_follow_up": True, "reply_received": True})
    fu = r.json()["overview"]["follow_up"]
    assert fu["user_set"] is False and fu["reply_received"] is True
    assert client.patch(f"/cases/{cid}", json={"follow_up_days": 0}).status_code == 422
    assert client.patch(f"/cases/{cid}", json={"follow_up_days": 9999}).status_code == 422


def test_due_follow_up_suggests_rti_action(client):
    cid = _case(client)
    for n in range(1, 4):
        client.post(f"/cases/{cid}/steps", json={"step": n})
    old = (date.today() - timedelta(days=50)).isoformat()
    client.post(f"/cases/{cid}/steps", json={"step": 4, "submitted_on": old})
    client.post(f"/cases/{cid}/steps", json={"step": 5, "reference": "AB-12345"})
    c = client.get(f"/cases/{cid}").json()
    assert c["overview"]["next_action"] == "follow_up"  # 50 days > the scheme's 45-day timeline


def test_notes_are_masked_limited_and_deletable(client):
    cid = _case(client)
    r = client.post(f"/cases/{cid}/notes", json={"text": "Called office, my Aadhaar 2345 6789 0124 noted"})
    assert r.status_code == 201
    notes = r.json()["notes"]
    assert len(notes) == 1 and "2345 6789 0124" not in notes[0]["text"] and "6789" not in notes[0]["text"]
    assert client.post(f"/cases/{cid}/notes", json={"text": ""}).status_code == 422
    assert client.post(f"/cases/{cid}/notes", json={"text": "x" * 301}).status_code == 422
    r = client.delete(f"/cases/{cid}/notes/{notes[0]['id']}")
    assert r.json()["notes"] == []


def test_delete_case_and_isolation(client):
    cid = _case(client)
    assert client.delete(f"/cases/{cid}").json() == {"ok": True}
    assert client.get(f"/cases/{cid}").status_code == 404
    assert client.delete(f"/cases/{cid}").status_code == 404
    assert client.get("/cases/overview").json() == []


def test_export_includes_notes(client):
    cid = _case(client)
    client.post(f"/cases/{cid}/notes", json={"text": "Visited the office"})
    data = client.get("/me/data").json()
    assert data["cases"][0]["notes"][0]["text"] == "Visited the office"
