def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_scan_url_creates_scan_and_report(client):
    payload = {"url": "http://paypal-login-secure-update.xyz/account/verify"}
    r = client.post("/scan/url", json=payload)
    assert r.status_code == 200

    data = r.json()
    assert data["status"] == "completed"
    assert "id" in data
    assert "score" in data
    assert "verdict" in data
    assert "created_at" in data


def test_scan_url_invalid_returns_422(client):
    """Test que URL vacía retorna 422 (Pydantic validation error)"""
    r = client.post("/scan/url", json={"url": ""})
    assert r.status_code == 422
