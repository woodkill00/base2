from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class GoogleIdentity:
    sub: str
    email: str
    email_verified: bool
    name: str
    picture: str


def verify_google_id_token(*, id_token: str, audience: str) -> GoogleIdentity:
    """Verify a Google ID token and return identity claims.

    Uses google-auth when installed.
    """

    if not id_token or not str(id_token).strip():
        raise ValueError("invalid_token")

    try:
        from google.auth.transport import requests as google_requests  # type: ignore
        from google.oauth2 import id_token as google_id_token  # type: ignore

        req = google_requests.Request()
        claims: dict[str, Any] = google_id_token.verify_oauth2_token(str(id_token), req, str(audience))
    except Exception as e:
        # Do not leak details; treat as invalid.
        raise ValueError("invalid_token") from e

    sub = str(claims.get("sub") or "")
    email = str(claims.get("email") or "").strip().lower()
    email_verified = bool(claims.get("email_verified") is True)
    name = str(claims.get("name") or "")
    picture = str(claims.get("picture") or "")

    if not sub or not email:
        raise ValueError("invalid_token")

    return GoogleIdentity(sub=sub, email=email, email_verified=email_verified, name=name, picture=picture)
