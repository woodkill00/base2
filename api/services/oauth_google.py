from __future__ import annotations

import hmac
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class GoogleIdentity:
    sub: str
    email: str
    email_verified: bool
    name: str
    picture: str


def verify_google_id_token(
    *, id_token: str, audience: str, expected_nonce: str | None = None
) -> GoogleIdentity:
    """Verify a Google ID token and return identity claims.

    Uses google-auth when installed.
    """

    if not id_token or not str(id_token).strip():
        raise ValueError('invalid_token')

    try:
        from google.auth.transport import requests as google_requests
        from google.oauth2 import id_token as google_id_token

        req = google_requests.Request()
        claims: dict[str, Any] = google_id_token.verify_oauth2_token(
            str(id_token), req, str(audience)
        )
    except Exception as e:
        # Do not leak details; treat as invalid.
        raise ValueError('invalid_token') from e

    sub = str(claims.get('sub') or '')
    email = str(claims.get('email') or '').strip().lower()
    email_verified = bool(claims.get('email_verified') is True)
    name = str(claims.get('name') or '')
    picture = str(claims.get('picture') or '')

    if not sub or not email:
        raise ValueError('invalid_token')
    if expected_nonce is not None and not hmac.compare_digest(
        str(claims.get('nonce') or ''), expected_nonce
    ):
        raise ValueError('invalid_nonce')

    return GoogleIdentity(
        sub=sub, email=email, email_verified=email_verified, name=name, picture=picture
    )


async def exchange_google_authorization_code(
    *, code: str, client_id: str, client_secret: str, redirect_uri: str
) -> str:
    if not all(str(value).strip() for value in (code, client_id, client_secret, redirect_uri)):
        raise ValueError('oauth_exchange_configuration_invalid')
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            'https://oauth2.googleapis.com/token',
            data={
                'code': code,
                'client_id': client_id,
                'client_secret': client_secret,
                'redirect_uri': redirect_uri,
                'grant_type': 'authorization_code',
            },
            headers={'Accept': 'application/json'},
        )
    if response.status_code != 200:
        raise ValueError('oauth_exchange_rejected')
    try:
        token = str(response.json().get('id_token') or '').strip()
    except Exception as exc:
        raise ValueError('oauth_exchange_rejected') from exc
    if not token:
        raise ValueError('oauth_exchange_rejected')
    return token
