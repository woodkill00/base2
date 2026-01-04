from __future__ import annotations

import os
import sys
from dataclasses import dataclass

from api.auth.passwords import hash_password
from api.auth.repo import (
    create_user,
    get_user_by_email,
    insert_audit_event,
    set_user_email_verified,
    set_user_password_hash,
)


def _env(name: str, default: str | None = None) -> str | None:
    v = os.getenv(name)
    if v is None:
        return default
    v = str(v).strip()
    return v if v else default


@dataclass(frozen=True)
class SeedUser:
    email: str
    password: str
    verified: bool = True


def _ensure_user(u: SeedUser) -> None:
    existing = get_user_by_email(u.email)
    if existing is None:
        created = create_user(email=u.email, password_hash=hash_password(u.password))
        if u.verified:
            set_user_email_verified(user_id=created.id)
        insert_audit_event(
            user_id=created.id,
            action="seed.user_created",
            ip="seed",
            user_agent="seed-script",
            metadata={"email": u.email},
        )
        return

    # Idempotent behavior: ensure password matches what the caller configured.
    set_user_password_hash(user_id=existing.id, password_hash=hash_password(u.password))
    if u.verified and not existing.is_email_verified:
        set_user_email_verified(user_id=existing.id)

    insert_audit_event(
        user_id=existing.id,
        action="seed.user_updated",
        ip="seed",
        user_agent="seed-script",
        metadata={"email": u.email},
    )


def main() -> int:
    # Schema ownership is Django.
    # Ensure required tables exist before seeding.
    try:
        from api.db import db_conn

        with db_conn() as conn, conn.cursor() as cur:
            cur.execute("SELECT to_regclass('public.api_auth_users')")
            exists = cur.fetchone()[0] is not None
        if not exists:
            print(
                "Seed failed: required tables are missing. Run Django migrations first: "
                "`python manage.py migrate` (using project.settings.production against Postgres).",
                file=sys.stderr,
            )
            return 2
    except Exception as e:
        print(f"Seed failed: unable to verify schema ({e})", file=sys.stderr)
        raise

    admin_email = _env("SEED_ADMIN_EMAIL")
    admin_password = _env("SEED_ADMIN_PASSWORD")
    if admin_email is None or admin_password is None or not admin_email.strip() or not admin_password.strip():
        print(
            "Missing SEED_ADMIN_EMAIL/SEED_ADMIN_PASSWORD. Set them in .env before running seed.",
            file=sys.stderr,
        )
        return 2

    demo_password = _env("SEED_DEMO_PASSWORD", admin_password) or admin_password

    users = [
        SeedUser(email=admin_email, password=admin_password, verified=True),
        SeedUser(email="demo1@base2.local", password=demo_password, verified=True),
        SeedUser(email="demo2@base2.local", password=demo_password, verified=True),
    ]

    for u in users:
        _ensure_user(u)

    print(f"Seed complete: ensured {len(users)} users")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
