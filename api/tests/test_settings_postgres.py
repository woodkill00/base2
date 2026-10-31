"""Real PostgreSQL persistence, distinct from the restricted-runtime RLS drill.

Run against an isolated migrated test database. Every fixture has a random owner
and cleanup targets only those exact owners. This does not prove runtime-role RLS.
"""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from threading import Barrier
from uuid import uuid4

import pytest

from api.db import db_conn
from api.repositories import settings as repository
from api.routes.settings import NotificationUpdate, _notification_payload

pytestmark = pytest.mark.integration


@pytest.fixture
def owners():
    ids = [uuid4(), uuid4()]
    with db_conn() as conn, conn.cursor() as cur:
        for user_id in ids:
            cur.execute(
                'INSERT INTO api_auth_users(id,email,password_hash) VALUES (%s,%s,%s)',
                (str(user_id), f'{user_id}@example.test', 'disabled-synthetic-fixture'),
            )
        conn.commit()
    try:
        yield ids
    finally:
        with db_conn() as conn, conn.cursor() as cur:
            for user_id in ids:
                cur.execute('DELETE FROM api_auth_users WHERE id=%s', (str(user_id),))
            conn.commit()


def test_concurrent_first_save_is_one_exact_success_and_one_conflict(monkeypatch, owners):
    gate = Barrier(2, timeout=10)
    original = repository.db_conn

    class Cursor:
        def __init__(self, cursor): self.cursor = cursor
        def __enter__(self):
            self.cursor.__enter__()
            return self
        def __exit__(self, *args): return self.cursor.__exit__(*args)
        def __getattr__(self, key): return getattr(self.cursor, key)
        def execute(self, sql, params):
            result = self.cursor.execute(sql, params)
            if sql.startswith('SELECT version FROM api_user_preferences'):
                # Force both transactions to observe the missing initial row.
                gate.wait()
            return result

    class Connection:
        def __init__(self, connection): self.connection = connection
        def cursor(self): return Cursor(self.connection.cursor())
        def __getattr__(self, key): return getattr(self.connection, key)

    @contextmanager
    def synchronized(*, tenant_id=None):
        with original(tenant_id=tenant_id) as conn:
            yield Connection(conn)

    monkeypatch.setattr(repository, 'db_conn', synchronized)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(
            repository.update_preferences, user_id=owners[0], tenant_id='settings-test',
            expected_version=0, values={**repository.DEFAULTS, 'theme': theme},
        ) for theme in ('light', 'dark')]
        results = [future.result(timeout=20) for future in futures]
    monkeypatch.setattr(repository, 'db_conn', original)
    assert sum(result is None for result in results) == 1
    winner = next(result for result in results if result is not None)
    assert winner['version'] == 1
    saved = repository.get_preferences(user_id=owners[0], tenant_id='settings-test')
    assert saved == winner
    assert repository.get_preferences(user_id=owners[1], tenant_id='settings-test')['version'] == 0
    assert repository.get_preferences(user_id=owners[0], tenant_id='another-settings-test')['version'] == 0
    assert repository.update_preferences(
        user_id=owners[0], tenant_id='settings-test', expected_version=0,
        values=repository.DEFAULTS,
    ) is None
    next_snapshot = repository.update_preferences(
        user_id=owners[0], tenant_id='settings-test', expected_version=1,
        values={**repository.DEFAULTS, 'theme': 'dark'},
    )
    assert next_snapshot['version'] == 2
    assert next_snapshot['theme'] == 'dark'


def test_notification_timestamp_roundtrip_and_repeat_save_stay_owner_scoped(owners):
    choices = [{'event_family': 'marketing', 'channel': 'email', 'delivery': 'digest', 'mandatory': False}]
    saved = repository.replace_notifications(
        user_id=owners[0], tenant_id='settings-test', preferences=choices,
    )
    assert saved[0]['updated_at'] is not None
    for _ in range(2):
        request = NotificationUpdate.model_validate({'preferences': [
            {key: row[key] for key in ('event_family', 'channel', 'delivery')}
            for row in saved
        ]})
        saved = repository.replace_notifications(
            user_id=owners[0], tenant_id='settings-test',
            preferences=_notification_payload(request.preferences),
        )
        assert saved[0]['delivery'] == 'digest'
        assert saved[0]['updated_at'] is not None
    assert repository.list_notifications(user_id=owners[1], tenant_id='settings-test') == []
    assert repository.list_notifications(user_id=owners[0], tenant_id='another-settings-test') == []
