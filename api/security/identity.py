from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import struct
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


_ROLE_PERMISSIONS = {
    "owner": frozenset(
        {
            "audit.read",
            "content.read",
            "content.write",
            "credential.create",
            "credential.revoke",
            "invitation.create",
            "invitation.revoke",
            "member.manage",
            "tenant.manage",
        }
    ),
    "admin": frozenset(
        {
            "audit.read",
            "content.read",
            "content.write",
            "credential.create",
            "credential.revoke",
            "invitation.create",
            "invitation.revoke",
            "member.manage",
        }
    ),
    "editor": frozenset({"content.read", "content.write"}),
    "viewer": frozenset({"content.read"}),
}
_REDACTED_KEYS = frozenset(
    {
        "access_token",
        "authorization",
        "client_secret",
        "code",
        "cookie",
        "credential",
        "id_token",
        "password",
        "recovery_code",
        "refresh_token",
        "secret",
        "token",
    }
)


class OAuthStateError(ValueError):
    pass


@dataclass(frozen=True)
class IssuedOAuthState:
    state: str
    browser_binding: str
    nonce: str
    expires_in: int


@dataclass(frozen=True)
class RecoveryCodeBundle:
    plaintext_codes: tuple[str, ...]
    code_hashes: tuple[str, ...]


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _timestamp(value: datetime) -> int:
    if value.tzinfo is None:
        raise ValueError("timezone_required")
    return int(value.timestamp())


def is_allowed(role: str, permission: str) -> bool:
    return permission in _ROLE_PERMISSIONS.get(str(role), frozenset())


def require_recent_reauthentication(
    *, authenticated_at: datetime, now: datetime | None = None, max_age_seconds: int = 300
) -> None:
    current = now or datetime.now(timezone.utc)
    age = _timestamp(current) - _timestamp(authenticated_at)
    if age < 0 or age > max_age_seconds:
        raise PermissionError("recent_reauthentication_required")


def hash_sensitive_value(value: str, *, pepper: str) -> str:
    if not value or not pepper:
        raise ValueError("secret_and_pepper_required")
    return hmac.new(pepper.encode(), value.encode(), hashlib.sha256).hexdigest()


def create_recovery_codes(*, pepper: str, count: int = 8) -> RecoveryCodeBundle:
    if count < 1 or count > 20:
        raise ValueError("invalid_recovery_code_count")
    codes = tuple(f"{secrets.token_hex(4)}-{secrets.token_hex(4)}" for _ in range(count))
    hashes = tuple(hash_sensitive_value(code, pepper=pepper) for code in codes)
    return RecoveryCodeBundle(plaintext_codes=codes, code_hashes=hashes)


def verify_recovery_code(code: str, code_hashes: tuple[str, ...], *, pepper: str) -> bool:
    candidate = hash_sensitive_value(code, pepper=pepper)
    return any(hmac.compare_digest(candidate, stored) for stored in code_hashes)


def generate_totp_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")


def totp_code(secret: str, *, at: datetime | None = None, period: int = 30) -> str:
    current = at or datetime.now(timezone.utc)
    padded = secret.upper() + "=" * (-len(secret) % 8)
    key = base64.b32decode(padded, casefold=True)
    counter = _timestamp(current) // period
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    value = (struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF) % 1_000_000
    return f"{value:06d}"


def verify_totp(
    secret: str, code: str, *, at: datetime | None = None, period: int = 30, window: int = 1
) -> bool:
    if len(str(code)) != 6 or not str(code).isdigit():
        return False
    current = at or datetime.now(timezone.utc)
    timestamp = _timestamp(current)
    for offset in range(-window, window + 1):
        candidate_at = datetime.fromtimestamp(timestamp + offset * period, tz=timezone.utc)
        if hmac.compare_digest(totp_code(secret, at=candidate_at, period=period), str(code)):
            return True
    return False


def redact_audit_metadata(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): (
                "[REDACTED]"
                if str(key).lower() in _REDACTED_KEYS
                else redact_audit_metadata(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_audit_metadata(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_audit_metadata(item) for item in value)
    return value


class OAuthStateSigner:
    def __init__(self, *, secret: str, ttl_seconds: int = 300):
        if len(secret) < 32:
            raise ValueError("oauth_state_secret_too_short")
        if ttl_seconds < 30 or ttl_seconds > 600:
            raise ValueError("invalid_oauth_state_ttl")
        self._secret = secret.encode()
        self.ttl_seconds = ttl_seconds

    def issue(self, *, return_path: str = "/", now: datetime | None = None) -> IssuedOAuthState:
        if not return_path.startswith("/") or return_path.startswith("//") or "\\" in return_path:
            raise OAuthStateError("unsafe_return_path")
        current = now or datetime.now(timezone.utc)
        browser_binding = secrets.token_urlsafe(24)
        nonce = secrets.token_urlsafe(24)
        payload = {
            "binding": hash_sensitive_value(browser_binding, pepper=self._secret.decode()),
            "exp": _timestamp(current) + self.ttl_seconds,
            "iat": _timestamp(current),
            "nonce": nonce,
            "return_path": return_path,
            "v": 1,
        }
        encoded = _b64encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode())
        signature = _b64encode(hmac.new(self._secret, encoded.encode(), hashlib.sha256).digest())
        return IssuedOAuthState(
            state=f"{encoded}.{signature}",
            browser_binding=browser_binding,
            nonce=nonce,
            expires_in=self.ttl_seconds,
        )

    def verify(
        self, state: str, *, browser_binding: str, now: datetime | None = None
    ) -> dict[str, Any]:
        try:
            encoded, supplied_signature = state.split(".", 1)
            expected_signature = _b64encode(
                hmac.new(self._secret, encoded.encode(), hashlib.sha256).digest()
            )
            if not hmac.compare_digest(supplied_signature, expected_signature):
                raise OAuthStateError("state_invalid")
            payload = json.loads(_b64decode(encoded))
        except OAuthStateError:
            raise
        except Exception as exc:
            raise OAuthStateError("state_invalid") from exc

        if payload.get("v") != 1:
            raise OAuthStateError("state_invalid")
        binding_hash = hash_sensitive_value(browser_binding, pepper=self._secret.decode())
        if not hmac.compare_digest(str(payload.get("binding", "")), binding_hash):
            raise OAuthStateError("state_browser_mismatch")
        current = now or datetime.now(timezone.utc)
        if _timestamp(current) > int(payload.get("exp", 0)):
            raise OAuthStateError("state_expired")
        return payload
