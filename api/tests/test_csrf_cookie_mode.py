import os
import sys
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from api.main import app


def test_refresh_cookie_mode_requires_double_submit_csrf(monkeypatch):
    from api.auth.repo import User
    from api.auth.service import AuthTokens

    # Force cookie mode on for this test.
    monkeypatch.setattr("api.routes.auth.settings.AUTH_REFRESH_COOKIE", True)
    monkeypatch.setattr("api.routes.auth.settings.COOKIE_SECURE", False)

    called = {"refresh": False}

    u = User(
        id=uuid4(),
        email="u@example.com",
        password_hash="",
        is_active=True,
        is_email_verified=True,
        display_name="",
        avatar_url="",
        bio="",
    )

    tokens = AuthTokens(
        access_token="access",
        refresh_token="refresh",
        refresh_token_expires_at=datetime.now(timezone.utc) + timedelta(days=30),
    )

    def fake_refresh_tokens(*, refresh_token: str, ip: str, user_agent: str, refresh_ttl_days: int, access_ttl_minutes: int):
        called["refresh"] = True
        return u, tokens

    monkeypatch.setattr("api.auth.service.refresh_tokens", fake_refresh_tokens)

    client = TestClient(app)
    client.cookies.set("base2_refresh", "refresh")

    r = client.post("/auth/refresh", json={})
    assert r.status_code == 403, r.text
    assert called["refresh"] is False


def test_refresh_cookie_mode_accepts_double_submit_csrf(monkeypatch):
    from api.auth.repo import User
    from api.auth.service import AuthTokens

    # Force cookie mode on for this test.
    monkeypatch.setattr("api.routes.auth.settings.AUTH_REFRESH_COOKIE", True)
    monkeypatch.setattr("api.routes.auth.settings.COOKIE_SECURE", False)

    u = User(
        id=uuid4(),
        email="u@example.com",
        password_hash="",
        is_active=True,
        is_email_verified=True,
        display_name="",
        avatar_url="",
        bio="",
    )

    tokens = AuthTokens(
        access_token="access",
        refresh_token="refresh2",
        refresh_token_expires_at=datetime.now(timezone.utc) + timedelta(days=30),
    )

    def fake_refresh_tokens(*, refresh_token: str, ip: str, user_agent: str, refresh_ttl_days: int, access_ttl_minutes: int):
        assert refresh_token == "refresh"
        return u, tokens

    monkeypatch.setattr("api.auth.service.refresh_tokens", fake_refresh_tokens)

    client = TestClient(app)
    client.cookies.set("base2_refresh", "refresh")
    client.cookies.set("base2_csrf", "csrf123")

    r = client.post("/auth/refresh", json={}, headers={"X-CSRF-Token": "csrf123"})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("access_token") == "access"
    assert "refresh_token" not in data
