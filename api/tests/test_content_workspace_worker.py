from __future__ import annotations

from contextlib import contextmanager
from uuid import UUID
from datetime import UTC, datetime

import pytest

from api.services import content_workspace_worker as worker


class Cursor:
    def __init__(self, rows):
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
        self.cursor_value, self.commits, self.rollbacks = cursor, 0, 0

    def cursor(self):
        return self.cursor_value

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


def bind(monkeypatch, connection):
    scopes = []

    @contextmanager
    def fake_db_conn(*, tenant_id=None):
        scopes.append(tenant_id)
        yield connection

    monkeypatch.setattr(worker, 'db_conn', fake_db_conn)
    return scopes


def test_due_publications_are_ordered_and_bounded(monkeypatch):
    cursor = Cursor([('site-a', UUID(int=104))])
    bind(monkeypatch, Connection(cursor))
    assert worker.due_publication_ids(limit=25) == [('site-a', str(UUID(int=104)))]
    assert 'ORDER BY publish_at, id LIMIT %s' in cursor.calls[0][0]


def test_worker_health_summary_is_bounded_deterministic_and_redacted(monkeypatch):
    rows = [
        ('import', 'failed', 'secret=https://private.example', 2, 12.5),
        ('export', 'completed', '', 3, 4.0),
    ]
    cursor = Cursor(rows)
    scopes = bind(monkeypatch, Connection(cursor))
    result = worker.workspace_health_summary(site_id='site-a')
    assert scopes == ['site-a']
    assert result['schemaVersion'] == 1
    assert result['siteRef'] != 'site-a'
    assert result['outcomes'][0] == {
        'kind': 'import',
        'state': 'failed',
        'errorCode': 'content_dependency_unavailable',
        'count': 2,
        'maximumDurationSeconds': 12.5,
    }
    assert len(result['digest']) == 64
    assert 'private.example' not in str(result)
    assert cursor.calls[0][1] == ('site-a', 'site-a')


def test_publication_is_tenant_bound_transactional_and_replay_safe(monkeypatch):
    record_id = UUID(int=104)
    cursor = Cursor([(record_id, 3, 1, {'title': 'Safe'}, 'scheduled', 'future'), (True,)])
    connection = Connection(cursor)
    scopes = bind(monkeypatch, connection)
    assert worker.publish_scheduled_record(site_id='site-a', record_id=record_id) == 'published'
    assert scopes == ['site-a'] and connection.commits == 1
    sql = ' '.join(statement for statement, _ in cursor.calls)
    assert 'FOR UPDATE' in sql and 'sitecontent_contentrevision' in sql
    assert 'sitecontent_workspaceauditevent' in sql

    replay_cursor = Cursor([(record_id, 4, 1, {}, 'published', None)])
    replay = Connection(replay_cursor)
    bind(monkeypatch, replay)
    assert (
        worker.publish_scheduled_record(site_id='site-a', record_id=record_id)
        == 'already_published'
    )
    assert all('UPDATE sitecontent_contentrecord' not in call[0] for call in replay_cursor.calls)


def test_due_index_records_are_restart_discoverable_ordered_and_bounded(monkeypatch):
    record_id = UUID(int=105)
    cursor = Cursor([('site-a', record_id, 7)])
    bind(monkeypatch, Connection(cursor))

    assert worker.due_index_records(limit=25) == [('site-a', str(record_id), 7)]
    sql = cursor.calls[0][0]
    assert 'LEFT JOIN sitecontent_searchdocument' in sql
    assert 'ORDER BY c.updated_at, c.id LIMIT %s' in sql
    with pytest.raises(ValueError, match='content_limit_exceeded'):
        worker.due_index_records(limit=0)


def test_search_projection_is_closed_and_never_indexes_private_values():
    updated_at = datetime(2026, 9, 2, tzinfo=UTC)
    projection = worker.build_search_projection(
        content_type='article',
        slug='safe-title',
        title='Safe title',
        body='Public body',
        state='published',
        search_visible=True,
        updated_at=updated_at,
        deleted_at=None,
    )
    assert projection == {
        'title': 'Safe title',
        'body': 'Public body',
        'url_path': '/article/safe-title',
        'visibility': 'public',
        'source_updated_at': updated_at,
        'tombstoned': False,
    }
    assert 'values' not in projection

    private = worker.build_search_projection(
        content_type='article',
        slug='draft',
        title='Draft',
        body='Private',
        state='draft',
        search_visible=True,
        updated_at=updated_at,
        deleted_at=None,
    )
    assert private['visibility'] == 'private'
    assert private['tombstoned'] is False


