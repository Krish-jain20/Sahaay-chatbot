"""Services the user adds themselves, the AI suggestion for them, and the date and to-do list on any case."""

from datetime import date, timedelta

from app.config import get_settings
from app.llm.client import LLM, LLMRequest, LLMResponse, SearchHit, ServiceSuggestion, StubProvider
from app.rules.custom_case import custom_readiness, key_date, merge_document_list

BODY = {
    "name": "Caste certificate",
    "department": "Revenue Department",
    "portal_url": "https://edistrict.delhigovt.nic.in/",
    "documents": ["Aadhaar card", "Address proof", "aadhaar card", "  "],
    "steps": ["Fill the form", "Visit the SDM office"],
    "timeline_days": 21,
}


def _custom(client, **over):
    r = client.post("/cases/custom", json={**BODY, **over})
    assert r.status_code == 201, r.text
    return r.json()


# ---- pure rules


def test_custom_readiness_counts_only_ticked_items_as_declared():
    r = custom_readiness([{"id": "a", "name": "A", "have": True}, {"id": "b", "name": "B", "have": False}])
    assert (r.completed, r.total) == (1, 2)
    assert r.checks[0].evaluated.value == "user_declared"  # never "checked"
    assert r.checks[1].status.value == "missing"


def test_merge_document_list_keeps_ticks_and_drops_duplicates():
    old = [{"id": "x1", "name": "Aadhaar card", "have": True}]
    ids = iter(["n1", "n2"])
    out = merge_document_list(old, ["AADHAAR CARD", "Photo", "photo"], lambda: next(ids))
    assert out == [
        {"id": "x1", "name": "AADHAAR CARD", "have": True},
        {"id": "n1", "name": "Photo", "have": False},
    ]


def test_key_date_days_left_soon_and_passed():
    today = date(2026, 11, 24)
    soon = key_date({"on": "2026-11-27", "kind": "deadline"}, today)
    assert soon and soon.days_left == 3 and soon.soon and not soon.passed
    past = key_date({"on": "2026-11-20", "kind": "bogus"}, today)
    assert past and past.passed and past.kind == "other"
    assert key_date({"on": "not a date"}, today) is None
    assert key_date(None, today) is None


# ---- custom cases through the API


def test_add_custom_case_shows_as_a_card(client):
    card = _custom(client)
    assert card["service_id"] == "custom" and card["service_name"] == "Caste certificate"
    c = card["custom"]
    assert c["label"] == "added_by_you" and c["ai_suggested"] is False
    assert [d["name"] for d in c["documents"]] == ["Aadhaar card", "Address proof"]
    assert card["overview"]["docs_total"] == 2 and card["overview"]["docs_ready"] == 0
    assert card["overview"]["follow_up"]["days"] == 21  # the user's own estimate drives the reminder
    assert [s["text"] for s in card["steps_text"]] == ["Fill the form", "Visit the SDM office"]
    listed = client.get("/cases/overview").json()
    assert [x["id"] for x in listed] == [card["id"]]


def test_two_custom_cases_can_coexist(client):
    a = _custom(client)
    b = _custom(client, name="Ration card")
    assert a["id"] != b["id"]
    assert len(client.get("/cases/overview").json()) == 2


def test_user_link_is_official_only_on_an_exact_allowlist_host(client):
    card = _custom(client, portal_url="https://delhi.gov.in.example.com/apply")
    assert card["custom"]["portal_official"] is False
    assert card["links"]["official_url"] is None
    assert (
        card["custom"]["portal_url"] == "https://delhi.gov.in.example.com/apply"
    )  # kept, as "a link you added"
    host = client.app.state.catalog.allowlist.domains[0].host
    card2 = _custom(client, name="Other", portal_url=f"https://{host}/apply")
    assert card2["custom"]["portal_official"] is True
    assert card2["links"]["official_url"] == f"https://{host}/apply"


def test_bad_link_and_name_are_rejected(client):
    assert client.post("/cases/custom", json={**BODY, "portal_url": "javascript:alert(1)"}).status_code == 422
    assert client.post("/cases/custom", json={**BODY, "name": "x"}).status_code == 422


