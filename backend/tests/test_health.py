def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_services_list_has_sources(client):
    r = client.get("/services")
    assert r.status_code == 200
    services = r.json()
    assert services, "at least one served record"
    for s in services:
        assert s["sources"], f"{s['id']} has no sources"


def test_unknown_service_404(client):
    assert client.get("/services/nope").status_code == 404
