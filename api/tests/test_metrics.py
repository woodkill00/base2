import os
import sys

from fastapi.testclient import TestClient

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from api.main import app


def test_metrics_exists_and_has_expected_names():
    client = TestClient(app)
    r = client.get("/metrics")
    assert r.status_code == 200
    body = r.text
    assert "base2_api_requests_total" in body
    assert "base2_api_uptime_seconds" in body
