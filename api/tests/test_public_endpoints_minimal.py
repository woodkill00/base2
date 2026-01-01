from fastapi.testclient import TestClient

from api.main import app


def client() -> TestClient:
    return TestClient(app)


def test_items_endpoints_return_not_implemented():
    c = client()
    r1 = c.get("/items")
    assert r1.status_code == 501

    r2 = c.get("/items/123")
    assert r2.status_code == 501

    r3 = c.post("/items", json={"name": "x"})
    assert r3.status_code == 501


def test_auth_me_requires_bearer_token():
    c = client()
    r = c.get("/auth/me")
    assert r.status_code == 401


def test_auth_refresh_requires_refresh_token():
    c = client()
    r = c.post("/auth/refresh", json={})
    assert r.status_code == 401


def test_logout_without_refresh_succeeds():
    c = client()
    r = c.post("/auth/logout", json={})
    assert r.status_code == 204


def test_users_me_requires_bearer_token():
    c = client()
    r = c.get("/users/me")
    assert r.status_code == 401


def test_users_me_patch_requires_bearer_token():
    c = client()
    r = c.patch("/users/me", json={"display_name": "hello"})
    assert r.status_code == 401


def test_tenant_echo_requires_tenant_header():
    c = client()
    # Missing header should be rejected before rate limit evaluation
    r = c.get("/tenants/abc/echo")
    assert r.status_code == 400
    assert r.json().get("detail") == "tenant_required"
