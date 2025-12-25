import json
from urllib.parse import parse_qs, urlparse

import pytest
from django.contrib.auth import get_user_model
from django.test import Client


@pytest.fixture()
def client() -> Client:
    # OAuth start/callback should not require CSRF
    return Client(enforce_csrf_checks=False)


def _set_oauth_env(monkeypatch):
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv("GOOGLE_OAUTH_REDIRECT_URI", "https://example.com/oauth/google/callback")
    monkeypatch.setenv("OAUTH_STATE_SECRET", "test-state-secret")


def _extract_state(authorization_url: str) -> str:
    parsed = urlparse(authorization_url)
    qs = parse_qs(parsed.query)
    assert "state" in qs
    return qs["state"][0]


@pytest.mark.django_db
def test_oauth_start_returns_authorization_url_and_state(client: Client, monkeypatch):
    _set_oauth_env(monkeypatch)

    r = client.post(
        "/internal/api/oauth/google/start",
        data=json.dumps({"next": "/dashboard"}),
        content_type="application/json",
    )
    assert r.status_code == 200
    j = r.json()
    assert "authorization_url" in j
    assert isinstance(j["authorization_url"], str)
    state = _extract_state(j["authorization_url"])
    assert state


@pytest.mark.django_db
def test_oauth_start_rejects_unallowlisted_next(client: Client, monkeypatch):
    _set_oauth_env(monkeypatch)

    r = client.post(
        "/internal/api/oauth/google/start",
        data=json.dumps({"next": "https://evil.example.com"}),
        content_type="application/json",
    )
    assert r.status_code == 400
    assert "detail" in r.json()


@pytest.mark.django_db
def test_oauth_callback_rejects_missing_code(client: Client, monkeypatch):
    _set_oauth_env(monkeypatch)

    r = client.post(
        "/internal/api/oauth/google/callback",
        data=json.dumps({"state": "anything"}),
        content_type="application/json",
    )
    assert r.status_code == 400
    assert "detail" in r.json()


@pytest.mark.django_db
def test_oauth_callback_rejects_invalid_state(client: Client, monkeypatch):
    _set_oauth_env(monkeypatch)

    r = client.post(
        "/internal/api/oauth/google/callback",
        data=json.dumps({"code": "test-code", "state": "bad-state"}),
        content_type="application/json",
    )
    assert r.status_code == 400
    assert "detail" in r.json()


@pytest.mark.django_db
def test_oauth_callback_links_account_and_logs_in(client: Client, monkeypatch):
    _set_oauth_env(monkeypatch)

    # Start: get a valid state minted by server
    r_start = client.post(
        "/internal/api/oauth/google/start",
        data=json.dumps({"next": "/dashboard"}),
        content_type="application/json",
    )
    assert r_start.status_code == 200
    state = _extract_state(r_start.json()["authorization_url"])

    # Patch Google HTTP helpers (implementation will call these via users.api_views)
    import users.api_views as api_views

    def fake_exchange_code_for_tokens(*_args, **_kwargs):
        return {
            "access_token": "access-token",
            "refresh_token": "refresh-token",
            "expires_in": 3600,
            "token_type": "Bearer",
        }

    def fake_fetch_userinfo(*_args, **_kwargs):
        return {
            "sub": "google-sub-123",
            "email": "oauthuser@example.com",
            "email_verified": True,
            "name": "OAuth User",
            "picture": "https://example.com/avatar.png",
        }

    monkeypatch.setattr(api_views, "_google_exchange_code_for_tokens", fake_exchange_code_for_tokens, raising=False)
    monkeypatch.setattr(api_views, "_google_fetch_userinfo", fake_fetch_userinfo, raising=False)

    r_cb = client.post(
        "/internal/api/oauth/google/callback",
        data=json.dumps({"code": "test-code", "state": state}),
        content_type="application/json",
    )
    assert r_cb.status_code == 200
    j = r_cb.json()
    assert j.get("email") == "oauthuser@example.com"

    # should now be authenticated
    r_me = client.get("/internal/api/users/me")
    assert r_me.status_code == 200
    assert r_me.json()["email"] == "oauthuser@example.com"

    # account linking should be stable (second callback logs into same user)
    AuthUser = get_user_model()
    assert AuthUser.objects.filter(email="oauthuser@example.com").count() == 1


@pytest.mark.django_db
def test_oauth_callback_reuses_existing_user_by_email(client: Client, monkeypatch):
    _set_oauth_env(monkeypatch)

    AuthUser = get_user_model()
    existing = AuthUser.objects.create_user(username="u1", email="existing@example.com", password="Test1234!")

    r_start = client.post(
        "/internal/api/oauth/google/start",
        data=json.dumps({"next": "/dashboard"}),
        content_type="application/json",
    )
    state = _extract_state(r_start.json()["authorization_url"])

    import users.api_views as api_views

    def fake_exchange_code_for_tokens(*_args, **_kwargs):
        return {"access_token": "access-token"}

    def fake_fetch_userinfo(*_args, **_kwargs):
        return {
            "sub": "google-sub-999",
            "email": "existing@example.com",
            "email_verified": True,
        }

    monkeypatch.setattr(api_views, "_google_exchange_code_for_tokens", fake_exchange_code_for_tokens, raising=False)
    monkeypatch.setattr(api_views, "_google_fetch_userinfo", fake_fetch_userinfo, raising=False)

    r_cb = client.post(
        "/internal/api/oauth/google/callback",
        data=json.dumps({"code": "test-code", "state": state}),
        content_type="application/json",
    )
    assert r_cb.status_code == 200
    assert r_cb.json()["email"] == "existing@example.com"

    assert AuthUser.objects.filter(email="existing@example.com").count() == 1
    assert AuthUser.objects.get(email="existing@example.com").id == existing.id
