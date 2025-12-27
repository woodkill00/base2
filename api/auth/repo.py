from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

from api.db import db_conn


@dataclass(frozen=True)
class User:
    id: UUID
    email: str
    password_hash: str
    is_active: bool
    is_email_verified: bool
    display_name: str
    avatar_url: str
    bio: str


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def create_user(*, email: str, password_hash: str) -> User:
    user_id = uuid4()
    normalized_email = email.strip().lower()

    with db_conn() as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO api_auth_users(id, email, password_hash)
                VALUES (%s, %s, %s)
                RETURNING id, email, password_hash, is_active, is_email_verified, display_name, avatar_url, bio
                """,
                (str(user_id), normalized_email, password_hash),
            )
            row = cur.fetchone()

    return User(
        id=UUID(str(row[0])),
        email=row[1],
        password_hash=row[2],
        is_active=bool(row[3]),
        is_email_verified=bool(row[4]),
        display_name=row[5] or "",
        avatar_url=row[6] or "",
        bio=row[7] or "",
    )


def get_user_by_email(email: str) -> Optional[User]:
    normalized_email = email.strip().lower()
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, email, password_hash, is_active, is_email_verified, display_name, avatar_url, bio
                FROM api_auth_users
                WHERE email=%s
                """,
                (normalized_email,),
            )
            row = cur.fetchone()

    if not row:
        return None

    return User(
        id=UUID(str(row[0])),
        email=row[1],
        password_hash=row[2],
        is_active=bool(row[3]),
        is_email_verified=bool(row[4]),
        display_name=row[5] or "",
        avatar_url=row[6] or "",
        bio=row[7] or "",
    )


def get_user_by_id(user_id: UUID) -> Optional[User]:
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, email, password_hash, is_active, is_email_verified, display_name, avatar_url, bio
                FROM api_auth_users
                WHERE id=%s
                """,
                (str(user_id),),
            )
            row = cur.fetchone()

    if not row:
        return None

    return User(
        id=UUID(str(row[0])),
        email=row[1],
        password_hash=row[2],
        is_active=bool(row[3]),
        is_email_verified=bool(row[4]),
        display_name=row[5] or "",
        avatar_url=row[6] or "",
        bio=row[7] or "",
    )


def update_profile(*, user_id: UUID, display_name: str | None, avatar_url: str | None, bio: str | None) -> User:
    # Only update provided fields.
    fields: list[str] = []
    values: list[Any] = []

    if display_name is not None:
        fields.append("display_name=%s")
        values.append(display_name)
    if avatar_url is not None:
        fields.append("avatar_url=%s")
        values.append(avatar_url)
    if bio is not None:
        fields.append("bio=%s")
        values.append(bio)

    if not fields:
        u = get_user_by_id(user_id)
        if u is None:
            raise RuntimeError("user_not_found")
        return u

    values.append(str(user_id))

    with db_conn() as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(
                f"""
                UPDATE api_auth_users
                SET {', '.join(fields)}, updated_at=NOW()
                WHERE id=%s
                RETURNING id, email, password_hash, is_active, is_email_verified, display_name, avatar_url, bio
                """,
                tuple(values),
            )
            row = cur.fetchone()

    if not row:
        raise RuntimeError("user_not_found")

    return User(
        id=UUID(str(row[0])),
        email=row[1],
        password_hash=row[2],
        is_active=bool(row[3]),
        is_email_verified=bool(row[4]),
        display_name=row[5] or "",
        avatar_url=row[6] or "",
        bio=row[7] or "",
    )


def insert_audit_event(*, user_id: UUID | None, action: str, ip: str, user_agent: str, metadata: dict[str, Any] | None = None) -> None:
    event_id = uuid4()
    metadata_json = json.dumps(metadata or {})
    with db_conn() as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO api_auth_audit_events(id, user_id, action, ip, user_agent, metadata_json)
                VALUES (%s, %s, %s, %s, %s, %s::jsonb)
                """,
                (str(event_id), (str(user_id) if user_id else None), action, ip or "", user_agent or "", metadata_json),
            )


def create_refresh_token(
    *,
    user_id: UUID,
    token_hash: str,
    ttl_days: int,
    ip: str,
    user_agent: str,
) -> tuple[UUID, datetime]:
    token_id = uuid4()
    expires_at = _utcnow() + timedelta(days=ttl_days)

    with db_conn() as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO api_auth_refresh_tokens(id, user_id, token_hash, expires_at, ip, user_agent)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (str(token_id), str(user_id), token_hash, expires_at, ip or "", user_agent or ""),
            )

    return token_id, expires_at


def find_refresh_token(*, token_hash: str) -> Optional[dict[str, Any]]:
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, user_id, token_hash, expires_at, revoked_at, replaced_by_token_id
                FROM api_auth_refresh_tokens
                WHERE token_hash=%s
                """,
                (token_hash,),
            )
            row = cur.fetchone()

    if not row:
        return None

    return {
        "id": UUID(str(row[0])),
        "user_id": UUID(str(row[1])),
        "token_hash": row[2],
        "expires_at": row[3],
        "revoked_at": row[4],
        "replaced_by_token_id": (UUID(str(row[5])) if row[5] else None),
    }


def revoke_refresh_token(*, token_id: UUID, replaced_by_token_id: UUID | None = None) -> None:
    with db_conn() as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE api_auth_refresh_tokens
                SET revoked_at=NOW(), replaced_by_token_id=%s
                WHERE id=%s
                """,
                (str(replaced_by_token_id) if replaced_by_token_id else None, str(token_id)),
            )


def revoke_all_refresh_tokens(*, user_id: UUID) -> None:
    with db_conn() as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE api_auth_refresh_tokens
                SET revoked_at=NOW()
                WHERE user_id=%s AND revoked_at IS NULL
                """,
                (str(user_id),),
            )


def set_user_email_verified(*, user_id: UUID) -> None:
    with db_conn() as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE api_auth_users
                SET is_email_verified=TRUE, updated_at=NOW()
                WHERE id=%s
                """,
                (str(user_id),),
            )


def set_user_password_hash(*, user_id: UUID, password_hash: str) -> None:
    with db_conn() as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE api_auth_users
                SET password_hash=%s, updated_at=NOW()
                WHERE id=%s
                """,
                (password_hash, str(user_id)),
            )


def create_one_time_token(*, user_id: UUID | None, token_hash: str, token_type: str, ttl_minutes: int) -> tuple[UUID, datetime]:
    token_id = uuid4()
    expires_at = _utcnow() + timedelta(minutes=max(1, int(ttl_minutes)))

    with db_conn() as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO api_auth_one_time_tokens(id, user_id, token_hash, type, expires_at)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (str(token_id), (str(user_id) if user_id else None), token_hash, token_type, expires_at),
            )

    return token_id, expires_at


def find_one_time_token(*, token_hash: str, token_type: str) -> Optional[dict[str, Any]]:
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, user_id, token_hash, type, expires_at, consumed_at
                FROM api_auth_one_time_tokens
                WHERE token_hash=%s AND type=%s
                """,
                (token_hash, token_type),
            )
            row = cur.fetchone()

    if not row:
        return None

    return {
        "id": UUID(str(row[0])),
        "user_id": (UUID(str(row[1])) if row[1] else None),
        "token_hash": row[2],
        "type": row[3],
        "expires_at": row[4],
        "consumed_at": row[5],
    }


def consume_one_time_token(*, token_id: UUID) -> None:
    with db_conn() as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE api_auth_one_time_tokens
                SET consumed_at=NOW()
                WHERE id=%s AND consumed_at IS NULL
                """,
                (str(token_id),),
            )
