import hashlib
import subprocess
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from api import tasks
from api.services.content_workspace_scanner import ScannerHealth, clamav_health
from api.services.media_library_parser import (
    FFPROBE_EXECUTION,
    MediaParserError,
    execute_fixed_parser,
    probe_media_no_network,
)
from api.services.media_library_runtime import (
    InspectionOutcome,
    MediaRuntimeError,
    append_media_audit,
    apply_due_media_governance,
    due_media_exports,
    inspect_media_payload,
    normalize_export_selection,
    process_governed_media_asset,
    process_media_export,
)


NOW = datetime(2026, 9, 6, 18, tzinfo=UTC)
CONTENT = b'ID3-safe-synthetic-audio'
DIGEST = hashlib.sha256(CONTENT).hexdigest()


class FakeStream:
    def __init__(self, reply):
        self.reply = reply
        self.sent = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def sendall(self, value):
        self.sent.append(value)

    def recv(self, _size):
        reply, self.reply = self.reply, b''
        return reply


def test_clamav_health_is_measured_and_strictly_normalized():
    stream = FakeStream(b'ClamAV 1.4.3/27788/Sat, 06 Sep 2026 17:30:00 +0000\0')
    health = clamav_health(connector=lambda *_args: stream)
    assert health.engine == 'clamav'
    assert health.engine_version == '1.4.3'
    assert health.definitions_version == '27788'
    assert health.definitions_updated_at == datetime(2026, 9, 6, 17, 30, tzinfo=UTC)
    assert stream.sent == [b'zVERSION\0']


def test_fixed_parser_is_stdin_only_shell_free_and_protocol_closed():
    calls = []

    def runner(argv, **kwargs):
        calls.append((argv, kwargs))
        return subprocess.CompletedProcess(
            argv,
            0,
            stdout=b'{"format":{"duration":"24.5"},"streams":[{"codec_type":"audio"}]}',
            stderr=b'',
        )

    result = probe_media_no_network(CONTENT, 'audio/mpeg', runner=runner)
    assert result.duration_seconds == 24.5 and result.stream_count == 1
    argv, kwargs = calls[0]
    assert argv == list(FFPROBE_EXECUTION.argv)
    assert argv[argv.index('-protocol_whitelist') + 1] == 'pipe'
    assert kwargs['input'] == CONTENT and kwargs['shell'] is False
    assert kwargs['close_fds'] is True and kwargs['timeout'] == 20
    assert set(kwargs['env']) == {'PATH', 'LC_ALL', 'HOME'}


def test_fixed_parser_fails_closed_on_output_or_command_variation():
    def oversized(argv, **_kwargs):
        return subprocess.CompletedProcess(argv, 0, stdout=b'x' * 65537, stderr=b'')

    with pytest.raises(MediaParserError, match='media_parser_rejected'):
        execute_fixed_parser(CONTENT, runner=oversized)
    changed = type(FFPROBE_EXECUTION)(('/bin/echo',), 1, 8)
    with pytest.raises(MediaParserError, match='media_parser_contract_invalid'):
        execute_fixed_parser(CONTENT, execution=changed)


def test_inspection_requires_fresh_measured_scanner_and_audio_probe():
    probed = []
    preview = type(
        'Preview',
        (),
        {
            'content': b'preview',
            'sha256': hashlib.sha256(b'preview').hexdigest(),
            'media_type': 'image/png',
            'width': 640,
            'height': 160,
        },
    )()
    health = ScannerHealth('clamav', '1.4.3', '27788', NOW - timedelta(minutes=5))
    outcome = inspect_media_payload(
        content=CONTENT,
        expected_sha256=DIGEST,
        media_type='audio/mpeg',
        scanner=lambda value: 'clean' if value == CONTENT else 'infected',
        health=health,
        observed_at=NOW,
        maximum_signature_age_hours=24,
        probe=lambda content, media_type: probed.append((content, media_type)),
        preview_builder=lambda **_kwargs: preview,
    )
    assert probed == [(CONTENT, 'audio/mpeg')]
    assert outcome.scanner_ref == 'clamav:1.4.3-27788'
    assert len(outcome.result_sha256) == 64

    with pytest.raises(MediaRuntimeError, match='media_scanner_stale'):
        inspect_media_payload(
            content=CONTENT,
            expected_sha256=DIGEST,
            media_type='audio/mpeg',
            scanner=lambda _value: 'clean',
            health=ScannerHealth('clamav', '1.4.3', '27788', NOW - timedelta(days=2)),
            observed_at=NOW,
            maximum_signature_age_hours=24,
            probe=lambda *_args: None,
            preview_builder=lambda **_kwargs: preview,
        )


