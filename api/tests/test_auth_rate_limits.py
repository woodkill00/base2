import os
import sys

import pytest
from fastapi.testclient import TestClient

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from api.main import app


class _FakePipeline:
    def __init__(self, store: dict):
        self._store = store
        self._ops = []

    def incr(self, k: str, n: int):
        self._ops.append(("incr", k, n))
        return self

    def pexpire(self, k: str, ms: int):
        self._ops.append(("pexpire", k, ms))
        return self

    def execute(self):
        val = None
        for op, k, arg in self._ops:
            if op == "incr":
                self._store[k] = int(self._store.get(k, 0)) + int(arg)
                val = self._store[k]
        return val, True


class _FakeRedis:
    def __init__(self):
        self.store = {}

    def pipeline(self):
        return _FakePipeline(self.store)


def test_auth_login_rate_limited_includes_retry_after(monkeypatch):
    import api.security.rate_limit as rl

    fake = _FakeRedis()
    monkeypatch.setattr(rl, "get_client", lambda: fake)

    # Avoid hitting the DB; simulate invalid credentials for first N attempts.
    def fake_login_user(*, email: str, password: str, ip: str, user_agent: str, refresh_ttl_days: int, access_ttl_minutes: int):
        raise ValueError("invalid_credentials")

    monkeypatch.setattr("api.auth.service.login_user", fake_login_user)

    client = TestClient(app)

    for _ in range(5):
        r = client.post("/auth/login", json={"email": "u@example.com", "password": "pw"})
        assert r.status_code == 401

    r6 = client.post("/auth/login", json={"email": "u@example.com", "password": "pw"})
    assert r6.status_code == 429
    assert r6.headers.get("Retry-After")
    assert int(r6.headers["Retry-After"]) >= 1
