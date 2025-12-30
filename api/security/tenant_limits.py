import os
import time
from typing import Tuple

from api.redis_client import get_client, key


def now_ms() -> int:
    return int(time.time() * 1000)


def bucket_start_for_window(ts_ms: int, window_ms: int) -> int:
    return ts_ms - (ts_ms % window_ms)


def _limit_for_scope(scope: str) -> tuple[int, int]:
    """Return (window_ms, max_requests) for tenant-scoped rate limit.

    Resolution order:
    1) env overrides: TENANT_RATE_LIMIT_<SCOPE>_WINDOW_MS / TENANT_RATE_LIMIT_<SCOPE>_MAX_REQUESTS
    2) defaults: 60s / 5
    """
    normalized = (scope or "").strip()
    env_prefix = f"TENANT_RATE_LIMIT_{normalized.upper()}"

    window_ms = 60_000
    max_requests = 5

    try:
        window_ms = int(os.environ.get(f"{env_prefix}_WINDOW_MS", str(window_ms)))
    except Exception:
        pass
    try:
        max_requests = int(os.environ.get(f"{env_prefix}_MAX_REQUESTS", str(max_requests)))
    except Exception:
        pass

    return window_ms, max_requests


def incr_and_check(tenant_id: str, scope: str) -> Tuple[int, bool]:
    """Increment counter for (tenant_id, scope) and check if over limit.
    Returns (count, over_limit).
    """
    count, over, _ = incr_and_check_detailed(tenant_id, scope)
    return count, over


def incr_and_check_detailed(tenant_id: str, scope: str) -> tuple[int, bool, int]:
    """Increment tenant limit counter and return (count, over_limit, retry_after_seconds)."""
    tenant = (tenant_id or "").strip()
    if not tenant:
        # Treat missing tenant as over-limit to force caller to enforce presence.
        return 0, True, 1

    c = get_client()
    ts = now_ms()
    window_ms, max_requests = _limit_for_scope(scope)
    start = bucket_start_for_window(ts, window_ms)
    k = key("tenant_rl", scope, tenant, str(start))
    pipe = c.pipeline()
    pipe.incr(k, 1)
    pipe.pexpire(k, window_ms)
    val, _ = pipe.execute()
    count = int(val)

    over = count > max_requests
    if not over:
        return count, False, 0

    remaining_ms = (start + window_ms) - ts
    retry_after = int((remaining_ms + 999) // 1000)
    if retry_after < 1:
        retry_after = 1
    return count, True, retry_after


def quota_key(tenant_id: str, quota: str) -> str:
    return key("tenant_quota", quota.strip(), tenant_id.strip())


def check_quota_and_incr(tenant_id: str, quota: str, limit: int, window_seconds: int) -> tuple[int, bool, int]:
    """Increment a tenant quota counter and check exhaustion.

    Returns (count, exhausted, seconds_until_reset).
    """
    tenant = (tenant_id or "").strip()
    if not tenant:
        return 0, True, window_seconds
    c = get_client()
    k = quota_key(tenant, quota)
    pipe = c.pipeline()
    pipe.incr(k, 1)
    # Set expiry only if new (NX not directly supported here; emulate by setting if ttl < 0)
    ttl = c.ttl(k)
    if ttl < 0:
        pipe.expire(k, window_seconds)
    res = pipe.execute()
    # First result is count; ttl may be updated asynchronously; re-read ttl.
    count = int(res[0]) if res else 1
    ttl2 = c.ttl(k)
    exhausted = count > int(limit)
    seconds_until_reset = int(ttl2 if ttl2 > 0 else window_seconds)
    return count, exhausted, seconds_until_reset
