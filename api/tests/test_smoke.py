from fastapi.testclient import TestClient
try:
    from api.main import app
except ModuleNotFoundError:
    from main import app

def test_health_exists():
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    j = r.json()
    assert "ok" in j and j["ok"] is True
