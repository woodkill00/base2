import os
import sys

from fastapi.testclient import TestClient

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

try:
    from main import app
except ModuleNotFoundError:
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


def test_incr_and_check_over_limit(monkeypatch):
    import api.security.rate_limit as rl

    fake = _FakeRedis()

    monkeypatch.setattr(rl, "get_client", lambda: fake)
    monkeypatch.setattr(rl, "MAX_REQUESTS", 2)
    monkeypatch.setattr(rl, "WINDOW_MS", 60000)

    c1, over1 = rl.incr_and_check("1.2.3.4", "login")
    assert c1 == 1 and over1 is False

    c2, over2 = rl.incr_and_check("1.2.3.4", "login")
    assert c2 == 2 and over2 is False

    c3, over3 = rl.incr_and_check("1.2.3.4", "login")
    assert c3 == 3 and over3 is True


def test_login_rate_limited_returns_detail(monkeypatch):
    import api.security.rate_limit as rl

    async def fake_request(*, method: str, path: str, json_body, cookies, headers):
        return 401, {"detail": "Invalid credentials"}, {}

    fake = _FakeRedis()

    monkeypatch.setattr(rl, "get_client", lambda: fake)
    monkeypatch.setattr(rl, "MAX_REQUESTS", 1)
    monkeypatch.setattr(rl, "WINDOW_MS", 60000)
    monkeypatch.setattr("api.routes._proxy.django_request", fake_request)

    client = TestClient(app)

    r1 = client.post("/users/login", json={"email": "u@example.com", "password": "pw"})
    assert r1.status_code in (200, 401, 422)

    r2 = client.post("/users/login", json={"email": "u@example.com", "password": "pw"})
    assert r2.status_code == 429
    assert "detail" in r2.json()
