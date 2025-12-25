import os
import sys

import pytest
from fastapi.testclient import TestClient

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

try:
    from main import app
except ModuleNotFoundError:
    from api.main import app


def test_profile_update_filters_payload_and_forwards_csrf(monkeypatch):
    seen = {}

    async def fake_request(*, method: str, path: str, json_body, cookies, headers):
        seen["method"] = method
        seen["path"] = path
        seen["json_body"] = json_body
        seen["headers"] = dict(headers or {})
        return 200, {"email": "u@example.com", "display_name": "New"}, {}

    monkeypatch.setattr("api.routes._proxy.django_request", fake_request)

    client = TestClient(app)
    resp = client.patch(
        "/users/me",
        cookies={"base2_session": "abc"},
        headers={"X-CSRF-Token": "csrf123"},
        json={"display_name": "New", "email": "evil@example.com", "is_staff": True},
    )

    assert resp.status_code == 200
    assert resp.json()["email"] == "u@example.com"

    assert seen["method"] == "PATCH"
    assert seen["path"] == "/internal/api/users/me"
    assert seen["headers"].get("X-CSRF-Token") == "csrf123"
    assert seen["json_body"] == {"display_name": "New"}


@pytest.mark.parametrize("payload", [None, {}])
def test_profile_update_requires_session_cookie(payload):
    client = TestClient(app)
    resp = client.patch("/users/me", json=payload)
    assert resp.status_code == 401
    assert resp.json()["detail"]
