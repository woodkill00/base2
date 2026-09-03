from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any


class CursorError(ValueError):
    pass


def canonical_digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
    return hashlib.sha256(encoded).hexdigest()


class CursorCodec:
    """Opaque, expiring cursor bound to the complete query authorization scope."""

    def __init__(self, secret: str, *, ttl_seconds: int = 900):
        if len(secret.encode()) < 16 or not 60 <= ttl_seconds <= 3600:
            raise ValueError('cursor_configuration_invalid')
        self._secret = secret.encode()
        self._ttl = ttl_seconds

    def encode(
        self, *, scope: dict[str, Any], position: dict[str, Any], now: int | None = None
    ) -> str:
        issued = int(time.time() if now is None else now)
        payload = {
            'v': 1,
            'iat': issued,
            'exp': issued + self._ttl,
            'scope': scope,
            'position': position,
        }
        body = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()
        signature = hmac.new(self._secret, body, hashlib.sha256).digest()
        return base64.urlsafe_b64encode(body + signature).decode().rstrip('=')

    def decode(
        self, token: str, *, expected_scope: dict[str, Any], now: int | None = None
    ) -> dict[str, Any]:
        try:
            padded = token + '=' * (-len(token) % 4)
            raw = base64.urlsafe_b64decode(padded.encode())
            body, supplied = raw[:-32], raw[-32:]
            expected = hmac.new(self._secret, body, hashlib.sha256).digest()
            if not hmac.compare_digest(supplied, expected):
                raise CursorError('content_query_invalid')
            payload = json.loads(body)
            current = int(time.time() if now is None else now)
            if (
                payload.get('v') != 1
                or payload.get('scope') != expected_scope
                or not isinstance(payload.get('position'), dict)
                or current > int(payload.get('exp', 0))
                or current < int(payload.get('iat', 0)) - 30
            ):
                raise CursorError('content_query_invalid')
            return payload['position']
        except CursorError:
            raise
        except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
            raise CursorError('content_query_invalid') from exc