@pytest.mark.parametrize(
    'verdict,code',
    [
        ('infected', 'media_inspection_rejected'),
        ('unknown', 'media_scanner_response_invalid'),
    ],
)
def test_inspection_rejects_non_clean_verdicts(verdict, code):
    with pytest.raises(MediaRuntimeError, match=code):
        inspect_media_payload(
            content=CONTENT,
            expected_sha256=DIGEST,
            media_type='audio/mpeg',
            scanner=lambda _value: verdict,
            health=ScannerHealth('clamav', '1.4.3', '27788', NOW),
            observed_at=NOW,
            maximum_signature_age_hours=24,
        )


def test_export_selection_is_exact_bounded_and_canonical():
    left = str(UUID(int=2))
    right = str(UUID(int=1))
    result = normalize_export_selection(
        {
            'fields': ['id', 'filename'],
            'assetIds': [left, right],
            'filters': {},
        }
    )
    assert result['assetIds'] == [right, left]
    with pytest.raises(MediaRuntimeError, match='media_export_selection_required'):
        normalize_export_selection(['id'])
    with pytest.raises(MediaRuntimeError, match='media_export_selection_invalid'):
        normalize_export_selection({'fields': ['id'], 'assetIds': [], 'filters': {}})
    with pytest.raises(MediaRuntimeError, match='media_export_selection_invalid'):
        normalize_export_selection(
            {
                'fields': ['id'],
                'assetIds': [str(UUID(int=110))],
                'filters': {'state': 'ready'},
            }
        )


def test_due_export_discovery_round_robins_tenants(monkeypatch):
    from api.services import media_library_runtime as runtime

    class FairCursor:
        def __init__(self):
            self.sql = ''

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def execute(self, sql, params=()):
            self.sql = ' '.join(sql.split())
            assert params == (4,)

        def fetchall(self):
            return [
                ('site-a', UUID(int=701)),
                ('site-b', UUID(int=801)),
                ('site-a', UUID(int=702)),
                ('site-b', UUID(int=802)),
            ]

    cursor = FairCursor()

    @contextmanager
    def global_worker(*, tenant_id=None):
        assert tenant_id is None
        connection = type('Connection', (), {'cursor': lambda _self: cursor})()
        yield connection

    monkeypatch.setattr(runtime, 'db_conn', global_worker)
    assert due_media_exports(limit=4) == [
        ('site-a', str(UUID(int=701))),
        ('site-b', str(UUID(int=801))),
        ('site-a', str(UUID(int=702))),
        ('site-b', str(UUID(int=802))),
    ]
    assert 'ROW_NUMBER() OVER ( PARTITION BY site_id' in cursor.sql
    assert 'ORDER BY tenant_rank,created_at,id' in cursor.sql


def test_media_runtime_tasks_dispatch_only_discovered_fixed_ids(monkeypatch):
    export_id = '00000000-0000-0000-0000-000000000110'
    delivered = []
    monkeypatch.setattr(tasks, 'due_media_exports', lambda *, limit: [('site-a', export_id)])
    monkeypatch.setattr(
        tasks.process_media_export_task,
        'delay',
        lambda site_id, identifier: delivered.append((site_id, identifier)),
    )
    assert tasks.replay_media_exports(limit=10) == 1
    assert delivered == [('site-a', export_id)]
    monkeypatch.setattr(
        tasks,
        'apply_due_media_governance',
        lambda *, limit: {'holdsExpired': limit, 'abuseCasesEnforced': 0},
    )
    assert tasks.apply_media_governance(limit=3) == {
        'holdsExpired': 3,
        'abuseCasesEnforced': 0,
    }


