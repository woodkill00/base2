
from fastapi.testclient import TestClient


from api.main import app


def test_metrics_exists_and_has_expected_names():
    client = TestClient(app)
    r = client.get("/metrics")
    assert r.status_code == 200
    body = r.text
    assert "base2_api_requests_total" in body
    assert "base2_api_uptime_seconds" in body
