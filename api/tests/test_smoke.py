import os
import sys

from fastapi.testclient import TestClient

# Pytest (notably newer versions) may not automatically prepend the project root
# to sys.path when importing test modules. Ensure the API app module is importable
# both when running from repo root and when code is copied into a container at /app.
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

try:
    from main import app
except ModuleNotFoundError:
    from api.main import app

def test_health_exists():
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    j = r.json()
    assert "ok" in j and j["ok"] is True