class RuntimeCursor:
    def __init__(self, asset_id):
        self.asset_id = asset_id
        self.calls = []
        self.response = None
        self.rowcount = 0

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, sql, params=()):
        compact = ' '.join(sql.split())
        self.calls.append((compact, params))
        self.response = None
        self.rowcount = 0
        if compact.startswith('SELECT storage_key'):
            self.response = (
                'media/site-a/source.bin',
                DIGEST,
                'quarantined',
                'audio/mpeg',
                len(CONTENT),
                1,
                1,
            )
        elif compact.startswith('SELECT id FROM sitecontent_mediaobjectversion'):
            self.response = (UUID(int=4110),)
        elif (
            compact.startswith('UPDATE sitecontent_mediaasset')
            and 'RETURNING lock_version' in compact
        ):
            self.response = (2,)
        elif compact.startswith('SELECT sequence, event_hash'):
            self.response = None
        elif compact.startswith('UPDATE sitecontent_mediajob') and 'SET available_at=' in compact:
            self.rowcount = 1

    def fetchone(self):
        return self.response


class RuntimeConnection:
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


def test_governed_worker_reaches_ready_with_job_inspection_and_hash_chain(monkeypatch):
    from api.services import media_library_runtime as runtime

    asset_id = UUID(int=110)
    cursor = RuntimeCursor(asset_id)
    connection = RuntimeConnection(cursor)

    @contextmanager
    def bound(*, tenant_id=None):
        assert tenant_id == 'site-a'
        yield connection

    monkeypatch.setattr(runtime, 'db_conn', bound)
    preview = type(
        'Preview',
        (),
        {
            'content': b'preview',
            'sha256': hashlib.sha256(b'preview').hexdigest(),
            'media_type': 'image/png',
            'width': 640,
            'height': 160,
        },
    )()
    outcome = InspectionOutcome(preview, 'clamav:1.4.3-27788', NOW, 'audio/mpeg', 'b' * 64)

    class Store:
        def get(self, key, *, expected_sha256):
            assert key == 'media/site-a/source.bin' and expected_sha256 == DIGEST
            return CONTENT

        def put(self, **kwargs):
            assert kwargs['namespace'] == 'variants' and kwargs['content'] == b'preview'
            return type(
                'Stored',
                (),
                {
                    'object_key': 'variants/site-a/safe.bin',
                    'sha256': preview.sha256,
                    'byte_size': len(preview.content),
                },
            )()

    result = process_governed_media_asset(
        site_id='site-a',
        asset_id=asset_id,
        artifact_store=Store(),
        health_reader=lambda: ScannerHealth('clamav', '1.4.3', '27788', NOW),
        observed_at=NOW,
        inspector=lambda **_kwargs: outcome,
    )
    assert result == 'ready' and connection.commits == 1 and connection.rollbacks == 0
    statements = ' '.join(sql for sql, _params in cursor.calls)
    assert 'sitecontent_mediainspectionresult' in statements
    assert 'sitecontent_mediajob' in statements
    assert 'sitecontent_mediaauditevent' in statements
    assert "SET status='ready'" in statements


class RetryRuntimeCursor(RuntimeCursor):
    def __init__(self, asset_id):
        super().__init__(asset_id)
        self.job_attempt = 0
        self.job_status = None

    def execute(self, sql, params=()):
        super().execute(sql, params)
        compact = ' '.join(sql.split())
        if compact.startswith('INSERT INTO sitecontent_mediajob'):
            if 'RETURNING status,attempt,maximum_attempts' in compact:
                self.job_attempt = min(self.job_attempt + 1, 3)
                rejected = bool(params[7])
                self.job_status = 'failed' if rejected or self.job_attempt >= 3 else 'retryable'
                self.response = (self.job_status, self.job_attempt, 3)
            else:
                self.job_attempt = min(self.job_attempt + 1, 3)
                self.job_status = 'completed'


