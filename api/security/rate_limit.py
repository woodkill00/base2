import time
import os
from typing import Tuple
from api.redis_client import get_client, key

WINDOW_MS = int(os.environ.get("RATE_LIMIT_WINDOW_MS", "900000"))  # 15 minutes default
MAX_REQUESTS = int(os.environ.get("RATE_LIMIT_MAX_REQUESTS", "100"))

# Scope-specific defaults (can be overridden by env).
# NOTE: Keep these conservative; they apply to the public auth surface.
SCOPE_LIMITS: dict[str, tuple[int, int]] = {
    # Fixed-window: 5 requests per minute per IP.
    "auth_login": (60_000, 5),
    "auth_register": (60_000, 5),
    "auth_oauth_google": (60_000, 5),
    # Forgot-password is intentionally a bit higher.
    "forgot_password": (900_000, 10),
    "forgot_password_email": (900_000, 5),
}


def now_ms() -> int:
    return int(time.time() * 1000)


def bucket_start(ts_ms: int) -> int:
    return ts_ms - (ts_ms % WINDOW_MS)


def bucket_start_for_window(ts_ms: int, window_ms: int) -> int:
    return ts_ms - (ts_ms % window_ms)


def _limit_for_scope(scope: str) -> tuple[int, int]:
    """Return (window_ms, max_requests) for the given scope.

    Resolution order:
    1) env overrides: RATE_LIMIT_<SCOPE>_WINDOW_MS / RATE_LIMIT_<SCOPE>_MAX_REQUESTS
    2) in-code defaults (SCOPE_LIMITS)
    3) global defaults (WINDOW_MS / MAX_REQUESTS)
    """
    normalized = (scope or "").strip()
    env_prefix = f"RATE_LIMIT_{normalized.upper()}"

    window_ms, max_requests = SCOPE_LIMITS.get(normalized, (WINDOW_MS, MAX_REQUESTS))

    try:
        window_ms = int(os.environ.get(f"{env_prefix}_WINDOW_MS", str(window_ms)))
    except Exception:
        pass
    try:
        max_requests = int(os.environ.get(f"{env_prefix}_MAX_REQUESTS", str(max_requests)))
    except Exception:
        pass

    return window_ms, max_requests


def incr_and_check(ip: str, scope: str) -> Tuple[int, bool]:
    """Increment counter for (ip, scope) and check if over limit.
    Returns (count, over_limit).
    """
    return incr_and_check_identifier(ip, scope)


def incr_and_check_detailed(ip: str, scope: str) -> tuple[int, bool, int]:
    """Like incr_and_check but also returns Retry-After seconds."""
    return incr_and_check_identifier_detailed(ip, scope)


def incr_and_check_identifier(identifier: str, scope: str) -> Tuple[int, bool]:
    """Increment counter for (identifier, scope) and check if over limit.

    Use this when the limiting key is not an IP address (e.g. email hash).
    Returns (count, over_limit).
    """
    count, over, _retry_after = incr_and_check_identifier_detailed(identifier, scope)
    return count, over


def incr_and_check_identifier_detailed(identifier: str, scope: str) -> tuple[int, bool, int]:
    """Increment counter for (identifier, scope) and check if over limit.

    Returns: (count, over_limit, retry_after_seconds)
    """
    c = get_client()
    ts = now_ms()
    window_ms, max_requests = _limit_for_scope(scope)
    start = bucket_start_for_window(ts, window_ms)
    k = key("rl", scope, identifier, str(start))
    pipe = c.pipeline()
    pipe.incr(k, 1)
    # Set expiry to window length in seconds if key is new
    pipe.pexpire(k, window_ms)
    val, _ = pipe.execute()
    count = int(val)

    over = count > max_requests
    if not over:
        return count, False, 0

    # Seconds remaining in this fixed window.
    remaining_ms = (start + window_ms) - ts
    retry_after = int((remaining_ms + 999) // 1000)
    if retry_after < 1:
        retry_after = 1
    return count, True, retry_after
