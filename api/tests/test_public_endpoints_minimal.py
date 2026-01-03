from fastapi.testclient import TestClient

from api.main import app


def client() -> TestClient:
    return TestClient(app)


def test_items_endpoints_return_not_implemented():
    c = client()
    r1 = c.get("/api/items")
    assert r1.status_code == 501

    r2 = c.get("/api/items/123")
    assert r2.status_code == 501

    r3 = c.post("/api/items", json={"name": "x"})
    assert r3.status_code == 501


def test_auth_me_requires_bearer_token():
    c = client()
    r = c.get("/api/auth/me")
    assert r.status_code == 401


def test_auth_refresh_requires_refresh_token():
    c = client()
    r = c.post("/api/auth/refresh", json={})
    assert r.status_code == 401


def test_logout_without_refresh_succeeds():
    c = client()
    r = c.post("/api/auth/logout", json={})
    assert r.status_code == 204


def test_users_me_requires_bearer_token():
    c = client()
    r = c.get("/api/users/me")
    assert r.status_code == 401


def test_users_me_patch_requires_bearer_token():
    c = client()
    r = c.patch("/api/users/me", json={"display_name": "hello"})
    assert r.status_code == 401


def test_tenant_echo_requires_tenant_header():
    c = client()
    # Missing header should be rejected before rate limit evaluation
    r = c.get("/api/tenants/abc/echo")
    assert r.status_code == 400
    assert r.json().get("detail") == "tenant_required"
