SERVICE = "delhi-old-age-pension"


def _case(client, service=SERVICE):
    r = client.post("/cases", json={"service_id": service})
    assert r.status_code == 201
    return r.json()["id"]


def _check(client, cid, doc_type):
    checks = client.get(f"/cases/{cid}").json()["readiness"]["checks"]
    return next(c for c in checks if c["doc_type"] == doc_type)


def test_create_case_is_idempotent_per_service(client):
    assert _case(client) == _case(client)
    assert len(client.get("/cases").json()) == 1


def test_unknown_service_404(client):
    assert client.post("/cases", json={"service_id": "nope"}).status_code == 404


def test_scanned_document_masks_and_counts(client):
    cid = _case(client)
    r = client.post(
        f"/cases/{cid}/documents",
        json={
            "doc_type": "bank_passbook",
            "fields": {
                "holder_name": "Asha 9876543210",
                "account_masked": "XXXXXX1234",
                "ifsc": "SBIN0001234",
            },
        },
    )
    assert r.status_code == 201
    assert "9876543210" not in str(r.json()["document"]["fields"])
    assert r.json()["readiness"]["completed"] == 1
    chk = _check(client, cid, "bank_passbook")
    assert chk["status"] == "ok" and chk["evaluated"] == "scanned_and_confirmed"


def test_full_number_in_field_is_masked(client):
    cid = _case(client)
    r = client.post(
        f"/cases/{cid}/documents",
        json={"doc_type": "aadhaar", "fields": {"aadhaar_masked": "2345 6789 0124"}},
    )
    assert r.status_code == 201
    assert "6789" not in str(r.json()["document"]["fields"]) or "0124" in str(r.json()["document"]["fields"])
    assert "2345 6789 0124" not in str(r.json())


def test_self_declared_counts_but_is_labelled(client):
    cid = _case(client)
    assert (
        client.post(
            f"/cases/{cid}/documents", json={"doc_type": "passport_photo", "self_declared": True}
        ).status_code
        == 201
    )
    chk = _check(client, cid, "passport_photo")
    assert chk["status"] == "ok" and chk["evaluated"] == "user_declared"


def test_declared_has_no_fields(client):
    cid = _case(client)
    bad = client.post(
        f"/cases/{cid}/documents",
        json={"doc_type": "aadhaar", "self_declared": True, "fields": {"aadhaar_masked": "x"}},
    )
    assert bad.status_code == 422


def test_validation(client):
    cid = _case(client)
    url = f"/cases/{cid}/documents"
    assert client.post(url, json={"doc_type": "zzz", "self_declared": True}).status_code == 422
    assert (
        client.post(url, json={"doc_type": "marksheet", "self_declared": True}).status_code == 422
    )  # not listed
    assert client.post(url, json={"doc_type": "aadhaar", "fields": {"x": "1"}}).status_code == 422
    assert client.post(url, json={"doc_type": "aadhaar", "fields": {}}).status_code == 422
    assert (
        client.post(
            "/cases/not-a-case/documents", json={"doc_type": "aadhaar", "self_declared": True}
        ).status_code
        == 404
    )


def test_newest_document_replaces_old(client):
    cid = _case(client)
    for _ in range(2):
        client.post(f"/cases/{cid}/documents", json={"doc_type": "aadhaar", "self_declared": True})
    assert len(client.get(f"/cases/{cid}").json()["documents"]) == 1


def test_delete_my_data_removes_cases(client):
    cid = _case(client)
    client.delete("/me/data")
    assert client.get(f"/cases/{cid}").status_code == 404
