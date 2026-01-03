from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient


from api.main import app


class _FakePipeline:
    def __init__(self, store: dict):
        self._store = store
        self._ops: list[tuple[str, str, int]] = []

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


def test_auth_login_cookie_mode_sets_http_only_cookie_and_hides_refresh(monkeypatch):
    import api.security.rate_limit as rl
    from api.auth.repo import User
    from api.auth.service import AuthTokens

    fake = _FakeRedis()
    monkeypatch.setattr(rl, "get_client", lambda: fake)

    # Force cookie mode on for this test.
    monkeypatch.setattr("api.routes.auth.settings.AUTH_REFRESH_COOKIE", True)
    monkeypatch.setattr("api.routes.auth.settings.COOKIE_SECURE", False)

    u = User(
        id=uuid4(),
        email="u@example.com",
        password_hash="",
        is_active=True,
        is_email_verified=True,
        display_name="",
        avatar_url="",
        bio="",
    )

    tokens = AuthTokens(
        access_token="access",
        refresh_token="refresh",
        refresh_token_expires_at=datetime.now(timezone.utc) + timedelta(days=30),
    )

    def fake_login_user(*, email: str, password: str, ip: str, user_agent: str, refresh_ttl_days: int, access_ttl_minutes: int):
        return u, tokens

    monkeypatch.setattr("api.auth.service.login_user", fake_login_user)

    client = TestClient(app)
    r = client.post("/api/auth/login", json={"email": "u@example.com", "password": "pw"})
    assert r.status_code == 200, r.text

    # Refresh should be a cookie only.
    assert "set-cookie" in {k.lower() for k in r.headers}
    assert "base2_refresh=" in r.headers.get("set-cookie", "")

    body = r.json()
    assert body.get("access_token") == "access"
    assert "refresh_token" not in body


def test_auth_login_non_cookie_mode_returns_refresh_in_json(monkeypatch):
    import api.security.rate_limit as rl
    from api.auth.repo import User
    from api.auth.service import AuthTokens

    fake = _FakeRedis()
    monkeypatch.setattr(rl, "get_client", lambda: fake)

    # Force cookie mode off for this test.
    monkeypatch.setattr("api.routes.auth.settings.AUTH_REFRESH_COOKIE", False)

    u = User(
        id=uuid4(),
        email="u@example.com",
        password_hash="",
        is_active=True,
        is_email_verified=True,
        display_name="",
        avatar_url="",
        bio="",
    )

    tokens = AuthTokens(
        access_token="access",
        refresh_token="refresh",
        refresh_token_expires_at=datetime.now(timezone.utc) + timedelta(days=30),
    )

    def fake_login_user(*, email: str, password: str, ip: str, user_agent: str, refresh_ttl_days: int, access_ttl_minutes: int):
        return u, tokens

    monkeypatch.setattr("api.auth.service.login_user", fake_login_user)

    client = TestClient(app)
    r = client.post("/api/auth/login", json={"email": "u@example.com", "password": "pw"})
    assert r.status_code == 200, r.text

    body = r.json()
    assert body.get("access_token") == "access"
    assert body.get("refresh_token") == "refresh"
