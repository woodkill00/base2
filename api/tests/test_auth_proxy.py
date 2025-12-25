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


@pytest.mark.parametrize(
    "method,path,expected_cookie",
    [
        ("GET", "/users/me", "base2_session"),
        ("POST", "/users/logout", "base2_session"),
    ],
)
def test_proxy_forwards_session_cookie(monkeypatch, method, path, expected_cookie):
    seen = {}

    async def fake_request(*, method: str, path: str, json_body, cookies, headers):
        seen["method"] = method
        seen["path"] = path
        seen["cookies"] = dict(cookies or {})
        seen["headers"] = dict(headers or {})
        return 200, {"email": "u@example.com"}, {}

    monkeypatch.setattr("api.clients.django_client.django_request", fake_request)

    client = TestClient(app)
    resp = client.request(method, path, cookies={expected_cookie: "abc"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "u@example.com"

    assert expected_cookie in seen["cookies"]


def test_proxy_forwards_csrf_header(monkeypatch):
    seen = {}

    async def fake_request(*, method: str, path: str, json_body, cookies, headers):
        seen["headers"] = dict(headers or {})
        return 204, None, {}

    monkeypatch.setattr("api.clients.django_client.django_request", fake_request)

    client = TestClient(app)
    resp = client.post(
        "/users/logout",
        cookies={"base2_session": "abc"},
        headers={"X-CSRF-Token": "token123"},
    )
    assert resp.status_code == 204

    assert seen["headers"].get("X-CSRF-Token") == "token123"


def test_proxy_passthrough_429(monkeypatch):
    monkeypatch.setattr("api.routes.auth.rate_limit.incr_and_check", lambda ip, scope: (1, False))

    async def fake_request(*, method: str, path: str, json_body, cookies, headers):
        return 429, {"detail": "Rate limited"}, {}

    monkeypatch.setattr("api.clients.django_client.django_request", fake_request)

    client = TestClient(app)
    resp = client.post("/users/login", json={"email": "u@example.com", "password": "pw"})
    assert resp.status_code == 429
    assert resp.json()["detail"]
