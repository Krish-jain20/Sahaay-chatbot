import pytest


def test_compare_two_services(client):
    r = client.get("/compare", params={"ids": "delhi-income-certificate,delhi-old-age-pension", "lang": "hn"})
    assert r.status_code == 200
    a, b = r.json()["services"]
    assert (a["id"], b["id"]) == ("delhi-income-certificate", "delhi-old-age-pension")
    assert a["fee_strip"]["official_fee_inr"] == 0 and b["fee_strip"]["official_fee_inr"] is None
    assert b["eligibility"][0] == "Umar 60 saal ya zyada"
    assert all(s["citations"] and s["fee_strip"]["source_n"] for s in (a, b))


def test_compare_three(client):
    ids = "delhi-income-certificate,delhi-merit-scholarship-scstobc,delhi-old-age-pension"
    assert len(client.get("/compare", params={"ids": ids}).json()["services"]) == 3


@pytest.mark.parametrize(
    ("ids", "status"),
    [
        ("delhi-income-certificate", 422),
        ("delhi-income-certificate,delhi-income-certificate", 422),
        ("delhi-income-certificate,nope", 404),
        ("a,b,c,d", 422),
    ],
)
def test_compare_bad_input(client, ids, status):
    assert client.get("/compare", params={"ids": ids}).status_code == status
