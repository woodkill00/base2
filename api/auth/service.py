from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

from api.auth import repo
from api.auth.passwords import hash_password, verify_password
from api.auth.tokens import create_access_token, hash_token, new_refresh_token


@dataclass(frozen=True)
class AuthTokens:
    access_token: str
    refresh_token: str
    refresh_token_expires_at: datetime


def register_user(*, email: str, password: str, ip: str, user_agent: str, refresh_ttl_days: int, access_ttl_minutes: int) -> tuple[repo.User, AuthTokens]:
    existing = repo.get_user_by_email(email)
    if existing is not None:
        raise ValueError("email_taken")

    user = repo.create_user(email=email, password_hash=hash_password(password))

    refresh = new_refresh_token()
    refresh_hash = hash_token(refresh)
    _token_id, refresh_expires_at = repo.create_refresh_token(
        user_id=user.id,
        token_hash=refresh_hash,
        ttl_days=refresh_ttl_days,
        ip=ip,
        user_agent=user_agent,
    )

    access = create_access_token(subject=str(user.id), email=user.email, ttl_minutes=access_ttl_minutes)

    repo.insert_audit_event(user_id=user.id, action="user.register", ip=ip, user_agent=user_agent)

    return user, AuthTokens(access_token=access, refresh_token=refresh, refresh_token_expires_at=refresh_expires_at)


def login_user(*, email: str, password: str, ip: str, user_agent: str, refresh_ttl_days: int, access_ttl_minutes: int) -> tuple[repo.User, AuthTokens]:
    user = repo.get_user_by_email(email)
    if user is None:
        repo.insert_audit_event(user_id=None, action="auth.login_failed", ip=ip, user_agent=user_agent, metadata={"email": email.strip().lower()})
        raise ValueError("invalid_credentials")

    if not user.is_active:
        raise ValueError("inactive")

    if not verify_password(password, user.password_hash):
        repo.insert_audit_event(user_id=user.id, action="auth.login_failed", ip=ip, user_agent=user_agent)
        raise ValueError("invalid_credentials")

    refresh = new_refresh_token()
    refresh_hash = hash_token(refresh)
    _token_id, refresh_expires_at = repo.create_refresh_token(
        user_id=user.id,
        token_hash=refresh_hash,
        ttl_days=refresh_ttl_days,
        ip=ip,
        user_agent=user_agent,
    )

    access = create_access_token(subject=str(user.id), email=user.email, ttl_minutes=access_ttl_minutes)

    repo.insert_audit_event(user_id=user.id, action="auth.login", ip=ip, user_agent=user_agent)

    return user, AuthTokens(access_token=access, refresh_token=refresh, refresh_token_expires_at=refresh_expires_at)


def refresh_tokens(*, refresh_token: str, ip: str, user_agent: str, refresh_ttl_days: int, access_ttl_minutes: int) -> tuple[repo.User, AuthTokens]:
    token_hash = hash_token(refresh_token)
    rec = repo.find_refresh_token(token_hash=token_hash)
    if rec is None:
        raise ValueError("invalid_refresh")

    if rec["revoked_at"] is not None:
        # Reuse detection (basic): revoked token used again.
        repo.insert_audit_event(user_id=rec["user_id"], action="auth.refresh_reuse", ip=ip, user_agent=user_agent)
        raise ValueError("invalid_refresh")

    expires_at = rec["expires_at"]
    if expires_at is not None:
        now = datetime.now(expires_at.tzinfo) if getattr(expires_at, "tzinfo", None) else datetime.utcnow()
        if expires_at <= now:
            raise ValueError("expired_refresh")

    user = repo.get_user_by_id(rec["user_id"])
    if user is None:
        raise ValueError("invalid_refresh")

    new_refresh = new_refresh_token()
    new_refresh_hash = hash_token(new_refresh)
    new_token_id, new_expires_at = repo.create_refresh_token(
        user_id=user.id,
        token_hash=new_refresh_hash,
        ttl_days=refresh_ttl_days,
        ip=ip,
        user_agent=user_agent,
    )

    repo.revoke_refresh_token(token_id=rec["id"], replaced_by_token_id=new_token_id)

    access = create_access_token(subject=str(user.id), email=user.email, ttl_minutes=access_ttl_minutes)

    repo.insert_audit_event(user_id=user.id, action="auth.refresh", ip=ip, user_agent=user_agent)

    return user, AuthTokens(access_token=access, refresh_token=new_refresh, refresh_token_expires_at=new_expires_at)