def test_index_worker_is_tenant_bound_replay_safe_and_rejects_future_job(monkeypatch):
    record_id = UUID(int=106)
    updated_at = datetime(2026, 9, 2, tzinfo=UTC)
    row = (
        record_id,
        'article',
        'safe-title',
        'Safe title',
        'Public body',
        'published',
        True,
        updated_at,
        None,
        7,
    )
    cursor = Cursor([row, None])
    connection = Connection(cursor)
    scopes = bind(monkeypatch, connection)

    assert worker.index_workspace_record(site_id='site-a', record_id=record_id, job_version=7) == (
        'indexed'
    )
    assert scopes == ['site-a'] and connection.commits == 1
    sql = ' '.join(statement for statement, _ in cursor.calls)
    assert 'FOR UPDATE' in sql
    assert 'ON CONFLICT (content_id)' in sql
    assert 'sitecontent_workspaceauditevent' in sql

    stale_cursor = Cursor([row])
    stale_connection = Connection(stale_cursor)
    bind(monkeypatch, stale_connection)
    assert (
        worker.index_workspace_record(site_id='site-a', record_id=record_id, job_version=6)
        == 'stale_job'
    )
    assert stale_connection.commits == 0

    future_cursor = Cursor([row])
    future_connection = Connection(future_cursor)
    bind(monkeypatch, future_connection)
    with pytest.raises(ValueError, match='content_index_version_invalid'):
        worker.index_workspace_record(site_id='site-a', record_id=record_id, job_version=8)
    assert future_connection.rollbacks == 1


def test_due_media_scans_only_discovers_unresolved_quarantine(monkeypatch):
    asset_id = UUID(int=7104)
    cursor = Cursor([('site-a', asset_id)])
    bind(monkeypatch, Connection(cursor))
    assert worker.due_media_scans(limit=10) == [('site-a', str(asset_id))]
    sql = cursor.calls[0][0]
    assert "status='quarantined'" in sql
    assert "metadata->>'admission'='content_verified'" in sql
    assert "NOT IN ('clean','infected')" in sql


@pytest.mark.parametrize(
    ('verdict', 'expected_status', 'expected_result'),
    [
        ('clean', 'validated', 'validated_safe_derivative'),
        ('infected', 'rejected', 'scanned_infected'),
    ],
)
def test_media_scanner_is_content_bound_and_promotes_only_a_safe_derivative(
    monkeypatch, verdict, expected_status, expected_result
):
    asset_id = UUID(int=7104)
    cursor = Cursor(
        [
            (
                f'media/site-a/{asset_id}.bin',
                'a' * 64,
                'quarantined',
                {'admission': 'content_verified', 'width': 20, 'height': 10},
                'image/png',
            )
        ]
    )
    connection = Connection(cursor)
    scopes = bind(monkeypatch, connection)

    class Store:
        puts = []

        def get(self, key, *, expected_sha256):
            assert key.endswith(f'{asset_id}.bin') and expected_sha256 == 'a' * 64
            return b'synthetic'

        def put(self, **kwargs):
            self.puts.append(kwargs)
            return type(
                'Stored',
                (),
                {
                    'object_key': 'variants/site-a/safe.bin',
                    'sha256': 'b' * 64,
                    'byte_size': 4,
                },
            )()

    derivative = type(
        'Derivative',
        (),
        {
            'content': b'safe',
            'media_type': 'image/png',
            'sha256': 'b' * 64,
            'width': 20,
            'height': 10,
        },
    )()
    store = Store()

    assert (
        worker.scan_workspace_asset(
            site_id='site-a',
            asset_id=asset_id,
            artifact_store=store,
            scanner=lambda content: verdict if content == b'synthetic' else 'error',
            derivative_builder=lambda **_kwargs: derivative,
        )
        == expected_result
    )
    assert scopes == ['site-a'] and connection.commits == 1
    update = next(call for call in cursor.calls if call[0].startswith('UPDATE'))
    assert update[1][0] == expected_status
    if verdict == 'clean':
        assert store.puts[0]['namespace'] == 'variants'
        assert any('INSERT INTO sitecontent_mediavariant' in call[0] for call in cursor.calls)
    else:
        assert store.puts == []


