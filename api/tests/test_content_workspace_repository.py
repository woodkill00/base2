from __future__ import annotations

import hashlib
from contextlib import contextmanager
from datetime import UTC, datetime
from uuid import UUID

import pytest

from api.repositories import content_workspace as repository
from api.security.content_workspace import CursorCodec
from api.services.content_workspace_storage import StoredArtifact


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


def test_asset_content_completion_binds_grant_hash_owner_and_quarantine(monkeypatch):
    monkeypatch.setattr(repository.settings, 'TOKEN_PEPPER', 'synthetic-test-pepper-104')
    asset_id = UUID(int=7104)
    content = (
        b'\x89PNG\r\n\x1a\n'
        + (13).to_bytes(4, 'big')
        + b'IHDR'
        + (1).to_bytes(4, 'big')
        + (1).to_bytes(4, 'big')
        + b'\x08\x06\x00\x00\x00\x00\x00\x00\x00fixture'
    )
    digest = hashlib.sha256(content).hexdigest()
    scope = {
        'site': 'site-a',
        'owner': 'user:test',
        'asset': str(asset_id),
        'sha256': digest,
        'bytes': len(content),
        'purpose': 'asset-upload',
    }
    grant = CursorCodec('synthetic-test-pepper-104', ttl_seconds=300).encode(
        scope=scope, position={'assetId': str(asset_id)}
    )
    cursor = Cursor(
        rows=[
            (asset_id, 'safe.png', 'image/png', len(content), digest, 'pending'),
            (asset_id,),
        ]
    )
    connection = Connection(cursor)
    scopes = bind(monkeypatch, connection)

    class Store:
        def put(self, **kwargs):
            assert kwargs == {
                'namespace': 'media',
                'site_id': 'site-a',
                'object_id': str(asset_id),
                'content': content,
            }
            return StoredArtifact(
                object_key=f'media/site-a/{asset_id}.bin',
                sha256=digest,
                byte_size=len(content),
            )

    result = repository.PostgresContentWorkspaceRepository().complete_asset_upload(
        site_id='site-a',
        asset_id=asset_id,
        owner_ref='user:test',
        upload_grant=grant,
        content=content,
        artifact_store=Store(),
    )
    assert result == {
        'id': str(asset_id),
        'status': 'quarantined',
        'sha256': digest,
        'replayed': False,
    }
    assert scopes == ['site-a'] and connection.commits == 1
    combined_sql = ' '.join(sql for sql, _ in cursor.calls)
    assert 'FOR UPDATE' in combined_sql
    assert "status='quarantined'" in combined_sql
    assert 'sitecontent_workspaceauditevent' in combined_sql


def test_validated_asset_download_is_grant_tenant_requester_and_derivative_bound(monkeypatch):
    monkeypatch.setattr(repository.settings, 'TOKEN_PEPPER', 'synthetic-test-pepper-104')
    asset_id = UUID(int=7104)
    digest = 'b' * 64
    scope = {
        'site': 'site-a',
        'requester': 'user:test',
        'asset': str(asset_id),
        'sha256': digest,
        'mediaType': 'image/png',
        'purpose': 'asset-download',
    }
    grant = CursorCodec('synthetic-test-pepper-104', ttl_seconds=60).encode(
        scope=scope, position={'assetId': str(asset_id)}
    )
    cursor = Cursor(rows=[('variants/site-a/safe.bin', digest, 'image/png')])
    connection = Connection(cursor)
    scopes = bind(monkeypatch, connection)

    class Store:
        def get(self, key, *, expected_sha256):
            assert key == 'variants/site-a/safe.bin'
            assert expected_sha256 == digest
            return b'safe-png'

    result = repository.PostgresContentWorkspaceRepository().read_asset_content(
        site_id='site-a',
        asset_id=asset_id,
        requester_ref='user:test',
        download_grant=grant,
        artifact_store=Store(),
    )
    assert result == {'content': b'safe-png', 'sha256': digest, 'media_type': 'image/png'}
    assert scopes == ['site-a'] and connection.commits == 1
    statements = ' '.join(sql for sql, _ in cursor.calls)
    assert "asset.status='validated'" in statements
    assert "variant.name='safe'" in statements
    assert 'sitecontent_workspaceauditevent' in statements

    rejected_cursor = Cursor(rows=[('variants/site-a/safe.bin', digest, 'image/png')])
    rejected_connection = Connection(rejected_cursor)
    bind(monkeypatch, rejected_connection)
    with pytest.raises(ValueError, match='content_download_grant_invalid'):
        repository.PostgresContentWorkspaceRepository().read_asset_content(
            site_id='site-a',
            asset_id=asset_id,
            requester_ref='user:different',
            download_grant=grant,
            artifact_store=Store(),
        )
    assert rejected_connection.rollbacks == 1