@pytest.mark.parametrize('infected,expected', [(False, 'ready'), (True, 'rejected')])
def test_scan_task_uses_real_governed_worker_result_contract(monkeypatch, infected, expected):
    from api.services import media_library_runtime as runtime
    from api.services.media_inspector_client import MediaInspectorClientError

    asset_id = UUID(int=110)
    cursor = RetryRuntimeCursor(asset_id) if infected else RuntimeCursor(asset_id)
    connection = RuntimeConnection(cursor)

    @contextmanager
    def bound(*, tenant_id=None):
        assert tenant_id == 'site-a'
        yield connection

    monkeypatch.setattr(runtime, 'db_conn', bound)
    preview = type(
        'Preview', (),
        {'content': b'preview', 'sha256': hashlib.sha256(b'preview').hexdigest(),
         'media_type': 'image/png', 'width': 640, 'height': 160},
    )()
    isolated = type(
        'Isolated', (),
        {
            'preview': preview,
            'scanner_ref': 'clamav:1.4.3-27788',
            'definitions_at': NOW,
            'observed_media_type': 'audio/mpeg',
            'result_sha256': 'b' * 64,
            'decoder_ref': 'ffprobe:7.1',
            'measurements': {'durationSeconds': 1},
        },
    )()

    def inspect(**_kwargs):
        if infected:
            raise MediaInspectorClientError('media_inspection_rejected')
        return isolated

    monkeypatch.setattr(runtime, 'inspect_media_via_spool', inspect)

    class Store:
        def get(self, _key, *, expected_sha256):
            assert expected_sha256 == DIGEST
            return CONTENT

        def put(self, **_kwargs):
            return type('Stored', (), {
                'object_key': 'variants/site-a/safe.bin',
                'sha256': preview.sha256,
                'byte_size': len(preview.content),
            })()

    completed = []
    monkeypatch.setattr(tasks, '_workspace_artifact_store', Store)
    monkeypatch.setattr(tasks, 'begin_media_scan_attempt', lambda **_kwargs: True)
    monkeypatch.setattr(
        tasks, 'finish_media_scan_attempt', lambda **kwargs: completed.append(kwargs)
    )
    result = tasks.scan_workspace_asset_task(
        'site-a', str(asset_id), str(UUID(int=111)), 1, '2026-09-07T12:02:00+00:00'
    )
    assert result == expected
    assert completed[0]['result'] == expected


def test_transient_inspector_failure_is_durable_bounded_and_recovers(monkeypatch):
    from api.services import media_library_runtime as runtime

    asset_id = UUID(int=110)
    cursor = RetryRuntimeCursor(asset_id)
    connection = RuntimeConnection(cursor)

    @contextmanager
    def bound(*, tenant_id=None):
        assert tenant_id == 'site-a'
        yield connection

    monkeypatch.setattr(runtime, 'db_conn', bound)
    preview = type(
        'Preview',
        (),
        {
            'content': b'preview',
            'sha256': hashlib.sha256(b'preview').hexdigest(),
            'media_type': 'image/png',
            'width': 640,
            'height': 160,
        },
    )()
    outcome = InspectionOutcome(preview, 'clamav:1.4.3-27788', NOW, 'audio/mpeg', 'b' * 64)

    class Store:
        def get(self, _key, *, expected_sha256):
            assert expected_sha256 == DIGEST
            return CONTENT

        def put(self, **_kwargs):
            return type(
                'Stored',
                (),
                {
                    'object_key': 'variants/site-a/safe.bin',
                    'sha256': preview.sha256,
                    'byte_size': len(preview.content),
                },
            )()

    failed = process_governed_media_asset(
        site_id='site-a',
        asset_id=asset_id,
        artifact_store=Store(),
        scanner=lambda _content: 'clean',
        health_reader=lambda: ScannerHealth('clamav', '1.4.3', '27788', NOW),
        observed_at=NOW,
        inspector=lambda **_kwargs: (_ for _ in ()).throw(
            MediaRuntimeError('media_dependency_unavailable')
        ),
    )
    assert failed == 'quarantined'
    assert cursor.job_status == 'retryable' and cursor.job_attempt == 1
    retry_schedule = next(
        params for sql, params in cursor.calls
        if sql.startswith('UPDATE sitecontent_mediajob') and 'SET available_at=' in sql
    )
    assert retry_schedule[0] == 15 and retry_schedule[-1] == 1
    failure_update = next(
        params
        for sql, params in cursor.calls
        if sql.startswith('UPDATE sitecontent_mediaasset') and 'SET status=%s' in sql
    )
    assert failure_update[0] == 'quarantined'

    recovered = process_governed_media_asset(
        site_id='site-a',
        asset_id=asset_id,
        artifact_store=Store(),
        health_reader=lambda: ScannerHealth('clamav', '1.4.3', '27788', NOW),
        observed_at=NOW,
        inspector=lambda **_kwargs: outcome,
    )
    assert recovered == 'ready'
    assert cursor.job_status == 'completed' and cursor.job_attempt == 2
    assert connection.commits == 2 and connection.rollbacks == 0