def test_media_scanner_failure_rolls_back_without_false_clean_state(monkeypatch):
    asset_id = UUID(int=7104)
    cursor = Cursor(
        [
            (
                f'media/site-a/{asset_id}.bin',
                'a' * 64,
                'quarantined',
                {'admission': 'content_verified'},
                'image/png',
            )
        ]
    )
    connection = Connection(cursor)
    bind(monkeypatch, connection)

    class Store:
        def get(self, *_args, **_kwargs):
            return b'synthetic'

    with pytest.raises(RuntimeError, match='scanner unavailable'):
        worker.scan_workspace_asset(
            site_id='site-a',
            asset_id=asset_id,
            artifact_store=Store(),
            scanner=lambda _content: (_ for _ in ()).throw(RuntimeError('scanner unavailable')),
        )
    assert connection.rollbacks == 1 and connection.commits == 0
    assert all(not call[0].startswith('UPDATE') for call in cursor.calls)


def test_due_exports_are_restart_discoverable_ordered_and_bounded(monkeypatch):
    job_id = UUID(int=6104)
    cursor = Cursor([('site-a', job_id)])
    bind(monkeypatch, Connection(cursor))
    assert worker.due_export_jobs(limit=10) == [('site-a', str(job_id))]
    assert "status='queued'" in cursor.calls[0][0]
    assert 'expires_at>NOW()' in cursor.calls[0][0]
    assert 'ORDER BY created_at, id LIMIT %s' in cursor.calls[0][0]


def test_export_payload_is_deterministic_and_csv_formulas_are_neutralized():
    rows = [{'title': '=cmd', 'nested': {'safe': True}, 'ignored': 'private'}]
    first = worker._export_payload(rows, ['title', 'nested'], 'json')
    second = worker._export_payload(rows, ['title', 'nested'], 'json')
    assert first == second == b'[{"nested":{"safe":true},"title":"=cmd"}]'
    csv_output = worker._export_payload(rows, ['title', 'nested'], 'csv').decode()
    assert "'=cmd" in csv_output
    assert 'ignored' not in csv_output
    with pytest.raises(ValueError, match='content_schema_invalid'):
        worker._export_payload(rows, ['title'], 'xml')


def test_export_worker_binds_projection_stores_encrypted_artifact_and_completes(monkeypatch):
    job_id = UUID(int=6104)
    fields = ['title', 'count']
    projection = worker.canonical_digest(
        {
            'site': 'site-a',
            'type': 'article',
            'schema': 3,
            'requester': 'user:test',
            'fields': fields,
        }
    )

    class ExportCursor(Cursor):
        def __init__(self):
            super().__init__([])
            self.statement = ''

        def execute(self, sql, params=()):
            super().execute(sql, params)
            self.statement = ' '.join(sql.split())

        def fetchone(self):
            if 'SELECT j.status' in self.statement:
                return ('queued', 3, 'json', projection, fields, 'user:test', 'article', '', '')
            if 'UPDATE sitecontent_exportjob' in self.statement:
                return (job_id,)
            return None

        def fetchall(self):
            if 'SELECT values FROM sitecontent_contentrecord' in self.statement:
                return [({'title': 'Synthetic', 'count': 2, 'private': 'omitted'},)]
            return []

    cursor = ExportCursor()
    connection = Connection(cursor)
    scopes = bind(monkeypatch, connection)

    class Store:
        def put(self, **kwargs):
            assert kwargs['namespace'] == 'exports' and kwargs['site_id'] == 'site-a'
            assert kwargs['content'] == b'[{"count":2,"title":"Synthetic"}]'
            return type(
                'Stored',
                (),
                {
                    'object_key': f'exports/site-a/{job_id}.bin',
                    'sha256': 'c' * 64,
                    'byte_size': len(kwargs['content']),
                },
            )()

    assert (
        worker.process_export_job(site_id='site-a', job_id=job_id, artifact_store=Store())
        == 'completed'
    )
    assert scopes == ['site-a'] and connection.commits == 1
    statements = ' '.join(sql for sql, _ in cursor.calls)
    assert 'FOR UPDATE' in statements
    assert 'sitecontent_workspaceauditevent' in statements


