from __future__ import annotations

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from jose import jwt


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def get_token_pepper() -> str:
    # Prefer explicit pepper; fall back to JWT secret for staging simplicity.
    pepper = (os.getenv("TOKEN_PEPPER") or "").strip()
    if pepper:
        return pepper
    return (os.getenv("JWT_SECRET") or "").strip()


def hash_token(token: str) -> str:
    pepper = get_token_pepper()
    raw = (token + pepper).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def new_refresh_token() -> str:
    # URL-safe token; 32 bytes is plenty.
    return secrets.token_urlsafe(32)


def create_access_token(*, subject: str, email: str, ttl_minutes: int) -> str:
    secret = (os.getenv("JWT_SECRET") or "").strip()
    if not secret:
        raise RuntimeError("Missing JWT_SECRET")

    now = _utcnow()
    exp = now + timedelta(minutes=ttl_minutes)
    payload: Dict[str, Any] = {
        "sub": subject,
        "email": email,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "jti": secrets.token_hex(16),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def decode_access_token(token: str) -> Dict[str, Any]:
    secret = (os.getenv("JWT_SECRET") or "").strip()
    if not secret:
        raise RuntimeError("Missing JWT_SECRET")
    return jwt.decode(token, secret, algorithms=["HS256"])