def test_asset_metadata_exposes_a_short_grant_only_for_validated_safe_variant(monkeypatch):
    monkeypatch.setattr(repository.settings, 'TOKEN_PEPPER', 'synthetic-test-pepper-104')
    asset_id = UUID(int=7104)
    now = datetime.now(UTC)
    validated = Cursor(
        rows=[
            (
                asset_id,
                'original.png',
                'image/png',
                10,
                'a' * 64,
                'validated',
                '',
                {'scanStatus': 'clean'},
                now,
                'b' * 64,
                'image/png',
            )
        ]
    )
    bind(monkeypatch, Connection(validated))
    result = repository.PostgresContentWorkspaceRepository().get_asset(
        site_id='site-a', asset_id=asset_id, requester_ref='user:test'
    )
    assert result['expiresIn'] == 60 and result['downloadGrant']

    quarantined = Cursor(
        rows=[
            (
                asset_id,
                'original.png',
                'image/png',
                10,
                'a' * 64,
                'quarantined',
                '',
                {},
                now,
                None,
                None,
            )
        ]
    )
    bind(monkeypatch, Connection(quarantined))
    result = repository.PostgresContentWorkspaceRepository().get_asset(
        site_id='site-a', asset_id=asset_id, requester_ref='user:test'
    )
    assert 'downloadGrant' not in result


def test_export_content_read_is_expiry_requester_grant_and_digest_bound(monkeypatch):
    monkeypatch.setattr(repository.settings, 'TOKEN_PEPPER', 'synthetic-test-pepper-104')
    job_id = UUID(int=6104)
    digest = 'c' * 64
    scope = {
        'site': 'site-a',
        'type': 'article',
        'requester': 'user:test',
        'job': str(job_id),
        'sha256': digest,
        'format': 'json',
        'purpose': 'export-download',
    }
    grant = CursorCodec('synthetic-test-pepper-104', ttl_seconds=60).encode(
        scope=scope, position={'jobId': str(job_id)}
    )
    cursor = Cursor(rows=[(digest, 'json', f'exports/site-a/{job_id}.bin')])
    connection = Connection(cursor)
    scopes = bind(monkeypatch, connection)

    class Store:
        def get(self, key, *, expected_sha256):
            assert key == f'exports/site-a/{job_id}.bin' and expected_sha256 == digest
            return b'[{"title":"Synthetic"}]'

    result = repository.PostgresContentWorkspaceRepository().read_export_content(
        site_id='site-a',
        type_key='article',
        job_id=job_id,
        requester_ref='user:test',
        download_grant=grant,
        artifact_store=Store(),
    )
    assert result['content'] == b'[{"title":"Synthetic"}]'
    assert result['format'] == 'json' and result['sha256'] == digest
    assert scopes == ['site-a'] and connection.commits == 1
    statements = ' '.join(sql for sql, _ in cursor.calls)
    assert "j.status='completed'" in statements and 'j.expires_at>NOW()' in statements
    assert 'sitecontent_workspaceauditevent' in statements


def test_import_review_can_skip_invalid_rows_only_under_explicit_partial_policy(monkeypatch):
    job_id = UUID(int=5104)

    class ReviewCursor(Cursor):
        def __init__(self):
            super().__init__()
            self.statement = ''

        def execute(self, sql, params=()):
            super().execute(sql, params)
            self.statement = ' '.join(sql.split())

        def fetchone(self):
            if 'SELECT j.atomic_policy' in self.statement:
                return ('valid_rows', {'valid': 0, 'invalid': 1})
            if self.statement.startswith('UPDATE sitecontent_importrowoutcome'):
                return (UUID(int=5204),)
            if self.statement.startswith('UPDATE sitecontent_importjob'):
                return (job_id,)
            return None

        def fetchall(self):
            if 'proposed_action IN' in self.statement:
                return [(1, 'reject', None, [])]
            if 'GROUP BY proposed_action' in self.statement:
                return [('skip', 1)]
            return []

    cursor = ReviewCursor()
    connection = Connection(cursor)
    scopes = bind(monkeypatch, connection)
    result = repository.PostgresContentWorkspaceRepository().resolve_import_review(
        site_id='site-a',
        type_key='article',
        job_id=job_id,
        requester_ref='user:test',
        decisions=[{'ordinal': 1, 'action': 'skip', 'match_id': None}],
    )
    assert result['status'] == 'validated'
    assert result['counters']['skipped'] == 1
    assert scopes == ['site-a'] and connection.commits == 1
    assert 'sitecontent_workspaceauditevent' in ' '.join(sql for sql, _ in cursor.calls)


