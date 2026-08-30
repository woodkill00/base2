from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from uuid import UUID
import pytest
from api.repositories.scheduling import SchedulingRepository


class Cursor:
    def __init__(self, mode):
        self.mode = mode
        self.sql = ''
        self.inserted = False

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass

    def execute(self, sql, params=()):
        self.sql = sql
        self.params = params
        self.inserted = self.inserted or 'INSERT INTO' in sql

    def fetchall(self):
        return [
            (
                UUID(int=1),
                'launch',
                'Launch',
                datetime.now(UTC),
                datetime.now(UTC) + timedelta(hours=1),
                'UTC',
                2,
                True,
            )
        ]

    def fetchone(self):
        if 'SELECT capacity' in self.sql:
            return (2, True, datetime.now(UTC) + timedelta(hours=1))
        if 'attendee_ref' in self.sql:
            return None
        if 'COALESCE' in self.sql:
            return (0,)
        return None


class Connection:
    def __init__(self, mode='success'):
        self.cursor_value = Cursor(mode)
        self.committed = False
        self.rolled = False

    def cursor(self):
        return self.cursor_value

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled = True


@contextmanager
def context(connection):
    yield connection


def test_lists_tenant_events_and_reserves_atomically():
    repo = SchedulingRepository()
    listed = Connection()
    with patch('api.repositories.scheduling.db_conn', lambda **_: context(listed)):
        assert repo.list_events(site_id='tenant-one')[0]['title'] == 'Launch'
    reserved = Connection()
    with patch('api.repositories.scheduling.db_conn', lambda **_: context(reserved)):
        result = repo.reserve(
            site_id='tenant-one', event_id=UUID(int=1), attendee_ref='user', seats=1
        )
    assert result['status'] == 'confirmed' and reserved.committed and reserved.cursor_value.inserted
    assert not hasattr(reserved, 'autocommit')


def test_missing_event_rolls_back_without_insert():
    connection = Connection()
    connection.cursor_value.fetchone = lambda: None
    with (
        patch('api.repositories.scheduling.db_conn', lambda **_: context(connection)),
        pytest.raises(ValueError, match='event_not_found'),
    ):
        SchedulingRepository().reserve(
            site_id='tenant-one', event_id=UUID(int=1), attendee_ref='user', seats=1
        )
    assert connection.rolled and not connection.cursor_value.inserted
