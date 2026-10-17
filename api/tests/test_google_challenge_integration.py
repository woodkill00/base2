"""Atomic one-use behavior against the disposable integration Redis service."""
from concurrent.futures import ThreadPoolExecutor

import pytest

from api.security import google_challenge

pytestmark = pytest.mark.integration


def test_real_redis_allows_exactly_one_consumer():
    binding, nonce = google_challenge.issue()
    client = google_challenge.redis_client.get_client()
    key = google_challenge._key(binding)
    try:
        assert 0 < client.ttl(key) <= google_challenge.TTL

        def consume():
            try:
                return google_challenge.consume(binding)
            except ValueError:
                return 'rejected'

        with ThreadPoolExecutor(max_workers=2) as workers:
            outcomes = list(workers.map(lambda _: consume(), range(2)))
        assert sorted(outcomes) == sorted([nonce, 'rejected'])
        assert client.get(key) is None
    finally:
        # Only this test's cryptographically unique key, never FLUSHDB.
        client.delete(key)
