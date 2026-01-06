import os
import uuid

import pytest
from fastapi.testclient import TestClient


from api.main import app
from api.db import db_ping


@pytest.mark.skipif(not os.getenv("JWT_SECRET"), reason="JWT_SECRET not set")
def test_auth_register_login_refresh_me_logout_flow():
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

    # In cookie mode, refresh requires double-submit CSRF when cookie is present
    csrf = client.cookies.get("base2_csrf")
    headers = {"X-CSRF-Token": csrf} if csrf else {}
    refreshed = client.post("/api/auth/refresh", headers=headers)
    assert refreshed.status_code == 200, refreshed.text
    j2 = refreshed.json()
    assert j2.get("email") == email
    assert j2.get("access_token")

    # Logout also enforces CSRF when refresh cookie is present
    out = client.post("/api/auth/logout", headers=headers)
    assert out.status_code == 204