def test_export_worker_rejects_tampered_projection_without_output(monkeypatch):
    job_id = UUID(int=6104)
    cursor = Cursor([('queued', 3, 'json', '0' * 64, ['title'], 'user:test', 'article', '', '')])
    connection = Connection(cursor)
    bind(monkeypatch, connection)

    class Store:
        def put(self, **_kwargs):
            raise AssertionError('tampered projection must not be stored')

    with pytest.raises(ValueError, match='content_integrity_failed'):
        worker.process_export_job(site_id='site-a', job_id=job_id, artifact_store=Store())
    assert connection.rollbacks == 1 and connection.commits == 0


def test_export_terminal_failure_is_redacted_and_expiry_is_bounded(monkeypatch):
    job_id = UUID(int=6104)
    failed_cursor = Cursor([(job_id,)])
    failed_connection = Connection(failed_cursor)
    bind(monkeypatch, failed_connection)
    assert worker.mark_export_failed(
        site_id='site-a', job_id=job_id, error_code='secret=https://private.example'
    )
    update = failed_cursor.calls[0]
    assert update[1][0] == 'content_dependency_unavailable'
    assert 'private.example' not in str(failed_cursor.calls)
    assert failed_connection.commits == 1

    expired_cursor = Cursor(
        [
            (UUID(int=6104), 'site-a', 'exports/site-a/00000000-0000-0000-0000-0000000017d8.bin', 'a' * 64),
            (UUID(int=6105), 'site-b', '', ''),
        ]
    )
    expired_connection = Connection(expired_cursor)
    bind(monkeypatch, expired_connection)
    deleted = []

    class Store:
        def delete(self, **kwargs):
            deleted.append(kwargs)
            return True

    assert worker.expire_export_jobs(artifact_store=Store(), limit=100) == 2
    assert 'FOR UPDATE SKIP LOCKED' in expired_cursor.calls[0][0]
    assert expired_cursor.calls[0][1] == (100,)
    assert deleted[0]['site_id'] == 'site-a'
    assert deleted[0]['missing_ok'] is True
    assert expired_connection.commits == 1


def test_retention_cleanup_preserves_relationships_and_audit_and_deletes_exact_objects(monkeypatch):
    asset_id = UUID(int=7104)
    record_id = UUID(int=7105)

    class RetentionCursor(Cursor):
        rowcount = 1

        def __init__(self):
            super().__init__([])
            self.result_sets = [
                [(asset_id, 'site-a', f'media/site-a/{asset_id}.bin', 'a' * 64)],
                [('safe', f'variants/site-a/{asset_id}-safe.bin', 'b' * 64)],
                [(record_id, 'site-a')],
            ]

        def fetchall(self):
            return self.result_sets.pop(0) if self.result_sets else []

    cursor = RetentionCursor()
    connection = Connection(cursor)
    bind(monkeypatch, connection)
    deleted = []

    class Store:
        def delete(self, **kwargs):
            deleted.append(kwargs)
            return True

    assert worker.purge_workspace_retention(
        artifact_store=Store(), recovery_days=30, limit=50
    ) == {'assets': 1, 'records': 1}
    assert [item['namespace'] for item in deleted] == ['variants', 'media']
    statements = ' '.join(sql for sql, _ in cursor.calls)
    assert 'NOT EXISTS ( SELECT 1 FROM sitecontent_contentrelationship' in statements
    assert 'NOT EXISTS ( SELECT 1 FROM sitecontent_assetbinding' in statements
    assert statements.count('sitecontent_workspaceauditevent') == 2
    assert connection.commits == 1 and connection.rollbacks == 0

    replay_cursor = RetentionCursor()
    replay_cursor.result_sets = [[], []]
    replay_connection = Connection(replay_cursor)
    bind(monkeypatch, replay_connection)
    assert worker.purge_workspace_retention(
        artifact_store=Store(), recovery_days=30, limit=50
    ) == {'assets': 0, 'records': 0}
    assert len(deleted) == 2
    assert replay_connection.commits == 1 and replay_connection.rollbacks == 0


