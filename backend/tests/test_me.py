import pytest


def test_facts_need_consent(client):
    r = client.put("/me/facts", json={"key": "age", "value": 65})
    assert r.status_code == 400
    assert client.get("/me/facts").json() == []


def test_save_and_list_fact_with_consent(client):
    r = client.put("/me/facts", json={"key": "age", "value": 65, "consent": True})
    assert r.status_code == 200
    assert [(f["key"], f["value"], f["confirmed"]) for f in client.get("/me/facts").json()] == [
        ("age", 65, True)
    ]


@pytest.mark.parametrize(
    ("body", "status"),
    [
        ({"key": "favourite_colour", "value": "red", "consent": True}, 422),
        ({"key": "full_name", "value": "my aadhaar 2345 6789 0124", "consent": True}, 422),
    ],
)
def test_bad_facts_rejected(client, body, status):
    assert client.put("/me/facts", json=body).status_code == status


def test_report_incorrect_masks_and_stores(client):
    r = client.post(
        "/reports/incorrect",
        json={"service_id": "delhi-income-certificate", "note": "Fee is wrong. Call me 9876543210"},
    )
    assert r.status_code == 201
    from app.main import app

    saved = app.state.store.corrections[-1]
    assert saved["service_id"] == "delhi-income-certificate" and "9876543210" not in saved["note"]
    assert client.post("/reports/incorrect", json={"service_id": "nope", "note": "abc"}).status_code == 404


def test_delete_my_data_removes_everything(client):
    client.put("/me/facts", json={"key": "age", "value": 65, "consent": True})
    client.post("/reports/incorrect", json={"service_id": "delhi-income-certificate", "note": "wrong fee"})
    assert client.delete("/me/data").json() == {"ok": True}
    from app.main import app

    assert client.get("/me/facts").json() == []
    assert app.state.store.corrections == []


def test_export_and_delete_cover_every_kind_of_data(client):
    client.put("/me/facts", json={"key": "age", "value": 65, "consent": True})
    cid = client.post("/cases", json={"service_id": "delhi-old-age-pension"}).json()["id"]
    client.post(
        f"/cases/{cid}/documents",
        json={"doc_type": "aadhaar", "fields": {"aadhaar_masked": "2345 6789 0124"}},
    )
    client.post(f"/cases/{cid}/steps", json={"step": 4, "submitted_on": "2026-11-20"})
    client.post(f"/cases/{cid}/steps", json={"step": 5, "reference": "DL/998877"})

    data = client.get("/me/data").json()
    assert [f["key"] for f in data["facts"]] == ["age"]
    (case,) = data["cases"]
    assert [d["doc_type"] for d in case["documents"]] == ["aadhaar"]
    assert sorted(s["step"] for s in case["steps"]) == [4, 5]
    assert case["submission"]["reference_no_masked"] == "XXXX8877"
    text = str(data)
    assert "2345 6789 0124" not in text and "998877" not in text

    assert client.delete("/me/data").status_code == 200
    assert client.get("/me/data").json() == {"facts": [], "cases": []}
