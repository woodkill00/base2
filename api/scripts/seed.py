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
    # Ensure schema exists before seeding (idempotent).
    try:
        from api.migrations.runner import apply_migrations

        apply_migrations()
    except Exception:
        # If migrations fail here, the API container would also fail later; surface clearly.
        print("Seed failed: unable to apply migrations", file=sys.stderr)
        raise

    admin_email = _env("SEED_ADMIN_EMAIL")
    admin_password = _env("SEED_ADMIN_PASSWORD")
    if not admin_email or not admin_password:
        print(
            "Missing SEED_ADMIN_EMAIL/SEED_ADMIN_PASSWORD. Set them in .env before running seed.",
            file=sys.stderr,
        )
        return 2

    demo_password = _env("SEED_DEMO_PASSWORD", admin_password)

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
