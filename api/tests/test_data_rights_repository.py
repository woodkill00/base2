from contextlib import contextmanager
from datetime import datetime, timezone
from uuid import UUID

from api.repositories import data_rights as repository


USER_ID = UUID('00000000-0000-0000-0000-000000001001')
OPERATION_ID = UUID('00000000-0000-0000-0000-000000001002')


class Cursor:
    def __init__(self, rows=None, rowcount=1):
        self.rows = list(rows or [])
        self.rowcount = rowcount
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, query, params=()):
        self.calls.append((' '.join(query.split()), params))

    def fetchone(self):
        return self.rows.pop(0) if self.rows else None

    def fetchall(self):
        rows, self.rows = self.rows, []
        return rows


class Connection:
    def __init__(self, cursor):
        self._cursor = cursor
        self.autocommit = False
        self.committed = False
        self.rolled_back = False

    def cursor(self):
        return self._cursor

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


def install(monkeypatch, cursor):
    connection = Connection(cursor)

    @contextmanager
    def fake_db_conn(**_kwargs):
        yield connection

    monkeypatch.setattr(repository, 'db_conn', fake_db_conn)
    return connection


def test_create_reuses_exact_active_kind_after_unique_conflict(monkeypatch):
    cursor = Cursor(rows=[(OPERATION_ID,)], rowcount=0)
    connection = install(monkeypatch, cursor)
    operation_id, created = repository.create_operation(
        tenant_id='tenant-a', user_id=USER_ID, kind='export',
        request_ciphertext='encrypted',
    )
    assert operation_id == OPERATION_ID
    assert created is False
    assert connection.committed is True
    assert connection.autocommit is False
    assert 'ON CONFLICT (tenant_id, user_id, kind)' in cursor.calls[0][0]
    assert cursor.calls[1][1] == ('tenant-a', str(USER_ID), 'export')


def test_claim_is_atomic_and_replay_safe(monkeypatch):
    row = (OPERATION_ID, 'tenant-a', USER_ID, 'export', 'encrypted')
    cursor = Cursor(rows=[row])
    connection = install(monkeypatch, cursor)
    operation = repository.claim_operation(operation_id=OPERATION_ID)
    assert operation['id'] == OPERATION_ID
    assert operation['tenant_id'] == 'tenant-a'
    assert connection.committed is True
    assert "status='queued'" in cursor.calls[0][0]
    assert 'retention_until > NOW()' in cursor.calls[0][0]

    empty_cursor = Cursor()
    empty_connection = install(monkeypatch, empty_cursor)
    assert repository.claim_operation(operation_id=OPERATION_ID) is None
    assert empty_connection.rolled_back is True


def test_completion_requires_running_state_and_retention_wipes_all_sensitive_material(monkeypatch):
    complete_cursor = Cursor(rowcount=1)
    install(monkeypatch, complete_cursor)
    repository.complete_operation(
        operation_id=OPERATION_ID, result_ciphertext='encrypted-result', digest='a' * 64
    )
    assert "status='completed'" in complete_cursor.calls[0][0]
    assert "status='running'" in complete_cursor.calls[0][0]

    retention_cursor = Cursor(rowcount=3)
    install(monkeypatch, retention_cursor)
    assert repository.expire_results() == 3
    query = retention_cursor.calls[0][0]
    assert "request_ciphertext=''" in query
    assert "result_ciphertext=''" in query
    assert "receipt_digest=''" in query
    assert "status='expired'" in query


def test_owner_and_admin_lists_always_bind_tenant_and_are_bounded(monkeypatch):
    now = datetime.now(timezone.utc)
    owner_cursor = Cursor(rows=[(OPERATION_ID, 'export', 'queued', '', now, None, now)])
    install(monkeypatch, owner_cursor)
    owner = repository.list_owned_operations(tenant_id='tenant-a', user_id=USER_ID, limit=999)
    assert owner[0]['id'] == OPERATION_ID
    assert owner_cursor.calls[0][1] == ('tenant-a', str(USER_ID), 100)

    admin_cursor = Cursor(
        rows=[(OPERATION_ID, USER_ID, 'export', 'queued', '', now, None, now)]
    )
    install(monkeypatch, admin_cursor)
    admin = repository.list_tenant_operations(tenant_id='tenant-b', limit=999)
    assert admin[0]['user_id'] == USER_ID
    assert admin_cursor.calls[0][1] == ('tenant-b', 200)
