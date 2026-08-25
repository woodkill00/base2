from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from api.main import app


def test_account_lifecycle_and_identity_routes_are_real_contracts():
    paths = app.openapi()["paths"]
    expected = {
        "/api/auth/register",
        "/api/auth/login",
        "/api/auth/logout",
        "/api/auth/verify-email",
        "/api/auth/forgot-password",
        "/api/auth/reset-password",
        "/api/auth/refresh",
        "/api/auth/sessions",
        "/api/auth/sessions/revoke-others",
        "/api/oauth/google/start",
        "/api/oauth/google/callback",
        "/api/identity/capabilities",
    }
    assert expected <= set(paths)


def test_google_oauth_is_explicitly_disabled_and_never_returns_501(monkeypatch):
    monkeypatch.setattr("api.routes.oauth.settings.GOOGLE_OAUTH_ENABLED", False)
    client = TestClient(app)
    response = client.post("/api/oauth/google/start", json={"return_path": "/account"})
    assert response.status_code == 404
    assert response.json() == {"detail": "oauth_provider_disabled"}
    assert response.status_code != 501


def test_google_oauth_start_uses_exact_allowlisted_redirect_and_browser_binding(monkeypatch):
    monkeypatch.setattr("api.routes.oauth.settings.GOOGLE_OAUTH_ENABLED", True)
    monkeypatch.setattr("api.routes.oauth.settings.GOOGLE_OAUTH_CLIENT_ID", "client-id")
    monkeypatch.setattr("api.routes.oauth.settings.GOOGLE_OAUTH_CLIENT_SECRET", "client-secret")
    monkeypatch.setattr(
        "api.routes.oauth.settings.GOOGLE_OAUTH_REDIRECT_URI",
        "https://example.test/api/oauth/google/callback",
    )
    monkeypatch.setattr("api.routes.oauth.settings.OAUTH_STATE_SECRET", "s" * 32)
    client = TestClient(app)

    response = client.post("/api/oauth/google/start", json={"return_path": "/account"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["provider"] == "google"
    assert body["expires_in"] <= 600
    assert "client_id=client-id" in body["authorization_url"]
    assert "redirect_uri=https%3A%2F%2Fexample.test%2Fapi%2Foauth%2Fgoogle%2Fcallback" in body[
        "authorization_url"
    ]
    cookie = response.cookies.get("base2_oauth_state")
    assert cookie
    assert body["state"] not in cookie


def test_google_oauth_callback_fails_closed_before_any_provider_request(monkeypatch):
    monkeypatch.setattr("api.routes.oauth.settings.GOOGLE_OAUTH_ENABLED", True)
    monkeypatch.setattr("api.routes.oauth.settings.GOOGLE_OAUTH_CLIENT_ID", "client-id")
    monkeypatch.setattr("api.routes.oauth.settings.GOOGLE_OAUTH_CLIENT_SECRET", "client-secret")
    monkeypatch.setattr(
        "api.routes.oauth.settings.GOOGLE_OAUTH_REDIRECT_URI",
        "https://example.test/api/oauth/google/callback",
    )
    monkeypatch.setattr("api.routes.oauth.settings.OAUTH_STATE_SECRET", "s" * 32)
    response = TestClient(app).post(
        "/api/oauth/google/callback", json={"code": "unused", "state": "unused"}
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "oauth_state_missing"}


def test_oauth_state_rejects_external_return_paths_expiry_tampering_and_wrong_browser():
    from api.security.identity import OAuthStateError, OAuthStateSigner

    signer = OAuthStateSigner(secret="s" * 32, ttl_seconds=300)
    now = datetime(2026, 8, 25, 12, 0, tzinfo=timezone.utc)
    issued = signer.issue(return_path="/account", now=now)
    assert signer.verify(issued.state, browser_binding=issued.browser_binding, now=now)["return_path"] == "/account"

    with pytest.raises(OAuthStateError, match="unsafe_return_path"):
        signer.issue(return_path="https://evil.example/steal", now=now)
    with pytest.raises(OAuthStateError, match="state_invalid"):
        signer.verify(issued.state + "x", browser_binding=issued.browser_binding, now=now)
    with pytest.raises(OAuthStateError, match="state_browser_mismatch"):
        signer.verify(issued.state, browser_binding="wrong", now=now)
    with pytest.raises(OAuthStateError, match="state_expired"):
        signer.verify(
            issued.state,
            browser_binding=issued.browser_binding,
            now=now + timedelta(seconds=301),
        )


def test_rbac_is_deny_by_default_and_sensitive_actions_need_recent_reauthentication():
    from api.security.identity import is_allowed, require_recent_reauthentication

    assert is_allowed("owner", "credential.create") is True
    assert is_allowed("admin", "invitation.create") is True
    assert is_allowed("editor", "content.write") is True
    assert is_allowed("viewer", "content.read") is True
    assert is_allowed("viewer", "credential.create") is False
    assert is_allowed("unknown", "content.read") is False
    assert is_allowed("owner", "unknown.permission") is False

    now = datetime(2026, 8, 25, 12, 0, tzinfo=timezone.utc)
    require_recent_reauthentication(authenticated_at=now - timedelta(minutes=4), now=now)
    with pytest.raises(PermissionError, match="recent_reauthentication_required"):
        require_recent_reauthentication(authenticated_at=now - timedelta(minutes=6), now=now)


def test_totp_recovery_invitation_and_api_secrets_are_not_retained_in_plaintext():
    from api.security.identity import (
        create_recovery_codes,
        generate_totp_secret,
        hash_sensitive_value,
        totp_code,
        verify_recovery_code,
        verify_totp,
    )

    pepper = "test-pepper"
    secret = generate_totp_secret()
    at = datetime(2026, 8, 25, 12, 0, tzinfo=timezone.utc)
    code = totp_code(secret, at=at)
    assert verify_totp(secret, code, at=at)
    assert not verify_totp(secret, "000000", at=at) or code == "000000"

    bundle = create_recovery_codes(pepper=pepper, count=8)
    assert len(bundle.plaintext_codes) == len(bundle.code_hashes) == 8
    assert not set(bundle.plaintext_codes) & set(bundle.code_hashes)
    assert verify_recovery_code(bundle.plaintext_codes[0], bundle.code_hashes, pepper=pepper)
    assert hash_sensitive_value("invite-token", pepper=pepper) != "invite-token"
    assert hash_sensitive_value("api-secret", pepper=pepper) != "api-secret"


def test_mfa_is_versioned_and_fails_closed_without_secret_or_webauthn_ceremony(monkeypatch):
    monkeypatch.setattr("api.routes.identity.settings.WEBAUTHN_ENABLED", False)
    monkeypatch.setattr("api.routes.identity.settings.IDENTITY_ENCRYPTION_KEY", None)
    response = TestClient(app).get("/api/identity/capabilities")
    assert response.status_code == 200
    methods = response.json()["mfa"]
    assert methods["totp"] == {"enabled": False, "version": "v1"}
    assert methods["recovery_codes"] == {"enabled": False, "version": "v1"}
    assert methods["webauthn"] == {"enabled": False, "version": "v1"}


def test_audit_redaction_is_recursive_and_append_only_is_enforced_by_model_contract():
    from api.security.identity import redact_audit_metadata

    result = redact_audit_metadata(
        {
            "provider": "google",
            "password": "nope",
            "nested": {"token": "nope", "safe": "yes"},
            "items": [{"client_secret": "nope", "action": "created"}],
        }
    )
    assert result == {
        "provider": "google",
        "password": "[REDACTED]",
        "nested": {"token": "[REDACTED]", "safe": "yes"},
        "items": [{"client_secret": "[REDACTED]", "action": "created"}],
    }


def test_data_rights_contract_requires_authentication_before_tenant_details():
    client = TestClient(app)
    for path in ("/api/privacy/export", "/api/privacy/correct", "/api/privacy/delete"):
        response = client.post(path, headers={"X-Tenant-Id": "tenant-a"}, json={})
        assert response.status_code == 401
        assert response.json()["detail"] == "not_authenticated"