def test_import_row_listing_is_requester_bound_bounded_and_stably_paginated(monkeypatch):
    job_id = UUID(int=5104)

    class RowCursor(Cursor):
        def __init__(self):
            super().__init__()
            self.statement = ''

        def execute(self, sql, params=()):
            super().execute(sql, params)
            self.statement = ' '.join(sql.split())

        def fetchone(self):
            if 'SELECT j.status' in self.statement:
                return ('review_required',)
            return None

        def fetchall(self):
            if 'SELECT ordinal, proposed_action' in self.statement:
                return [
                    (1, 'review', [], None, [UUID(int=3104)], None, None),
                    (2, 'skip', [], None, [], None, None),
                ]
            return []

    cursor = RowCursor()
    scopes = bind(monkeypatch, Connection(cursor))
    result = repository.PostgresContentWorkspaceRepository().list_import_rows(
        site_id='site-a',
        type_key='article',
        job_id=job_id,
        requester_ref='user:test',
        after_ordinal=0,
        limit=1,
    )
    assert result['status'] == 'review_required'
    assert result['items'][0]['candidateIds'] == [str(UUID(int=3104))]
    assert result['nextOrdinal'] == 1
    assert scopes == ['site-a']
    assert cursor.calls[0][1][-1] == 'user:test'
    assert 'ORDER BY ordinal LIMIT %s' in cursor.calls[1][0]
    assert cursor.calls[1][1][-1] == 2

    with pytest.raises(ValueError, match='content_limit_exceeded'):
        repository.PostgresContentWorkspaceRepository().list_import_rows(
            site_id='site-a',
            type_key='article',
            job_id=job_id,
            requester_ref='user:test',
            after_ordinal=0,
            limit=201,
        )


def test_import_source_completion_validates_parses_encrypts_and_marks_ready(monkeypatch):
    monkeypatch.setattr(repository.settings, 'TOKEN_PEPPER', 'synthetic-test-pepper-104')
    job_id = UUID(int=5104)
    content = b'[{"title":"Synthetic"}]'
    digest = hashlib.sha256(content).hexdigest()
    scope = {
        'site': 'site-a',
        'type': 'article',
        'requester': 'user:test',
        'job': str(job_id),
        'sha256': digest,
        'format': 'json',
        'purpose': 'import-source-upload',
    }
    grant = CursorCodec('synthetic-test-pepper-104', ttl_seconds=300).encode(
        scope=scope, position={'jobId': str(job_id)}
    )
    cursor = Cursor(rows=[(job_id, digest, 'json', '', 'uploaded'), (job_id,)])
    connection = Connection(cursor)
    scopes = bind(monkeypatch, connection)

    class Store:
        def put(self, **kwargs):
            assert kwargs['namespace'] == 'imports'
            assert kwargs['site_id'] == 'site-a'
            assert kwargs['content'] == content
            return StoredArtifact(
                object_key=f'imports/site-a/{job_id}.bin',
                sha256=digest,
                byte_size=len(content),
            )

    result = repository.PostgresContentWorkspaceRepository().complete_import_source(
        site_id='site-a',
        type_key='article',
        job_id=job_id,
        requester_ref='user:test',
        upload_grant=grant,
        content=content,
        artifact_store=Store(),
    )
    assert result['sourceReady'] is True and result['replayed'] is False
    assert scopes == ['site-a'] and connection.commits == 1
    sql = ' '.join(statement for statement, _ in cursor.calls)
    assert 'source_object_key' in sql and 'FOR UPDATE' in sql
    assert 'sitecontent_workspaceauditevent' in sql


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


def test_query_compiler_uses_typed_parameterized_comparisons():
    allowed = {
        'count': 'integer',
        'available': 'boolean',
        'published_on': 'date',
    }
    sql, params = repository.compile_filters(
        [
            {'field': 'count', 'operator': 'gte', 'value': 10},
            {'field': 'available', 'operator': 'eq', 'value': True},
            {'field': 'published_on', 'operator': 'lt', 'value': '2026-09-03'},
        ],
        allowed,
    )
    assert '(values ->> %s)::numeric >= %s' in sql
    assert '(values ->> %s)::boolean = %s' in sql
    assert '(values ->> %s)::date < %s' in sql
    assert params == ['count', '10', 'available', 'true', 'published_on', '2026-09-03']


