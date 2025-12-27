import os
import sys

import pytest
from fastapi.testclient import TestClient

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from api.main import app


def test_forgot_password_is_rate_limited(monkeypatch):
    monkeypatch.setattr("api.routes.auth.rate_limit.incr_and_check", lambda ip, scope: (11, False))

    client = TestClient(app)
    resp = client.post("/users/forgot-password", json={"email": "u@example.com"})
    assert resp.status_code == 429
    assert resp.json()["detail"]


def test_proxy_forgot_password_to_django(monkeypatch):
    monkeypatch.setattr("api.routes.auth.rate_limit.incr_and_check", lambda ip, scope: (1, False))

    seen = {}

    async def fake_request(*, method: str, path: str, json_body, cookies, headers):
        seen["method"] = method
        seen["path"] = path
        seen["json_body"] = json_body
        return 200, {"detail": "ok"}, {}

    monkeypatch.setattr("api.routes._proxy.django_request", fake_request)

    client = TestClient(app)
    resp = client.post("/users/forgot-password", json={"email": "u@example.com"})
    assert resp.status_code == 200
    assert resp.json()["detail"] == "ok"

    assert seen["method"] == "POST"
    assert seen["path"] == "/internal/api/users/forgot-password"
    assert seen["json_body"] == {"email": "u@example.com"}


def test_proxy_reset_password_to_django(monkeypatch):
    seen = {}

    async def fake_request(*, method: str, path: str, json_body, cookies, headers):
        seen["method"] = method
        seen["path"] = path
        seen["json_body"] = json_body
        return 200, {"detail": "ok"}, {}

    monkeypatch.setattr("api.routes._proxy.django_request", fake_request)

    client = TestClient(app)
    resp = client.post("/users/reset-password", json={"token": "t", "password": "NewPass123!"})
    assert resp.status_code == 200
    assert resp.json()["detail"] == "ok"

    assert seen["method"] == "POST"
    assert seen["path"] == "/internal/api/users/reset-password"
    assert seen["json_body"] == {"token": "t", "password": "NewPass123!"}
