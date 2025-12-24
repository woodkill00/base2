from fastapi.testclient import TestClient
from api.main import app

def test_health_exists():
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    j = r.json()
    assert "ok" in j and j["ok"] is True
