from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from uuid import UUID
from types import SimpleNamespace
from psycopg2.errors import RaiseException
import pytest
from api.repositories.scheduling import SchedulingRepository


class Rejection(RaiseException):
    @property
    def diag(self):
        return SimpleNamespace(message_primary=str(self))


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
        if 'base2_reserve_booking' in sql and self.mode != 'success':
            raise Rejection(self.mode)

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
        if 'base2_reserve_booking' in self.sql:
            return (UUID(int=2), 'confirmed', False)
        if 'SELECT capacity' in self.sql:
            return (
                2,
                self.mode != 'closed',
                datetime.now(UTC) + timedelta(hours=-1 if self.mode == 'expired' else 1),
            )
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
    assert result['status'] == 'confirmed' and reserved.committed
    assert 'base2_reserve_booking' in reserved.cursor_value.sql
    assert not reserved.cursor_value.inserted
    assert not hasattr(reserved, 'autocommit')


def test_missing_result_rolls_back_without_insert():
    connection = Connection()
    connection.cursor_value.fetchone = lambda: None
    with (
        patch('api.repositories.scheduling.db_conn', lambda **_: context(connection)),
        pytest.raises(RuntimeError, match='booking_result_missing'),
    ):
        SchedulingRepository().reserve(
            site_id='tenant-one', event_id=UUID(int=1), attendee_ref='user', seats=1
        )
    assert connection.rolled and not connection.cursor_value.inserted


@pytest.mark.parametrize(
    'mode',
    [
        'booking_closed',
        'event_not_found',
        'booking_invalid',
        'booking_replay_conflict',
        'capacity_exceeded',
    ],
)
def test_database_rejection_rolls_back(mode):
    connection = Connection(mode)
    with patch(
        'api.repositories.scheduling.db_conn', lambda **_: context(connection)
    ), pytest.raises(ValueError, match=mode):
        SchedulingRepository().reserve(
            site_id='tenant-one', event_id=UUID(int=1), attendee_ref='user', seats=1
        )
    assert connection.rolled and not connection.committed
    assert not connection.cursor_value.inserted


def test_unknown_database_rejection_is_sanitized():
    connection = Connection('private database details')
    with patch(
        'api.repositories.scheduling.db_conn', lambda **_: context(connection)
    ), pytest.raises(RuntimeError, match='^booking_database_rejected$'):
        SchedulingRepository().reserve(
            site_id='tenant-one', event_id=UUID(int=1), attendee_ref='user', seats=1
        )
    assert connection.rolled