def test_search_is_tenant_type_cursor_and_staleness_bound(monkeypatch):
    monkeypatch.setattr(repository.settings, 'TOKEN_PEPPER', 'synthetic-test-pepper-104')
    now = datetime.now(UTC)

    class SearchCursor(Cursor):
        def __init__(self):
            super().__init__()
            self.statement = ''

        def execute(self, sql, params=()):
            super().execute(sql, params)
            self.statement = ' '.join(sql.split())

        def fetchall(self):
            if 'FROM sitecontent_searchdocument d' in self.statement:
                return [
                    (
                        UUID(int=9104),
                        UUID(int=3104),
                        'Safe guide',
                        'Synthetic excerpt',
                        '/article/safe-guide',
                        'public',
                        now,
                        now,
                        False,
                    )
                ]
            return []

        def fetchone(self):
            if 'SELECT EXISTS' in self.statement:
                return (True,)
            return None

    cursor = SearchCursor()
    scopes = bind(monkeypatch, Connection(cursor))
    result = repository.PostgresContentWorkspaceRepository().search_records(
        site_id='site-a', type_key='article', term='100%_safe', limit=25, cursor=None
    )
    assert result['items'][0]['id'] == str(UUID(int=3104))
    assert result['indexState'] == 'stale'
    assert scopes == ['site-a']
    sql, params = cursor.calls[0]
    assert 'c.site_id=%s' in sql and 'c.content_type=%s' in sql
    assert "ILIKE %s ESCAPE '\\'" in sql
    assert params[3] == r'%100\%\_safe%'
    assert '100%_safe' not in sql


def test_saved_view_executes_the_exact_bounded_query(monkeypatch):
    repo = repository.PostgresContentWorkspaceRepository()
    query = {
        'filters': [{'field': 'title', 'operator': 'contains', 'value': 'safe'}],
        'sort': ['slug'],
        'fields': ['title'],
        'expand': [],
        'limit': 10,
    }
    monkeypatch.setattr(
        repo,
        'get_view',
        lambda **_: {'query': query, 'schemaVersion': 2, 'currentSchemaVersion': 2},
    )
    calls = []

    def list_records(**kwargs):
        calls.append(kwargs)
        return {'items': [], 'nextCursor': None}

    monkeypatch.setattr(repo, 'list_records', list_records)
    result = repo.execute_view(
        site_id='site-a',
        type_key='article',
        view_id=UUID(int=104),
        owner_ref='user:test',
        caller_role='editor',
    )
    assert result == {'items': [], 'nextCursor': None}
    assert calls == [
        {
            'site_id': 'site-a',
            'type_key': 'article',
            'limit': 10,
            'cursor': None,
            'query': query,
        }
    ]


def test_saved_view_execution_fails_closed_after_schema_change(monkeypatch):
    repo = repository.PostgresContentWorkspaceRepository()
    monkeypatch.setattr(
        repo,
        'get_view',
        lambda **_: {
            'query': {'filters': [], 'sort': ['slug'], 'fields': [], 'expand': [], 'limit': 25},
            'schemaVersion': 1,
            'currentSchemaVersion': 2,
        },
    )
    monkeypatch.setattr(
        repo,
        'list_records',
        lambda **_: (_ for _ in ()).throw(AssertionError('stale view executed')),
    )
    with pytest.raises(ValueError, match='saved_view_schema_stale'):
        repo.execute_view(
            site_id='site-a',
            type_key='article',
            view_id=UUID(int=104),
            owner_ref='user:test',
            caller_role='editor',
        )


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


def test_record_value_mirror_enforces_formats_bounds_and_finite_decimals():
    fields = [
        ('slug', 'slug', True, False, None, {}),
        ('price', 'decimal', False, False, None, {'minimum': 1, 'maximum': 100}),
        ('published_at', 'datetime', False, False, None, {}),
        ('kind', 'enum', False, False, None, {'choices': ['news', 'guide']}),
        ('related', 'references', False, False, None, {'maximumItems': 2}),
    ]
    repository._validate_values(
        {
            'slug': 'safe-slug',
            'price': '4.50',
            'published_at': '2026-09-02T12:00:00Z',
            'kind': 'guide',
            'related': [str(UUID(int=1)), str(UUID(int=2))],
        },
        fields,
    )
    invalid_values = [
        {'slug': 'Unsafe Slug'},
        {'slug': 'safe', 'price': 'NaN'},
        {'slug': 'safe', 'price': '101'},
        {'slug': 'safe', 'published_at': '2026-09-02T12:00:00'},
        {'slug': 'safe', 'kind': 'unknown'},
        {'slug': 'safe', 'related': [str(UUID(int=1))] * 3},
    ]
    for values in invalid_values:
        try:
            repository._validate_values(values, fields)
        except ValueError as exc:
            assert str(exc) == 'content_schema_invalid'
        else:
            raise AssertionError(f'invalid value mirror was accepted: {values!r}')


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
