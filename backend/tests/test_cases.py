import pytest

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


def _steps(client, cid):
    return client.get(f"/cases/{cid}").json()["journey"]


def test_journey_starts_empty_and_is_labelled_as_own_progress(client):
    cid = _case(client)
    j = _steps(client, cid)
    assert j["label"] == "your_own_progress" and j["current"] == 1 and j["completed"] == 0


def test_record_and_undo_steps(client):
    cid = _case(client)
    assert client.post(f"/cases/{cid}/steps", json={"step": 1}).status_code == 201
    client.post(f"/cases/{cid}/steps", json={"step": 1})  # twice keeps one
    j = _steps(client, cid)
    assert j["completed"] == 1 and j["current"] == 2 and j["steps"][0]["done_at"]
    assert client.delete(f"/cases/{cid}/steps/1").json()["journey"]["completed"] == 0
    assert client.delete(f"/cases/{cid}/steps/9").status_code == 404


def test_reference_is_masked_and_submission_date_saved(client):
    cid = _case(client)
    assert (
        client.post(f"/cases/{cid}/steps", json={"step": 4, "submitted_on": "2026-11-20"}).status_code == 201
    )
    r = client.post(f"/cases/{cid}/steps", json={"step": 5, "reference": "DL/IC/2026/998877"})
    assert r.status_code == 201
    sub = client.get(f"/cases/{cid}").json()["submission"]
    assert sub == {"reference_no_masked": "XXXX8877", "submitted_on": "2026-11-20"}
    assert "998877" not in str(client.get(f"/cases/{cid}").json())


@pytest.mark.parametrize(
    "body",
    [
        {"step": 5},
        {"step": 5, "reference": "12"},
        {"step": 4, "submitted_on": "2999-01-01"},
        {"step": 6},
        {"step": 0},
    ],
)
def test_bad_steps_rejected(client, body):
    cid = _case(client)
    assert client.post(f"/cases/{cid}/steps", json=body).status_code == 422


def test_steps_of_another_case_404(client):
    assert client.post("/cases/nope/steps", json={"step": 1}).status_code == 404


def _summary_text(client, cid, lang="en"):
    import pymupdf

    r = client.get(f"/cases/{cid}/summary.pdf", params={"lang": lang})
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    return "".join(p.get_text() for p in pymupdf.open(stream=r.content, filetype="pdf"))


def test_summary_pdf_has_progress_checklist_and_sources(client):
    from tests.test_drafts import PDF_OK

    if not PDF_OK:
        pytest.skip("WeasyPrint system libraries not available")
    cid = _case(client)
    client.post(f"/cases/{cid}/steps", json={"step": 1})
    client.post(f"/cases/{cid}/documents", json={"doc_type": "aadhaar", "self_declared": True})
    client.post(f"/cases/{cid}/steps", json={"step": 5, "reference": "DL/998877"})
    text = _summary_text(client, cid)
    assert "Not government status" in text and "Eligibility checked" in text
    assert "XXXX8877" in text and "998877" not in text.replace("XXXX8877", "")
    assert "you said you have it, not checked" in text
    assert "Sources" in text and "socialwelfare.delhi.gov.in" in text
    assert "₹[" not in text
    assert "Verify locally" in text  # fees are unknown in the record: never invented
    assert "केस सारांश" in _summary_text(
        client, cid, "hi"
    )  # extraction reorders some matras, so check a plain heading


def test_summary_of_other_case_404(client):
    assert client.get("/cases/nope/summary.pdf").status_code == 404