def test_identity_numbers_and_links_are_removed_from_text(client):
    card = _custom(
        client,
        name="Pension 9876543210",
        documents=["Aadhaar 2345 6789 0124", "Form from https://evil.example/x"],
    )
    text = str(card)
    assert "9876543210" not in text and "2345 6789 0124" not in text
    assert "evil.example" not in str(card["custom"]["documents"])


def test_promises_are_refused(client):
    r = client.post("/cases/custom", json={**BODY, "steps": ["Approval is guaranteed in 3 days"]})
    assert r.status_code == 422


def test_tick_document_and_edit_keeps_ticks(client):
    card = _custom(client)
    doc = card["custom"]["documents"][0]
    r = client.patch(f"/cases/{card['id']}/custom/documents/{doc['id']}", json={"have": True})
    assert r.status_code == 200 and r.json()["overview"]["docs_ready"] == 1
    edited = client.put(
        f"/cases/{card['id']}/custom",
        json={**BODY, "documents": ["Aadhaar card", "Photo"], "name": "Caste cert"},
    ).json()
    docs = {d["name"]: d["have"] for d in edited["custom"]["documents"]}
    assert docs == {"Aadhaar card": True, "Photo": False}
    assert edited["service_name"] == "Caste cert"
    assert client.patch(f"/cases/{card['id']}/custom/documents/nope", json={"have": True}).status_code == 404


def test_custom_endpoints_refuse_a_listed_service(client):
    cid = client.post("/cases", json={"service_id": "delhi-old-age-pension"}).json()["id"]
    assert client.put(f"/cases/{cid}/custom", json=BODY).status_code == 404


def test_custom_case_uses_its_own_checklist_not_document_upload(client):
    card = _custom(client)
    r = client.post(f"/cases/{card['id']}/documents", json={"doc_type": "aadhaar", "self_declared": True})
    assert r.status_code == 422


def test_custom_case_steps_and_reference_work(client):
    card = _custom(client)
    cid = card["id"]
    for step in (1, 2, 3):
        assert client.post(f"/cases/{cid}/steps", json={"step": step}).status_code == 201
    sub = (date.today() - timedelta(days=30)).isoformat()
    assert client.post(f"/cases/{cid}/steps", json={"step": 4, "submitted_on": sub}).status_code == 201
    r = client.post(f"/cases/{cid}/steps", json={"step": 5, "reference": "DL-2026-00123456"})
    assert r.json()["submission"]["reference_no_masked"] == "XXXX3456"
    ov = client.get(f"/cases/{cid}").json()["overview"]
    assert ov["next_action"] == "follow_up"  # 30 days > the user's 21-day estimate


def test_custom_case_summary_pdf(client):
    from app.pdf import summary

    card = _custom(client, ai_suggested=True, sources=[{"title": "x.gov.in", "url": "https://x.gov.in/a"}])
    state = client.app.state.store.cases[card["id"]]["state"]
    html = summary.build_custom_html(
        state["custom"], "en", custom_readiness(state["custom"]["documents"]), _empty_journey(), None, state
    )
    assert "not checked by Sahaay" in html and "Caste certificate" in html
    r = client.get(f"/cases/{card['id']}/summary.pdf")
    assert r.status_code in (200, 503)  # 503 only when WeasyPrint's system libraries are missing
    if r.status_code == 200:
        assert r.content[:4] == b"%PDF"


def _empty_journey():
    from app.rules.journey import journey

    return journey([])


# ---- date and to-dos on any case


def test_key_date_set_and_clear(client):
    card = _custom(client)
    on = (date.today() + timedelta(days=5)).isoformat()
    r = client.patch(
        f"/cases/{card['id']}",
        json={"key_date": on, "key_date_kind": "appointment", "key_date_label": "SDM office 9876543210"},
    )
    kd = r.json()["key_date"]
    assert kd["on"] == on and kd["kind"] == "appointment" and kd["days_left"] == 5 and kd["soon"]
    assert "9876543210" not in kd["label"]
    assert (
        client.patch(f"/cases/{card['id']}", json={"key_date": on, "key_date_kind": "x"}).status_code == 422
    )
    assert client.patch(f"/cases/{card['id']}", json={"clear_key_date": True}).json()["key_date"] is None


