import pytest
from fastapi.testclient import TestClient

from api.main import app

# Uses the tenant echo route which performs Redis-backed rate limiting.
# Mark as integration to require Redis service (CI integration job).
pytestmark = pytest.mark.integration

client = TestClient(app)


def test_tenant_header_required():
    r = client.get("/tenants/alpha/echo")
    assert r.status_code == 400
    assert r.json().get("detail") == "tenant_required"


def test_tenant_header_must_match_path():
    r = client.get("/tenants/alpha/echo", headers={"X-Tenant-Id": "beta"})
    assert r.status_code == 403
    assert r.json().get("detail") == "cross_tenant_forbidden"


def test_tenant_header_ok_when_matching():
    r = client.get("/tenants/alpha/echo", headers={"X-Tenant-Id": "alpha"})
    assert r.status_code == 200
    assert r.json()["tenant_id"] == "alpha"
