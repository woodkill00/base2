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
    monkeypatch.setattr(repository.settings, 'TOKEN_PEPPER', 'synthetic-test-pepper-104')
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


def test_definition_cursor_is_opaque_and_bound_to_page_scope(monkeypatch):
    monkeypatch.setattr(repository.settings, 'TOKEN_PEPPER', 'synthetic-test-pepper-104')
    rows = [
        (UUID(int=1), 'site-a', 'article', 1, 'Article', '', 'draft', 1),
        (UUID(int=2), 'site-a', 'catalog', 1, 'Catalog', '', 'draft', 1),
    ]
    first_cursor = Cursor(rows=rows)
    bind(monkeypatch, Connection(first_cursor))
    first = repository.PostgresContentWorkspaceRepository().list_definitions(
        site_id='site-a', limit=1, cursor=None
    )
    assert first['nextCursor'] and 'site-a' not in first['nextCursor']
    second_cursor = Cursor()
    bind(monkeypatch, Connection(second_cursor))
    repository.PostgresContentWorkspaceRepository().list_definitions(
        site_id='site-a', limit=1, cursor=first['nextCursor']
    )
    assert second_cursor.calls[0][1][:4] == ('site-a', 'article', 1, str(UUID(int=1)))
    try:
        repository.PostgresContentWorkspaceRepository().list_definitions(
            site_id='site-a', limit=2, cursor=first['nextCursor']
        )
    except ValueError as exc:
        assert str(exc) == 'content_query_invalid'
    else:
        raise AssertionError('cursor replayed under a different page bound')


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
    statements = ' '.join(sql for sql, _ in cursor.calls)
    assert 'sitecontent_workflowdefinition' in statements
    assert 'sitecontent_workspaceauditevent' in statements


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


def test_record_value_mirror_rejects_unknown_required_and_wrong_types():
    fields = [
        ('title', 'short_text', True, False, None, {}),
        ('count', 'integer', False, False, None, {}),
    ]
    repository._validate_values({'title': 'Safe', 'count': 2}, fields)
    for values in ({}, {'title': 'Safe', 'unknown': 1}, {'title': 'Safe', 'count': True}):
        try:
            repository._validate_values(values, fields)
        except ValueError as exc:
            assert str(exc) == 'content_schema_invalid'
        else:
            raise AssertionError('invalid record values were accepted')


def test_structured_rich_text_mirror_rejects_script_nodes_and_unsafe_links():
    fields = [('body', 'rich_text', True, False, None, {})]
    repository._validate_values(
        {'body': {'type': 'document', 'children': [{'type': 'text', 'text': 'Safe'}]}}, fields
    )
    for body in (
        {'type': 'script', 'text': 'bad'},
        {'type': 'link', 'href': 'javascript:alert(1)', 'children': []},
        {'type': 'document', 'onclick': 'bad', 'children': []},
    ):
        try:
            repository._validate_values({'body': body}, fields)
        except ValueError as exc:
            assert str(exc) == 'content_schema_invalid'
        else:
            raise AssertionError('unsafe structured content was accepted')