def test_import_mapping_rejects_unknown_or_invalid_rows_without_losing_ordinals():
    parsed = worker.ParsedRows(
        (
            {'Slug': 'safe-one', 'Title': 'Safe one'},
            {'Slug': '../unsafe', 'Title': 'Unsafe'},
            {'Slug': 'unknown', 'Title': 'Unknown', 'Secret': 'not-declared'},
        ),
        'a' * 64,
    )
    fields = [('title', 'short_text', True, False, None, {})]
    valid, ordinals, rejected = worker._mapped_import_rows(
        parsed, {'Slug': 'slug', 'Title': 'title'}, fields
    )
    assert valid == [{'slug': 'safe-one', 'title': 'Safe one'}]
    assert ordinals == [1]
    assert [item.ordinal for item in rejected] == [2, 3]
    assert all(item.action == 'reject' for item in rejected)


def test_due_import_validations_require_an_uploaded_private_source(monkeypatch):
    job_id = UUID(int=5104)
    cursor = Cursor([('site-a', job_id)])
    bind(monkeypatch, Connection(cursor))
    assert worker.due_import_validations(limit=10) == [('site-a', str(job_id))]
    assert "status='uploaded'" in cursor.calls[0][0]
    assert "source_object_key<>''" in cursor.calls[0][0]


def test_import_terminal_failure_is_redacted_audited_and_replay_safe(monkeypatch):
    job_id = UUID(int=5104)
    cursor = Cursor([(job_id,)])
    connection = Connection(cursor)
    scopes = bind(monkeypatch, connection)
    assert worker.mark_import_failed(
        site_id='site-a',
        job_id=job_id,
        error_code='provider password=private',
    )
    assert scopes == ['site-a'] and connection.commits == 1
    statements = ' '.join(sql for sql, _ in cursor.calls)
    assert "status IN ('uploaded','validated','committing')" in statements
    assert 'content.import_failed' in statements
    combined_params = repr([params for _, params in cursor.calls])
    assert 'content_dependency_unavailable' in combined_params
    assert 'password=private' not in combined_params

    replay = Connection(Cursor([]))
    bind(monkeypatch, replay)
    assert not worker.mark_import_failed(
        site_id='site-a', job_id=job_id, error_code='content_integrity_failed'
    )
    assert replay.commits == 1


def test_import_validation_stages_outcomes_without_mutating_records(monkeypatch):
    job_id = UUID(int=5104)
    content = b'[{"slug":"safe-one","title":"Safe one"}]'
    digest = worker.hashlib.sha256(content).hexdigest()

    class ImportCursor(Cursor):
        def __init__(self):
            super().__init__([])
            self.statement = ''

        def execute(self, sql, params=()):
            super().execute(sql, params)
            self.statement = ' '.join(sql.split())

        def fetchone(self):
            if 'SELECT j.status' in self.statement:
                return (
                    'uploaded',
                    1,
                    digest,
                    'json',
                    f'imports/site-a/{job_id}.bin',
                    {},
                    'update_exact',
                    'all_or_nothing',
                    'article',
                    UUID(int=2104),
                )
            if 'UPDATE sitecontent_importjob' in self.statement:
                return (job_id,)
            return None

        def fetchall(self):
            if 'SELECT field_key' in self.statement:
                return [('title', 'short_text', True, False, None, {})]
            if 'SELECT id, slug, title, values' in self.statement:
                return []
            return []

    cursor = ImportCursor()
    connection = Connection(cursor)
    scopes = bind(monkeypatch, connection)

    class Store:
        def get(self, key, *, expected_sha256):
            assert key == f'imports/site-a/{job_id}.bin' and expected_sha256 == digest
            return content

    assert (
        worker.validate_import_job(site_id='site-a', job_id=job_id, artifact_store=Store())
        == 'validated'
    )
    assert scopes == ['site-a'] and connection.commits == 1
    statements = ' '.join(sql for sql, _ in cursor.calls)
    assert 'sitecontent_importrowoutcome' in statements
    assert 'sitecontent_workspaceauditevent' in statements
    assert 'INSERT INTO sitecontent_contentrecord' not in statements