def test_todos_add_tick_delete_on_a_listed_service(client):
    cid = client.post("/cases", json={"service_id": "delhi-old-age-pension"}).json()["id"]
    r = client.post(f"/cases/{cid}/todos", json={"text": "Get a passport photo"})
    assert r.status_code == 201
    todo = r.json()["todos"][0]
    assert todo["done"] is False and r.json()["todos_done"] == 0
    r = client.patch(f"/cases/{cid}/todos/{todo['id']}", json={"done": True})
    assert r.json()["todos_done"] == 1
    assert client.patch(f"/cases/{cid}/todos/nope", json={"done": True}).status_code == 404
    assert client.delete(f"/cases/{cid}/todos/{todo['id']}").json()["todos"] == []
    assert client.post(f"/cases/{cid}/todos", json={"text": ""}).status_code == 422


# ---- AI suggestion


class FakeSuggest:
    name = "fake"

    def __init__(self, payload):
        self.payload = payload
        self.requests: list[LLMRequest] = []

    def generate(self, req: LLMRequest) -> LLMResponse:
        self.requests.append(req)
        return LLMResponse(self.payload, 5, 5)


def _with_llm(client, provider, hits):
    s = get_settings().model_copy(update={"web_search_enabled": True, "web_search_provider": "tavily"})
    seen: list[str] = []

    def searcher(q, domains):
        seen.append(q)
        return hits

    client.app.state.llm = LLM(provider=provider, settings=s, searcher=searcher)
    return seen


HITS = [
    SearchHit(
        "x", "https://edistrict.delhigovt.nic.in/caste", "Caste certificate needs Aadhaar and address proof."
    ),
    SearchHit("y", "https://someblog.example/caste", "Apply online."),
]


def test_suggest_returns_labelled_editable_checklist(client):
    payload = ServiceSuggestion(
        found=True,
        department="Revenue Department",
        documents=["Aadhaar card", "Address proof", "Approval is guaranteed with this"],
        steps=["Apply on https://evil.example/apply", "Visit the office"],
        timeline_days=14,
        note="Results are about Delhi.",
    ).model_dump_json()
    p = FakeSuggest(payload)
    seen = _with_llm(client, p, HITS)
    r = client.post("/cases/suggest", json={"name": "Caste certificate 9876543210", "lang": "en"})
    assert r.status_code == 200
    out = r.json()
    assert out["found"] and out["label"] == "ai_suggested_not_checked"
    assert out["documents"] == ["Aadhaar card", "Address proof"]  # the promise was dropped
    assert all("http" not in s for s in out["steps"])
    assert out["timeline_days"] == 14
    assert "9876543210" not in seen[0]  # the query is masked before it leaves
    assert "<results>" in p.requests[0].text  # web text goes inside delimiters
    # Government results are preferred; the portal is only ever an exact allowlist host.
    assert [s["title"] for s in out["sources"]] == ["edistrict.delhigovt.nic.in"]
    assert out["sources"][0]["official"] is True
    assert out["portal_url"] == "https://edistrict.delhigovt.nic.in/caste"


def test_suggest_never_offers_an_unlisted_portal(client):
    payload = ServiceSuggestion(found=True, documents=["Photo"], steps=[]).model_dump_json()
    _with_llm(
        client, FakeSuggest(payload), [SearchHit("y", "https://someblog.example/caste", "Apply online.")]
    )
    out = client.post("/cases/suggest", json={"name": "Caste certificate"}).json()
    assert out["portal_url"] is None
    assert out["sources"][0]["kind"] == "other" and out["sources"][0]["official"] is False


def test_suggest_not_found_and_unavailable(client):
    _with_llm(client, FakeSuggest('{"found": false, "documents": [], "steps": []}'), HITS)
    assert client.post("/cases/suggest", json={"name": "Moon visa"}).json() == {"found": False}
    client.app.state.llm = LLM(provider=StubProvider())  # offline: no web search
    assert client.post("/cases/suggest", json={"name": "Caste certificate"}).status_code == 503


def test_suggest_bad_json_is_not_found(client):
    p = FakeSuggest("not json")
    s = get_settings().model_copy(update={"web_search_enabled": True, "web_search_provider": "google"})
    client.app.state.llm = LLM(provider=p, settings=s, retries=0)
    assert client.post("/cases/suggest", json={"name": "Caste certificate"}).json() == {"found": False}
