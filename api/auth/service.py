from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import os
from uuid import UUID

import secrets

from api.auth import repo
from api.auth.passwords import hash_password, verify_password
from api.auth.tokens import create_access_token, hash_token, new_refresh_token


@dataclass(frozen=True)
class AuthTokens:
    access_token: str
    refresh_token: str
    refresh_token_expires_at: datetime


def _public_base_url_from_headers(*, host: str | None, proto: str | None) -> str:
    h = (host or "").strip()
    p = (proto or "").strip()
    if not h:
        h = "localhost"
    if not p:
        p = "https"
    return f"{p}://{h}".rstrip("/")


def _new_one_time_token() -> str:
    # URL-safe token suitable for query parameters.
    return secrets.token_urlsafe(32)


def issue_verify_email(*, email: str, host: str | None, proto: str | None, request_id: str | None = None, ttl_minutes: int = 60 * 24) -> None:
    user = repo.get_user_by_email(email)
    if user is None:
        return
    if user.is_email_verified:
        return

    raw = _new_one_time_token()
    repo.create_one_time_token(
        user_id=user.id,
        token_hash=hash_token(raw),
        token_type="verify_email",
        ttl_minutes=ttl_minutes,
    )

    base = _public_base_url_from_headers(host=host, proto=proto)
    url = f"{base}/verify-email?token={raw}"
    body = f"Verify your email by visiting: {url}"

    try:
        from api.services.email_service import queue_email

        queue_email(
            to_email=user.email,
            subject="Verify your email",
            body_text=body,
            body_html="",
            request_id=request_id,
            send_async=True,
        )
    except Exception:
        # Never fail the request path.
        pass


def verify_email(*, token: str) -> UUID:
    if not token:
        raise ValueError("invalid_token")

    rec = repo.find_one_time_token(token_hash=hash_token(token), token_type="verify_email")
    if rec is None:
        raise ValueError("invalid_token")

    if rec.get("consumed_at") is not None:
        raise ValueError("invalid_token")

    expires_at = rec.get("expires_at")
    if expires_at is not None:
        now = datetime.now(expires_at.tzinfo) if getattr(expires_at, "tzinfo", None) else datetime.utcnow()
        if expires_at <= now:
            raise ValueError("invalid_token")

    user_id = rec.get("user_id")
    if user_id is None:
        raise ValueError("invalid_token")

    repo.set_user_email_verified(user_id=user_id)
    repo.consume_one_time_token(token_id=rec["id"])

    return user_id


def issue_password_reset(*, email: str, host: str | None, proto: str | None, request_id: str | None = None, ttl_minutes: int = 60) -> None:
    user = repo.get_user_by_email(email)
    if user is None:
        return
    if not user.is_active:
        return

    raw = _new_one_time_token()
    repo.create_one_time_token(
        user_id=user.id,
        token_hash=hash_token(raw),
        token_type="password_reset",
        ttl_minutes=ttl_minutes,
    )

    base = _public_base_url_from_headers(host=host, proto=proto)
    url = f"{base}/reset-password?token={raw}"
    body = f"Reset your password by visiting: {url}"

    try:
        from api.services.email_service import queue_email

        queue_email(
            to_email=user.email,
            subject="Reset your password",
            body_text=body,
            body_html="",
            request_id=request_id,
            send_async=True,
        )
    except Exception:
        pass


def reset_password(*, token: str, new_password: str) -> UUID:
    if not token:
        raise ValueError("invalid_token")

    _validate_password_or_raise(new_password)

    rec = repo.find_one_time_token(token_hash=hash_token(token), token_type="password_reset")
    if rec is None:
        raise ValueError("invalid_token")

    if rec.get("consumed_at") is not None:
        raise ValueError("invalid_token")

    expires_at = rec.get("expires_at")
    if expires_at is not None:
        now = datetime.now(expires_at.tzinfo) if getattr(expires_at, "tzinfo", None) else datetime.utcnow()
        if expires_at <= now:
            raise ValueError("invalid_token")

    user_id = rec.get("user_id")
    if user_id is None:
        raise ValueError("invalid_token")

    repo.set_user_password_hash(user_id=user_id, password_hash=hash_password(new_password))
    repo.consume_one_time_token(token_id=rec["id"])
    repo.revoke_all_refresh_tokens(user_id=user_id)

    return user_id


def register_user(*, email: str, password: str, ip: str, user_agent: str, refresh_ttl_days: int, access_ttl_minutes: int) -> tuple[repo.User, AuthTokens]:
    _validate_password_or_raise(password)

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

    # Always return generic invalid credentials.
    if not user.is_active:
        repo.insert_audit_event(user_id=user.id, action="auth.login_failed", ip=ip, user_agent=user_agent)
        raise ValueError("invalid_credentials")

    # Account lockout window.
    try:
        st = repo.get_user_lock_state(user_id=user.id)
        locked_until = st.get("locked_until")
        if locked_until is not None:
            now = datetime.now(locked_until.tzinfo) if getattr(locked_until, "tzinfo", None) else datetime.utcnow()
            if locked_until > now:
                repo.insert_audit_event(user_id=user.id, action="auth.login_locked", ip=ip, user_agent=user_agent)
                raise ValueError("invalid_credentials")
    except ValueError:
        raise
    except Exception:
        # Never block login because lock metadata couldn't be read.
        pass

    if not verify_password(password, user.password_hash):
        repo.insert_audit_event(user_id=user.id, action="auth.login_failed", ip=ip, user_agent=user_agent)
        try:
            max_failures = int(os.getenv("AUTH_LOCKOUT_MAX_FAILURES", "5") or 5)
            lock_minutes = int(os.getenv("AUTH_LOCKOUT_MINUTES", "15") or 15)
            st = repo.register_login_failure(user_id=user.id, max_failures=max_failures, lock_minutes=lock_minutes)
            if st.get("locked_until") is not None and int(st.get("failed_login_attempts") or 0) >= max_failures:
                repo.insert_audit_event(user_id=user.id, action="auth.account_locked", ip=ip, user_agent=user_agent)
        except Exception:
            pass
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

    try:
        repo.reset_login_failures(user_id=user.id)
    except Exception:
        pass

    repo.insert_audit_event(user_id=user.id, action="auth.login", ip=ip, user_agent=user_agent)

    return user, AuthTokens(access_token=access, refresh_token=refresh, refresh_token_expires_at=refresh_expires_at)


def _validate_password_or_raise(password: str) -> None:
    pwd = str(password or "")
    if len(pwd) < 8:
        raise ValueError("invalid_password")
    has_lower = any(c.islower() for c in pwd)
    has_upper = any(c.isupper() for c in pwd)
    has_digit = any(c.isdigit() for c in pwd)
    if not (has_lower and has_upper and has_digit):
        raise ValueError("invalid_password")


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

    try:
        repo.touch_refresh_token(token_id=rec["id"], ip=ip, user_agent=user_agent)
    except Exception:
        # Never fail refresh because of session bookkeeping.
        pass

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
