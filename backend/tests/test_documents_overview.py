"""Documents page backend: one list across cases, add once and it counts everywhere, remove."""


def _case(client, service):
    return client.post("/cases", json={"service_id": service}).json()["id"]


def _declare(client, cid, doc_type):
    r = client.post(f"/cases/{cid}/documents", json={"doc_type": doc_type, "self_declared": True})
    assert r.status_code == 201, r.text


def _row(overview, doc_type):
    return next(r for r in overview["documents"] if r["doc_type"] == doc_type)


def test_overview_empty_without_cases(client):
    out = client.get("/documents/overview").json()
    assert out == {"documents": [], "missing_count": 0, "custom": []}


def test_one_document_is_shared_by_every_case_that_needs_it(client):
    pension = _case(client, "delhi-old-age-pension")
    income = _case(client, "delhi-income-certificate")
    out = client.get("/documents/overview").json()
    row = _row(out, "aadhaar")
    assert {n["case_id"] for n in row["needed_by"]} == {pension, income}  # needed by both
    assert row["held"] is None and row["needs_attention"] and out["missing_count"] >= 1
    _declare(client, pension, "aadhaar")
    row = _row(client.get("/documents/overview").json(), "aadhaar")
    assert row["held"]["evaluated"] == "user_declared"
    assert all(n["status"] == "ok" for n in row["needed_by"])  # added once, ready in both
    ready = {c["id"]: c["overview"]["docs_ready"] for c in client.get("/cases/overview").json()}
    assert ready[pension] >= 1 and ready[income] >= 1


def test_most_needed_missing_documents_come_first(client):
    _case(client, "delhi-old-age-pension")
    _case(client, "delhi-income-certificate")
    docs = client.get("/documents/overview").json()["documents"]
    assert docs[0]["needs_attention"] and len(docs[0]["needed_by"]) >= len(docs[-1]["needed_by"])


def test_remove_a_document_everywhere(client):
    pension = _case(client, "delhi-old-age-pension")
    income = _case(client, "delhi-income-certificate")
    _declare(client, pension, "aadhaar")
    assert client.delete("/documents/aadhaar").json() == {"removed": 1}
    row = _row(client.get("/documents/overview").json(), "aadhaar")
    assert row["held"] is None and row["needs_attention"]
    assert client.get(f"/cases/{income}").json()["overview"]["docs_ready"] == 0
    assert client.delete("/documents/aadhaar").status_code == 404


def test_custom_cases_are_listed_separately(client):
    _case(client, "delhi-old-age-pension")
    c = client.post(
        "/cases/custom", json={"name": "Ration card", "documents": ["Photo", "Address proof"]}
    ).json()
    out = client.get("/documents/overview").json()
    assert [x["case_id"] for x in out["custom"]] == [c["id"]]
    assert [d["name"] for d in out["custom"][0]["documents"]] == ["Photo", "Address proof"]
    assert all(r["doc_type"] != c["custom"]["documents"][0]["id"] for r in out["documents"])


def test_service_readiness_preview_creates_no_case_and_uses_existing_documents(client):
    pension = _case(client, "delhi-old-age-pension")
    _declare(client, pension, "aadhaar")
    r = client.get("/services/delhi-income-certificate/readiness").json()
    assert r["completed"] >= 1 and r["total"] >= r["completed"]
    assert len(client.get("/cases").json()) == 1  # still only the pension case
    assert client.get("/services/nope/readiness").status_code == 404