def test_import_commit_revalidates_source_and_applies_all_rows_atomically(monkeypatch):
    job_id = UUID(int=5104)
    definition_id = UUID(int=2104)
    content = b'[{"slug":"safe-one","title":"Safe one"}]'
    digest = worker.hashlib.sha256(content).hexdigest()
    row_digest = worker.hashlib.sha256(b'{"slug":"safe-one","title":"Safe one"}').hexdigest()

    class CommitCursor(Cursor):
        def __init__(self):
            super().__init__([])
            self.statement = ''

        def execute(self, sql, params=()):
            super().execute(sql, params)
            self.statement = ' '.join(sql.split())

        def fetchone(self):
            if 'SELECT j.status' in self.statement:
                return (
                    'committing',
                    1,
                    digest,
                    'json',
                    f'imports/site-a/{job_id}.bin',
                    {},
                    'article',
                    definition_id,
                )
            if "UPDATE sitecontent_importjob SET status='completed'" in self.statement:
                return (job_id,)
            return None

        def fetchall(self):
            if 'SELECT field_key' in self.statement:
                return [('title', 'short_text', True, False, None, {})]
            if 'SELECT ordinal, source_row_sha256' in self.statement:
                return [(1, row_digest, 'create', None)]
            return []

    cursor = CommitCursor()
    connection = Connection(cursor)
    scopes = bind(monkeypatch, connection)

    class Store:
        def get(self, key, *, expected_sha256):
            assert key == f'imports/site-a/{job_id}.bin' and expected_sha256 == digest
            return content

    assert (
        worker.process_import_commit(site_id='site-a', job_id=job_id, artifact_store=Store())
        == 'completed'
    )
    assert scopes == ['site-a'] and connection.commits == 1
    statements = ' '.join(sql for sql, _ in cursor.calls)
    assert 'INSERT INTO sitecontent_contentrecord' in statements
    assert "'draft'" in statements
    assert 'sitecontent_importrowoutcome' in statements
    assert 'sitecontent_workspaceauditevent' in statements


def test_due_import_commits_require_committing_state_and_private_source(monkeypatch):
    job_id = UUID(int=5104)
    cursor = Cursor([('site-a', job_id)])
    bind(monkeypatch, Connection(cursor))
    assert worker.due_import_commits(limit=10) == [('site-a', str(job_id))]
    assert "status='committing'" in cursor.calls[0][0]
    assert "source_object_key<>''" in cursor.calls[0][0]


def test_import_commit_rolls_back_if_staged_row_digest_changed(monkeypatch):
    job_id = UUID(int=5104)
    content = b'[{"slug":"safe-one","title":"Safe one"}]'
    digest = worker.hashlib.sha256(content).hexdigest()

    class TamperedCursor(Cursor):
        def __init__(self):
            super().__init__([])
            self.statement = ''

        def execute(self, sql, params=()):
            super().execute(sql, params)
            self.statement = ' '.join(sql.split())

        def fetchone(self):
            if 'SELECT j.status' in self.statement:
                return (
                    'committing',
                    1,
                    digest,
                    'json',
                    f'imports/site-a/{job_id}.bin',
                    {},
                    'article',
                    UUID(int=2104),
                )
            return None

        def fetchall(self):
            if 'SELECT field_key' in self.statement:
                return [('title', 'short_text', True, False, None, {})]
            if 'SELECT ordinal, source_row_sha256' in self.statement:
                return [(1, '0' * 64, 'create', None)]
            return []

    cursor = TamperedCursor()
    connection = Connection(cursor)
    bind(monkeypatch, connection)

    class Store:
        def get(self, *_args, **_kwargs):
            return content

    with pytest.raises(ValueError, match='content_integrity_failed'):
        worker.process_import_commit(site_id='site-a', job_id=job_id, artifact_store=Store())
    assert connection.rollbacks == 1 and connection.commits == 0
    assert all('INSERT INTO sitecontent_contentrecord' not in sql for sql, _ in cursor.calls)
