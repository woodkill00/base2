#!/usr/bin/env python3
"""Fixed synthetic recovery checks, invoked only by disposable Postgres acceptance.

The API, token repository and outbox use real PostgreSQL. Only the external
Celery handoff is intercepted: this is not SMTP delivery or browser evidence.
Never emit response bodies, tokens, passwords or email body contents.
"""

from __future__ import annotations

import os
import re
import secrets
import traceback
from contextlib import closing
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from unittest.mock import patch


class JourneyFailure(RuntimeError):
    """A fixed, non-sensitive assertion code."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise JourneyFailure(code)


def main() -> None:
    require(
        os.getenv("DB_HOST") == "127.0.0.1" and os.getenv("DB_NAME") == "base2",
        "disposable_database_required",
    )
    require(os.getenv("BASE2_DISPOSABLE_JOURNEY") == "1", "disposable_runner_required")
    os.environ["BASE2_EMAIL_ADAPTER"] = "disabled"
    import psycopg2
    from fastapi.testclient import TestClient

    from api.auth import repo
    from api.auth.passwords import verify_password
    from api.auth.service import issue_password_reset, issue_verify_email
    from api.auth.tokens import hash_token
    from api.db import db_ping
    from api.main import app
    from api.redis_client import ping
    from api.settings import SITE_MANIFEST

    require(db_ping(), "database_unavailable")
    require(ping(), "rate_limit_store_unavailable")
    email = f"journey-{secrets.token_hex(10)}@example.test"
    password = f"Synthetic-{secrets.token_urlsafe(20)}-9aA!"
    replacement = f"Synthetic-{secrets.token_urlsafe(20)}-8bB!"

    def token_from_outbox(subject: str) -> str:
        # Separate read-only fixture observer. API requests use the restricted
        # runtime role and cannot read mail/token bodies from the outbox.
        with (
            closing(
                psycopg2.connect(
                    host="127.0.0.1",
                    dbname="base2",
                    user="base2",
                    password=os.environ["JOURNEY_OUTBOX_READ_PASSWORD"],
                    options="-c default_transaction_read_only=on",
                )
            ) as conn,
            conn.cursor() as cursor,
        ):
            cursor.execute(
                "SELECT body_text FROM api_email_outbox WHERE to_email=%s AND subject=%s ORDER BY created_at DESC LIMIT 1",
                (email, subject),
            )
            row = cursor.fetchone()
        require(row is not None, "outbox_message_missing")
        match = re.search(r"token=([A-Za-z0-9_-]+)", row[0])
        require(match is not None, "outbox_link_missing")
        return match.group(1)

    with patch("api.tasks.app.send_task") as handoff, TestClient(app) as client:
        response = client.post(
            "/api/auth/register",
            json={"email": email, "password": password},
            headers={"X-Tenant-Id": SITE_MANIFEST["siteId"]},
        )
        require(response.status_code == 201, "registration_failed")
        require(
            isinstance(response.json().get("permissions"), list), "navigation_permissions_missing"
        )
        recovery = client.post("/api/auth/resend-verification", json={"email": email})
        require(recovery.status_code == 202, "verification_recovery_failed")
        limited = client.post("/api/auth/resend-verification", json={"email": email})
        require(limited.status_code == 429, "verification_recovery_limit_missing")
        require(int(limited.headers.get("Retry-After", "0")) > 0, "verification_retry_missing")
        # Real Redis counters must admit only one concurrent request for a
        # recipient. Freeze the bucket timestamp, not Redis or the route.
        from api.security import rate_limit

        unknown_email = f"unknown-{secrets.token_hex(10)}@example.test"

        def concurrent_resend(_):
            with TestClient(app) as concurrent_client:
                return concurrent_client.post(
                    "/api/auth/resend-verification", json={"email": unknown_email}
                ).status_code

        with patch("api.security.rate_limit.now_ms", return_value=rate_limit.now_ms()):
            with ThreadPoolExecutor(max_workers=2) as executor:
                statuses = sorted(executor.map(concurrent_resend, range(2)))
        require(statuses == [202, 429], "verification_concurrent_limit_missing")
        require(
            client.post(
                "/api/auth/register", json={"email": email, "password": password}
            ).status_code
            == 400,
            "duplicate_registration_not_rejected",
        )
        user = repo.get_user_by_email(email)
        require(user is not None, "registration_not_persisted")
        with patch("api.auth.repo._utcnow", return_value=datetime.now(UTC) - timedelta(minutes=5)):
            issue_verify_email(email=email, host="localhost", proto="http", ttl_minutes=1)
        expired_verification = token_from_outbox("Verify your email")
        expired_record = repo.find_one_time_token(
            token_hash=hash_token(expired_verification), token_type="verify_email"
        )
        require(
            expired_record["expires_at"] < datetime.now(UTC), "verification_fixture_not_expired"
        )
        require(
            client.post("/api/auth/verify-email", json={"token": expired_verification}).status_code
            == 400,
            "expired_verification_accepted",
        )
        require(
            not repo.get_user_by_id(user.id).is_email_verified, "expired_verification_mutated_user"
        )
        issue_verify_email(email=email, host="localhost", proto="http")
        verification = token_from_outbox("Verify your email")
        require(
            client.post("/api/auth/verify-email", json={"token": verification}).status_code == 200,
            "verification_failed",
        )
        require(repo.get_user_by_id(user.id).is_email_verified, "verification_not_persisted")
        require(
            client.post("/api/auth/verify-email", json={"token": verification}).status_code == 400,
            "verification_replay_accepted",
        )

        # The revocation assertion must begin with a real session, not an empty
        # table that would let a broken reset implementation pass vacuously.
        initial_login = client.post("/api/auth/login", json={"email": email, "password": password})
        require(initial_login.status_code == 200, "initial_login_failed")
        require(
            bool(repo.list_active_refresh_sessions(user_id=user.id)),
            "reset_session_fixture_missing",
        )
        client.cookies.clear()
        missing = client.post(
            "/api/auth/forgot-password",
            json={"email": f"missing-{secrets.token_hex(10)}@example.test"},
        )
        existing = client.post("/api/auth/forgot-password", json={"email": email})
        require(
            missing.status_code == existing.status_code == 200
            and missing.json() == existing.json(),
            "recovery_enumeration_difference",
        )
        reset = token_from_outbox("Reset your password")
        require(
            client.post(
                "/api/auth/reset-password", json={"token": reset, "password": replacement}
            ).status_code
            == 200,
            "reset_failed",
        )
        require(
            verify_password(replacement, repo.get_user_by_id(user.id).password_hash),
            "replacement_not_persisted",
        )
        require(
            client.post(
                "/api/auth/reset-password", json={"token": reset, "password": password}
            ).status_code
            == 400,
            "reset_replay_accepted",
        )
        require(
            not repo.list_active_refresh_sessions(user_id=user.id), "reset_sessions_not_revoked"
        )
        require(
            client.post("/api/auth/login", json={"email": email, "password": password}).status_code
            == 401,
            "old_password_accepted",
        )
        login = client.post("/api/auth/login", json={"email": email, "password": replacement})
        require(login.status_code == 200, "replacement_login_failed")
        headers = {
            "Authorization": f"Bearer {login.json()['access_token']}",
            "X-Tenant-Id": SITE_MANIFEST["siteId"],
        }
        before = client.get("/api/settings/preferences", headers=headers)
        require(before.status_code == 200, "preferences_read_failed")
        preferences = {
            "expected_version": before.json()["version"],
            "theme": "dark",
            "contrast": "high",
            "motion": "reduced",
            "density": "compact",
            "locale": SITE_MANIFEST["defaultLocale"],
            "timezone": "Europe/Budapest",
            "week_start": "monday",
        }
        saved = client.put("/api/settings/preferences", headers=headers, json=preferences)
        require(saved.status_code == 200, "preferences_write_failed")
        require(
            client.put("/api/settings/preferences", headers=headers, json=preferences).status_code
            == 409,
            "stale_preferences_overwritten",
        )
        reread = client.get("/api/settings/preferences", headers=headers)
        require(
            reread.status_code == 200
            and all(
                reread.json()[key] == value
                for key, value in preferences.items()
                if key != "expected_version"
            ),
            "preferences_not_persisted",
        )
        marketing = {"event_family": "marketing", "channel": "email", "delivery": "disabled"}
        notification = client.put(
            "/api/settings/notifications", headers=headers, json={"preferences": [marketing]}
        )
        require(notification.status_code == 200, "notifications_write_failed")
        notifications = client.get("/api/settings/notifications", headers=headers)
        require(
            notifications.status_code == 200
            and any(
                all(item.get(key) == value for key, value in marketing.items())
                for item in notifications.json()["preferences"]
            ),
            "notifications_not_persisted",
        )
        forbidden = {"event_family": "security", "channel": "email", "delivery": "disabled"}
        require(
            client.put(
                "/api/settings/notifications", headers=headers, json={"preferences": [forbidden]}
            ).status_code
            == 422,
            "mandatory_notifications_disabled",
        )
        # Production clamps TTL to at least one minute. Backdate only fixture
        # issuance; do not change the service's real expiry validation clock.
        with patch("api.auth.repo._utcnow", return_value=datetime.now(UTC) - timedelta(minutes=5)):
            issue_password_reset(email=email, host="localhost", proto="http", ttl_minutes=1)
        expired = token_from_outbox("Reset your password")
        expired_record = repo.find_one_time_token(
            token_hash=hash_token(expired), token_type="password_reset"
        )
        require(expired_record["expires_at"] < datetime.now(UTC), "fixture_not_actually_expired")
        require(
            client.post(
                "/api/auth/reset-password", json={"token": expired, "password": password}
            ).status_code
            == 400,
            "expired_reset_accepted",
        )
        require(handoff.call_count >= 3, "outbox_handoff_missing")
    print(
        "Synthetic recovery/settings: registration, duplicate, verification, replay, reset, session revocation, password rotation, expiry, preference persistence/conflicts and mandatory notifications passed; external delivery disabled."
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # Fixed diagnostic codes only; upstream exceptions can contain private data.
        if type(exc) is JourneyFailure:
            code = str(exc)
        else:
            # Class and source line identify infrastructure failures without
            # exposing database error strings, query parameters or mail tokens.
            frames = traceback.extract_tb(exc.__traceback__)
            line = frames[-1].lineno if frames else 0
            code = f"recovery_journey_failed:{type(exc).__name__}:line_{line}"
        print(f"Recovery journey failed: {code}")
        raise SystemExit(1) from None
