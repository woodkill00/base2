import os
import uuid

import pytest
from fastapi.testclient import TestClient


from api.main import app
from api.db import db_ping


@pytest.mark.skipif(not os.getenv("JWT_SECRET"), reason="JWT_SECRET not set")
def test_auth_register_login_refresh_me_logout_flow(monkeypatch):
    # For TestClient over HTTP, avoid Secure cookies blocking storage
    monkeypatch.setattr("api.routes.auth.settings.AUTH_REFRESH_COOKIE", False)
    monkeypatch.setattr("api.routes.auth.settings.COOKIE_SECURE", False)
    # Requires Postgres reachable via env vars.
    if not db_ping():
        pytest.skip("DB not reachable")

    client = TestClient(app)

    email = f"u_{uuid.uuid4().hex[:12]}@example.com"
    password = "Test1234!"

    r = client.post("/api/auth/register", json={"email": email, "password": password})
    assert r.status_code == 201, r.text
    j = r.json()
    assert j.get("email") == email
    assert j.get("access_token")

    access_token = j["access_token"]

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    assert me.status_code == 200
    assert me.json().get("email") == email

    # Non-cookie mode: refresh token is returned in JSON and accepted in body
    refresh_token = j.get("refresh_token")
    refreshed = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert refreshed.status_code == 200, refreshed.text
    j2 = refreshed.json()
    assert j2.get("email") == email
    assert j2.get("access_token")

    # Non-cookie mode: logout accepts refresh token in body
    out = client.post("/api/auth/logout", json={"refresh_token": refresh_token})
    assert out.status_code == 204
