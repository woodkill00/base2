import uuid

import pytest
from fastapi.testclient import TestClient


from api.db import db_ping
from api.main import app


def test_auth_oauth_google_creates_user_and_returns_tokens(monkeypatch):
    if not db_ping():
        pytest.skip("DB not reachable")

    from api.services import oauth_google

    monkeypatch.setattr("api.routes.auth.settings.GOOGLE_OAUTH_CLIENT_ID", "test-client")

    def fake_verify(*, id_token: str, audience: str):
        assert audience == "test-client"
        return oauth_google.GoogleIdentity(
            sub="sub_" + uuid.uuid4().hex,
            email=f"g_{uuid.uuid4().hex[:8]}@example.com",
            email_verified=True,
            name="G User",
            picture="https://example.com/p.png",
        )

    monkeypatch.setattr("api.services.oauth_google.verify_google_id_token", fake_verify)

    client = TestClient(app)
    r = client.post("/api/auth/oauth/google", json={"credential": "dummy"})
    assert r.status_code == 200, r.text
    j = r.json()
    assert j.get("email")
    assert j.get("access_token")


def test_auth_oauth_google_merge_rules_reject_unverified_collision(monkeypatch):
    if not db_ping():
        pytest.skip("DB not reachable")

    from api.auth import repo
    from api.services import oauth_google

    email = f"merge_{uuid.uuid4().hex[:8]}@example.com"
    # Create local user with unverified email.
    repo.create_user(email=email, password_hash="x")

    monkeypatch.setattr("api.routes.auth.settings.GOOGLE_OAUTH_CLIENT_ID", "test-client")

    def fake_verify(*, id_token: str, audience: str):
        return oauth_google.GoogleIdentity(
            sub="sub_" + uuid.uuid4().hex,
            email=email,
            email_verified=False,
            name="G User",
            picture="",
        )

    monkeypatch.setattr("api.services.oauth_google.verify_google_id_token", fake_verify)

    client = TestClient(app)
    r = client.post("/api/auth/oauth/google", json={"credential": "dummy"})
    assert r.status_code == 401


def test_auth_oauth_google_merge_rules_allow_when_google_verified(monkeypatch):
    if not db_ping():
        pytest.skip("DB not reachable")

    from api.auth import repo
    from api.services import oauth_google

    email = f"mergeok_{uuid.uuid4().hex[:8]}@example.com"
    repo.create_user(email=email, password_hash="x")

    monkeypatch.setattr("api.routes.auth.settings.GOOGLE_OAUTH_CLIENT_ID", "test-client")

    def fake_verify(*, id_token: str, audience: str):
        return oauth_google.GoogleIdentity(
            sub="sub_" + uuid.uuid4().hex,
            email=email,
            email_verified=True,
            name="G User",
            picture="",
        )

    monkeypatch.setattr("api.services.oauth_google.verify_google_id_token", fake_verify)

    client = TestClient(app)
    r = client.post("/api/auth/oauth/google", json={"credential": "dummy"})
    assert r.status_code == 200, r.text
    assert r.json().get("email") == email
