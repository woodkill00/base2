import time
import os
from typing import Tuple
from api.redis_client import get_client, key

WINDOW_MS = int(os.environ.get("RATE_LIMIT_WINDOW_MS", "900000"))  # 15 minutes default
MAX_REQUESTS = int(os.environ.get("RATE_LIMIT_MAX_REQUESTS", "100"))


def now_ms() -> int:
    return int(time.time() * 1000)


def bucket_start(ts_ms: int) -> int:
    return ts_ms - (ts_ms % WINDOW_MS)


def incr_and_check(ip: str, scope: str) -> Tuple[int, bool]:
    """Increment counter for (ip, scope) and check if over limit.
    Returns (count, over_limit).
    """
    c = get_client()
    ts = now_ms()
    start = bucket_start(ts)
    k = key("rl", scope, ip, str(start))
    pipe = c.pipeline()
    pipe.incr(k, 1)
    # Set expiry to window length in seconds if key is new
    pipe.pexpire(k, WINDOW_MS)
    val, _ = pipe.execute()
    count = int(val)
    return count, count > MAX_REQUESTS
