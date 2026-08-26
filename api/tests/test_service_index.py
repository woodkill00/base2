from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app


def test_api_root_is_a_safe_stable_service_index():
    response = TestClient(app).get("/api")
    assert response.status_code == 200
    assert response.json() == {
        "service": "base2-api",
        "status": "ready",
        "health": "/api/health",
        "site": "/api/site",
        "documentation": "protected",
    }
    lowered = response.text.lower()
    for forbidden in ("password", "secret", "token", "postgres", "redis://", "docker"):
        assert forbidden not in lowered
