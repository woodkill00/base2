from __future__ import annotations

from contextlib import contextmanager
from uuid import UUID

from api.repositories import content_workspace as repository


class Cursor:
    def __init__(self, rows=()):
        self.rows = list(rows)
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, params=()):
        self.calls.append((' '.join(sql.split()), params))

    def fetchone(self):
        return self.rows.pop(0) if self.rows else None

    def fetchall(self):
        return list(self.rows)


class Connection:
    def __init__(self, cursor):
        self.value = cursor
        self.commits = 0
        self.rollbacks = 0

    def cursor(self):
        return self.value

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


def bind(monkeypatch, connection):
    calls = []

    @contextmanager
    def fake_db_conn(*, tenant_id):
        calls.append(tenant_id)
        yield connection

    monkeypatch.setattr(repository, 'db_conn', fake_db_conn)
    return calls


def test_definition_listing_binds_tenant_and_uses_stable_cursor(monkeypatch):
    cursor = Cursor()
    scopes = bind(monkeypatch, Connection(cursor))
    result = repository.PostgresContentWorkspaceRepository().list_definitions(
        site_id='site-a', limit=25, cursor=None
    )
    assert scopes == ['site-a']
    sql, params = cursor.calls[0]
    assert 'WHERE site_id=%s' in sql
    assert 'ORDER BY type_key, version, id' in sql
    assert params == ('site-a', 26)
    assert result == {'items': [], 'nextCursor': None}


def test_create_definition_is_one_transaction_and_never_accepts_site_from_payload(monkeypatch):
    definition_id = UUID('00000000-0000-0000-0000-000000002104')
    cursor = Cursor(rows=[(definition_id, 1, 'draft', 1)])
    connection = Connection(cursor)
    scopes = bind(monkeypatch, connection)
    result = repository.PostgresContentWorkspaceRepository().create_definition(
        site_id='site-a',
        actor_ref='user:test',
        payload={
            'type_key': 'article',
            'name': 'Article',
            'description': '',
            'preset_id': 'custom',
            'fields': [],
        },
    )
    assert scopes == ['site-a']
    assert connection.commits == 1
    assert result['siteId'] == 'site-a'
    assert all('site-b' not in str(call) for call in cursor.calls)


def test_query_compiler_rejects_unknown_fields_operators_and_excess_complexity():
    allowed = {'title': 'short_text', 'published_at': 'datetime'}
    sql, params = repository.compile_filters(
        [{'field': 'title', 'operator': 'contains', 'value': 'safe'}], allowed
    )
    assert 'values ->> %s ILIKE %s' in sql
    assert params == ['title', '%safe%']

    for filters in (
        [{'field': 'secret', 'operator': 'eq', 'value': 'x'}],
        [{'field': 'title', 'operator': 'sql', 'value': 'x'}],
        [{'field': 'title', 'operator': 'eq', 'value': 'x'}] * 17,
    ):
        try:
            repository.compile_filters(filters, allowed)
        except ValueError as exc:
            assert str(exc) == 'content_query_invalid'
        else:
            raise AssertionError('unsafe query was accepted')