def test_transient_inspector_retry_attempts_stop_at_durable_limit(monkeypatch):
    from api.services import media_library_runtime as runtime

    asset_id = UUID(int=110)
    cursor = RetryRuntimeCursor(asset_id)
    connection = RuntimeConnection(cursor)

    @contextmanager
    def bound(*, tenant_id=None):
        assert tenant_id == 'site-a'
        yield connection

    monkeypatch.setattr(runtime, 'db_conn', bound)

    class Store:
        def get(self, _key, *, expected_sha256):
            assert expected_sha256 == DIGEST
            return CONTENT

    def unavailable(**_kwargs):
        raise MediaRuntimeError('media_dependency_unavailable')

    results = [
        process_governed_media_asset(
            site_id='site-a',
            asset_id=asset_id,
            artifact_store=Store(),
            scanner=lambda _content: 'clean',
            health_reader=lambda: ScannerHealth('clamav', '1.4.3', '27788', NOW),
            observed_at=NOW,
            inspector=unavailable,
        )
        for _attempt in range(3)
    ]
    assert results == ['quarantined', 'quarantined', 'failed']
    assert cursor.job_status == 'failed' and cursor.job_attempt == 3
    assert connection.commits == 3 and connection.rollbacks == 0


def test_permanent_inspector_rejection_is_not_retried(monkeypatch):
    from api.services import media_library_runtime as runtime
    from api.services.media_inspector_client import MediaInspectorClientError

    asset_id = UUID(int=110)
    cursor = RetryRuntimeCursor(asset_id)
    connection = RuntimeConnection(cursor)

    @contextmanager
    def bound(*, tenant_id=None):
        assert tenant_id == 'site-a'
        yield connection

    monkeypatch.setattr(runtime, 'db_conn', bound)

    class Store:
        def get(self, _key, *, expected_sha256):
            assert expected_sha256 == DIGEST
            return CONTENT

    result = process_governed_media_asset(
        site_id='site-a',
        asset_id=asset_id,
        artifact_store=Store(),
        scanner=lambda _content: 'clean',
        health_reader=lambda: ScannerHealth('clamav', '1.4.3', '27788', NOW),
        observed_at=NOW,
        inspector=lambda **_kwargs: (_ for _ in ()).throw(
            MediaInspectorClientError('media_inspection_rejected')
        ),
    )
    assert result == 'rejected'
    assert cursor.job_status == 'failed' and cursor.job_attempt == 1
    assert connection.commits == 1 and connection.rollbacks == 0


def test_audit_rejects_private_or_unbounded_detail_before_insert():
    cursor = RuntimeCursor(UUID(int=110))
    with pytest.raises(MediaRuntimeError, match='media_audit_detail_invalid'):
        append_media_audit(
            cursor,
            site_id='site-a',
            event_type='media.export.failed',
            actor_ref='system:worker',
            subject_ref='export:test',
            detail={'signed_url': 'https://private.example'},
        )
    assert cursor.calls == []


class ExportCursor(RuntimeCursor):
    def execute(self, sql, params=()):
        super().execute(sql, params)
        compact = ' '.join(sql.split())
        if compact.startswith('SELECT status,output_format'):
            self.response = (
                'queued',
                'csv',
                {'fields': ['id', 'filename'], 'assetIds': [str(UUID(int=110))], 'filters': {}},
                'user:test',
                'd' * 64,
                datetime.now(UTC) + timedelta(hours=1),
            )
        elif compact.startswith('SELECT sequence, event_hash'):
            self.response = (3, 'a' * 64)

    def fetchall(self):
        if self.calls and self.calls[-1][0].startswith('SELECT id,original_name'):
            return [(UUID(int=110), 'safe.mp3', 'audio/mpeg', 24, DIGEST, 'ready', 'private', NOW)]
        return []


