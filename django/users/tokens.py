from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from users.models import OneTimeToken


def hash_one_time_token(raw_token: str) -> str:
    # Use Django SECRET_KEY as a pepper. Raw tokens are never stored.
    material = f"{settings.SECRET_KEY}:{raw_token}".encode()
    return hashlib.sha256(material).hexdigest()


def mint_one_time_token(
    *,
    user,
    purpose: str,
    email: str,
    ttl: timedelta,
) -> tuple[str, OneTimeToken]:
    raw = secrets.token_urlsafe(32)
    token_hash = hash_one_time_token(raw)
    token = OneTimeToken.objects.create(
        user=user,
        purpose=purpose,
        email=email,
        token_hash=token_hash,
        expires_at=timezone.now() + ttl,
    )
    return raw, token


def get_valid_one_time_token(*, raw_token: str, purpose: str) -> OneTimeToken | None:
    token_hash = hash_one_time_token(raw_token)
    now = timezone.now()

    token = (
        OneTimeToken.objects.select_related("user")
        .filter(purpose=purpose, token_hash=token_hash, consumed_at__isnull=True)
        .first()
    )
    if token is None:
        return None

    if token.expires_at and token.expires_at <= now:
        return None

    return token


def consume_one_time_token(*, raw_token: str, purpose: str) -> OneTimeToken | None:
    token = get_valid_one_time_token(raw_token=raw_token, purpose=purpose)
    if token is None:
        return None

    token.consumed_at = timezone.now()
    token.save(update_fields=["consumed_at"])
    return token
