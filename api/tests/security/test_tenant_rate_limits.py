import os
import time
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_per_tenant_rate_limits_are_separate(monkeypatch):
    # Tighten the window for test scope
    monkeypatch.setenv("TENANT_RATE_LIMIT_TENANT_ECHO_WINDOW_MS", "1000")
    monkeypatch.setenv("TENANT_RATE_LIMIT_TENANT_ECHO_MAX_REQUESTS", "2")

    # Tenant alpha: two ok, third 429
    h_alpha = {"X-Tenant-Id": "alpha"}
    r1 = client.get("/tenants/alpha/echo", headers=h_alpha)
    assert r1.status_code == 200
    r2 = client.get("/tenants/alpha/echo", headers=h_alpha)
    assert r2.status_code == 200
    r3 = client.get("/tenants/alpha/echo", headers=h_alpha)
    assert r3.status_code == 429

    # Tenant beta should not be affected by alpha's counts
    h_beta = {"X-Tenant-Id": "beta"}
    b1 = client.get("/tenants/beta/echo", headers=h_beta)
    assert b1.status_code == 200
    b2 = client.get("/tenants/beta/echo", headers=h_beta)
    assert b2.status_code == 200
    b3 = client.get("/tenants/beta/echo", headers=h_beta)
    assert b3.status_code == 429

    # Wait for window to roll over, then alpha should be allowed again
    time.sleep(1.1)
    r4 = client.get("/tenants/alpha/echo", headers=h_alpha)
    assert r4.status_code == 200
