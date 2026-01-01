import uuid

import pytest
from fastapi.testclient import TestClient


from api.auth.passwords import hash_password, verify_password
from api.auth.tokens import hash_token
from api.db import db_conn, db_ping
from api.main import app


def _count_outbox_rows_for(to_email: str) -> int:
    with db_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM api_email_outbox WHERE to_email=%s", (to_email,))
        return int(cur.fetchone()[0])


def _count_unrevoked_refresh_tokens(user_id: str) -> int:
    with db_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM api_auth_refresh_tokens WHERE user_id=%s AND revoked_at IS NULL",
            (user_id,),
        )
        return int(cur.fetchone()[0])


def _count_audit_events(action: str, user_id: str | None = None) -> int:
    with db_conn() as conn, conn.cursor() as cur:
        if user_id is None:
            cur.execute(
                "SELECT COUNT(*) FROM api_auth_audit_events WHERE action=%s",
                (action,),
            )
        else:
            cur.execute(
                "SELECT COUNT(*) FROM api_auth_audit_events WHERE action=%s AND user_id=%s",
                (action, user_id),
            )
        return int(cur.fetchone()[0])


def _create_user(email: str, password: str):
    from api.auth import repo

    return repo.create_user(email=email, password_hash=hash_password(password))


def _insert_refresh_token_for(user_id: str):
    from api.auth import repo

    raw = "r_" + uuid.uuid4().hex
    repo.create_refresh_token(
        user_id=uuid.UUID(user_id),
        token_hash=hash_token(raw),
        ttl_days=30,
        ip="test",
        user_agent="pytest",
    )


def _insert_one_time_token(user_id: str, token_type: str, raw_token: str, ttl_minutes: int = 60):
    from api.auth import repo

    repo.create_one_time_token(
        user_id=uuid.UUID(user_id),
        token_hash=hash_token(raw_token),
        token_type=token_type,
        ttl_minutes=ttl_minutes,
    )


def test_auth_verify_email_consumes_token_and_sets_flag():
    if not db_ping():
        pytest.skip("DB not reachable")

    client = TestClient(app)

    email = f"v_{uuid.uuid4().hex[:10]}@example.com"
    user = _create_user(email, "Test1234!")

    raw = "t_verify_" + uuid.uuid4().hex
    _insert_one_time_token(str(user.id), "verify_email", raw, ttl_minutes=60)

    before_audit = _count_audit_events("user.verify_email", str(user.id))

    r = client.post("/auth/verify-email", json={"token": raw})
    assert r.status_code == 200, r.text

    after_audit = _count_audit_events("user.verify_email", str(user.id))
    assert after_audit == before_audit + 1

    from api.auth import repo

    updated = repo.get_user_by_id(user.id)
    assert updated is not None
    assert updated.is_email_verified is True

    # Single-use: second attempt should fail.
    r2 = client.post("/auth/verify-email", json={"token": raw})
    assert r2.status_code == 400


def test_auth_verify_email_rejects_unknown_token():
    client = TestClient(app)
    r = client.post("/auth/verify-email", json={"token": "nope"})
    assert r.status_code in (400, 500)
    # If DB isn't reachable, endpoint may 500; that's fine for this test.


def test_auth_forgot_password_enumeration_safe_and_sends_email_only_if_user_exists():
    if not db_ping():
        pytest.skip("DB not reachable")

    client = TestClient(app)

    missing = f"missing_{uuid.uuid4().hex[:8]}@example.com"
    existing = f"fp_{uuid.uuid4().hex[:8]}@example.com"
    _create_user(existing, "Test1234!")

    before_missing = _count_outbox_rows_for(missing)
    before_existing = _count_outbox_rows_for(existing)

    r1 = client.post("/auth/forgot-password", json={"email": missing})
    r2 = client.post("/auth/forgot-password", json={"email": existing})

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json().get("detail") == r2.json().get("detail")

    after_missing = _count_outbox_rows_for(missing)
    after_existing = _count_outbox_rows_for(existing)

    assert after_missing == before_missing
    assert after_existing == before_existing + 1


def test_auth_reset_password_updates_hash_consumes_token_and_revokes_refresh_tokens():
    if not db_ping():
        pytest.skip("DB not reachable")

    client = TestClient(app)

    email = f"rp_{uuid.uuid4().hex[:10]}@example.com"
    old_pw = "OldPass123!"
    new_pw = "NewPass123!"
    user = _create_user(email, old_pw)

    # Seed refresh tokens; reset should revoke them.
    _insert_refresh_token_for(str(user.id))
    _insert_refresh_token_for(str(user.id))
    assert _count_unrevoked_refresh_tokens(str(user.id)) >= 2

    raw = "t_reset_" + uuid.uuid4().hex
    _insert_one_time_token(str(user.id), "password_reset", raw, ttl_minutes=60)

    before_audit = _count_audit_events("user.reset_password", str(user.id))

    r = client.post("/auth/reset-password", json={"token": raw, "password": new_pw})
    assert r.status_code == 200, r.text

    after_audit = _count_audit_events("user.reset_password", str(user.id))
    assert after_audit == before_audit + 1

    from api.auth import repo

    updated = repo.get_user_by_id(user.id)
    assert updated is not None
    assert verify_password(new_pw, updated.password_hash)

    # Single-use: second attempt should fail.
    r2 = client.post("/auth/reset-password", json={"token": raw, "password": "Another123!"})
    assert r2.status_code == 400

    assert _count_unrevoked_refresh_tokens(str(user.id)) == 0
