import os
import sys

import pytest
from fastapi.testclient import TestClient

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from api.main import app


def test_oauth_start_proxies_to_django(monkeypatch):
    seen = {}

    async def fake_request(*, method: str, path: str, json_body, cookies, headers):
        seen["method"] = method
        seen["path"] = path
        seen["json"] = json_body
        return 200, {"authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?state=abc"}, {}

    monkeypatch.setattr("api.routes._proxy.django_request", fake_request)

    client = TestClient(app)
    resp = client.post("/oauth/google/start", json={"next": "/dashboard"})
    assert resp.status_code == 200
    assert "authorization_url" in resp.json()

    assert seen["method"] == "POST"
    assert seen["path"] == "/internal/api/oauth/google/start"
    assert seen["json"] == {"next": "/dashboard"}


def test_oauth_callback_proxies_to_django(monkeypatch):
    seen = {}

    async def fake_request(*, method: str, path: str, json_body, cookies, headers):
        seen["method"] = method
        seen["path"] = path
        seen["json"] = json_body
        return 200, {"email": "oauthuser@example.com"}, {}

    monkeypatch.setattr("api.routes._proxy.django_request", fake_request)

    client = TestClient(app)
    resp = client.post("/oauth/google/callback", json={"code": "test-code", "state": "test-state"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "oauthuser@example.com"

    assert seen["method"] == "POST"
    assert seen["path"] == "/internal/api/oauth/google/callback"
    assert seen["json"] == {"code": "test-code", "state": "test-state"}