def test_media_export_worker_uses_exact_selection_and_completes_atomically(monkeypatch):
    from api.services import media_library_runtime as runtime

    cursor = ExportCursor(UUID(int=110))
    connection = RuntimeConnection(cursor)

    @contextmanager
    def bound(*, tenant_id=None):
        assert tenant_id == 'site-a'
        yield connection

    monkeypatch.setattr(runtime, 'db_conn', bound)

    class Store:
        def put(self, **kwargs):
            assert kwargs['namespace'] == 'media-exports'
            assert b'safe.mp3' in kwargs['content']
            return type(
                'Stored',
                (),
                {
                    'object_key': 'media-exports/site-a/result.bin',
                    'sha256': hashlib.sha256(kwargs['content']).hexdigest(),
                },
            )()

    assert (
        process_media_export(site_id='site-a', export_id=UUID(int=500), artifact_store=Store())
        == 'ready'
    )
    assert connection.commits == 1 and connection.rollbacks == 0
    statements = ' '.join(sql for sql, _params in cursor.calls)
    assert 'id=ANY(%s::uuid[])' in statements
    export_query = next(
        (sql, params) for sql, params in cursor.calls if sql.startswith('SELECT id,original_name')
    )
    assert "owner_ref=%s OR visibility IN ('authenticated','public')" in export_query[0]
    assert export_query[1] == ('site-a', [str(UUID(int=110))], 'user:test')
    assert "SET status='ready'" in statements
    assert 'sitecontent_mediaauditevent' in statements


class GovernanceDiscoveryCursor(RuntimeCursor):
    def __init__(self):
        super().__init__(UUID(int=110))
        self.result_sets = []

    def execute(self, sql, params=()):
        super().execute(sql, params)
        compact = ' '.join(sql.split())
        if compact.startswith('SELECT site_id,id FROM sitecontent_mediaretentionhold'):
            self.result_sets = [('site-a', UUID(int=701))]
        elif compact.startswith('SELECT c.site_id,c.id'):
            self.result_sets = [
                ('site-a', UUID(int=601)),
                ('site-b', UUID(int=602)),
            ]

    def fetchall(self):
        values, self.result_sets = self.result_sets, []
        return values


class GovernanceTenantCursor(RuntimeCursor):
    def __init__(self, site):
        super().__init__(UUID(int=110))
        self.site = site
        self.result_sets = []
        self.rowcount = 0

    def execute(self, sql, params=()):
        super().execute(sql, params)
        compact = ' '.join(sql.split())
        self.rowcount = 0
        if compact.startswith('UPDATE sitecontent_mediaretentionhold'):
            assert self.site == 'site-a' and params[0] == self.site
            self.result_sets = [(UUID(int=110), 'legal_hold')]
        elif compact.startswith('SELECT c.id,c.asset_id'):
            if self.site == 'site-a':
                self.result_sets = [(UUID(int=601), UUID(int=110), 'quarantined', 'ready', 2)]
            else:
                self.result_sets = [(UUID(int=602), UUID(int=111), 'removed', 'archived', 4)]
        elif compact.startswith('UPDATE sitecontent_mediaasset'):
            assert params[1] == self.site
            self.rowcount = 1

    def fetchall(self):
        values, self.result_sets = self.result_sets, []
        return values


def test_governance_worker_expires_holds_and_enforces_only_reviewed_states(monkeypatch):
    from api.services import media_library_runtime as runtime

    discovery_cursor = GovernanceDiscoveryCursor()
    discovery = RuntimeConnection(discovery_cursor)
    tenant_connections = {}

    @contextmanager
    def bound(*, tenant_id=None):
        if tenant_id is None:
            yield discovery
            return
        cursor = GovernanceTenantCursor(tenant_id)
        connection = RuntimeConnection(cursor)
        tenant_connections[tenant_id] = connection
        yield connection

    monkeypatch.setattr(runtime, 'db_conn', bound)
    assert apply_due_media_governance(limit=10) == {
        'holdsExpired': 1,
        'abuseCasesEnforced': 2,
    }
    assert set(tenant_connections) == {'site-a', 'site-b'}
    assert all(value.commits == 1 and value.rollbacks == 0 for value in tenant_connections.values())
    calls = [call for connection in tenant_connections.values() for call in connection.value.calls]
    updates = [call for call in calls if call[0].startswith('UPDATE sitecontent_mediaasset')]
    assert [item[1][0] for item in updates] == ['archived', 'soft_deleted']
    statements = ' '.join(sql for sql, _params in calls)
    assert 'sitecontent_mediadeliverygrant' in statements
    assert (
        sum(sql.startswith('INSERT INTO sitecontent_mediaauditevent') for sql, _params in calls)
        == 3
    )
