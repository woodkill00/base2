import os
import redis

_prefix = os.environ.get("RATE_LIMIT_REDIS_PREFIX", "rate_limit")
_redis_url = os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/0")

_client: redis.Redis | None = None


def get_client() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.from_url(_redis_url)
    return _client


def ping() -> bool:
    try:
        return bool(get_client().ping())
    except Exception:
        return False


def key(*parts: str) -> str:
    return ":".join([_prefix, *parts])
