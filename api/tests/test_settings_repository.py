from contextlib import contextmanager
from uuid import UUID

from api.repositories import settings as repository


USER = UUID('00000000-0000-0000-0000-000000001103')


class Cursor:
    def __init__(self, rows=()):
        self.rows = list(rows)
        self.calls = []
        self.rowcount = 1

    def __enter__(self): return self
    def __exit__(self, *_): return False
    def execute(self, sql, params=()): self.calls.append((' '.join(sql.split()), params))
    def fetchone(self): return self.rows.pop(0) if self.rows else None
    def fetchall(self): return list(self.rows)


class Connection:
    def __init__(self, cursor):
        self.value = cursor
        self.autocommit = True
        self.commits = 0
        self.rollbacks = 0

    def cursor(self): return self.value
    def commit(self): self.commits += 1
    def rollback(self): self.rollbacks += 1


def bind(monkeypatch, conn):
    @contextmanager
    def fake_db_conn():
        yield conn
    monkeypatch.setattr(repository, 'db_conn', fake_db_conn)


def test_defaults_are_copy_safe_and_read_is_exact_user_tenant_bound(monkeypatch):
    cursor = Cursor()
    bind(monkeypatch, Connection(cursor))
    first = repository.get_preferences(user_id=USER, tenant_id='tenant-a')
    first['theme'] = 'dark'
    second = repository.get_preferences(user_id=USER, tenant_id='tenant-b')
    assert second == repository.DEFAULTS
    assert cursor.calls[0][1] == (str(USER), 'tenant-a')
    assert cursor.calls[1][1] == (str(USER), 'tenant-b')


def test_stale_preference_update_rolls_back_without_write(monkeypatch):
    cursor = Cursor(rows=[(3,)])
    conn = Connection(cursor)
    bind(monkeypatch, conn)
    result = repository.update_preferences(
        user_id=USER, tenant_id='tenant-a', expected_version=2,
        values={key: str(value) for key, value in repository.DEFAULTS.items() if key not in {'schema_version', 'version'}},
    )
    assert result is None
    assert conn.rollbacks == 1
    assert conn.commits == 0
    assert len(cursor.calls) == 1
    assert cursor.calls[0][1] == (str(USER), 'tenant-a')


def test_first_preference_write_is_atomic_and_tenant_bound(monkeypatch):
    cursor = Cursor(rows=[])
    conn = Connection(cursor)
    bind(monkeypatch, conn)
    monkeypatch.setattr(repository, 'get_preferences', lambda **kwargs: {**repository.DEFAULTS, 'version': 1, **kwargs})
    values = {key: str(value) for key, value in repository.DEFAULTS.items() if key not in {'schema_version', 'version'}}
    result = repository.update_preferences(user_id=USER, tenant_id='tenant-a', expected_version=0, values=values)
    assert result['version'] == 1
    assert conn.commits == 1
    insert = cursor.calls[1]
    assert 'INSERT INTO api_user_preferences' in insert[0]
    assert insert[1][1:3] == (str(USER), 'tenant-a')


def test_notification_replace_deletes_and_inserts_only_exact_owner_scope(monkeypatch):
    cursor = Cursor()
    conn = Connection(cursor)
    bind(monkeypatch, conn)
    monkeypatch.setattr(repository, 'list_notifications', lambda **kwargs: [{**kwargs, 'event_family': 'security'}])
    result = repository.replace_notifications(
        user_id=USER, tenant_id='tenant-a',
        preferences=[{'event_family': 'security', 'channel': 'email', 'delivery': 'immediate', 'mandatory': True}],
    )
    assert conn.commits == 1
    assert cursor.calls[0][1] == (str(USER), 'tenant-a')
    assert cursor.calls[1][1][1:3] == (str(USER), 'tenant-a')
    assert result[0]['tenant_id'] == 'tenant-a'


def test_security_projection_clamps_limit_and_never_selects_metadata_or_ip(monkeypatch):
    cursor = Cursor(rows=[('event-1', 'auth.login', '2026-08-30T00:00:00Z', 'A' * 200)])
    bind(monkeypatch, Connection(cursor))
    events = repository.security_events(user_id=USER, limit=500)
    sql, params = cursor.calls[0]
    assert params == (str(USER), 50)
    assert 'metadata' not in sql.lower() and ',ip' not in sql.lower()
    assert len(events[0]['device']) == 120
