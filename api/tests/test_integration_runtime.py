import pytest

from api.redis_client import ping as redis_ping
from api.db import db_ping


pytestmark = [pytest.mark.integration]


def test_redis_ping_succeeds():
    assert redis_ping() is True


def test_db_ping_succeeds():
    assert db_ping() is True
