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
            argv, 0,
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
        'Preview', (),
        {'content': b'preview', 'sha256': hashlib.sha256(b'preview').hexdigest(),
         'media_type': 'image/png', 'width': 640, 'height': 160},
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
            content=CONTENT, expected_sha256=DIGEST, media_type='audio/mpeg',
            scanner=lambda _value: 'clean',
            health=ScannerHealth('clamav', '1.4.3', '27788', NOW - timedelta(days=2)),
            observed_at=NOW, maximum_signature_age_hours=24,
            probe=lambda *_args: None, preview_builder=lambda **_kwargs: preview,
        )


@pytest.mark.parametrize('verdict,code', [
    ('infected', 'media_inspection_rejected'),
    ('unknown', 'media_scanner_response_invalid'),
])
def test_inspection_rejects_non_clean_verdicts(verdict, code):
    with pytest.raises(MediaRuntimeError, match=code):
        inspect_media_payload(
            content=CONTENT, expected_sha256=DIGEST, media_type='audio/mpeg',
            scanner=lambda _value: verdict,
            health=ScannerHealth('clamav', '1.4.3', '27788', NOW),
            observed_at=NOW, maximum_signature_age_hours=24,
        )


def test_export_selection_is_exact_bounded_and_canonical():
    left = str(UUID(int=2))
    right = str(UUID(int=1))
    result = normalize_export_selection({
        'fields': ['id', 'filename'], 'assetIds': [left, right], 'filters': {},
    })
    assert result['assetIds'] == [right, left]
    with pytest.raises(MediaRuntimeError, match='media_export_selection_required'):
        normalize_export_selection(['id'])
    with pytest.raises(MediaRuntimeError, match='media_export_selection_invalid'):
        normalize_export_selection({'fields': ['id'], 'assetIds': [], 'filters': {}})
    with pytest.raises(MediaRuntimeError, match='media_export_selection_invalid'):
        normalize_export_selection({
            'fields': ['id'], 'assetIds': [str(UUID(int=110))],
            'filters': {'state': 'ready'},
        })


def test_media_runtime_tasks_dispatch_only_discovered_fixed_ids(monkeypatch):
    export_id = '00000000-0000-0000-0000-000000000110'
    delivered = []
    monkeypatch.setattr(tasks, 'due_media_exports', lambda *, limit: [('site-a', export_id)])
    monkeypatch.setattr(
        tasks.process_media_export_task, 'delay',
        lambda site_id, identifier: delivered.append((site_id, identifier)),
    )
    assert tasks.replay_media_exports(limit=10) == 1
    assert delivered == [('site-a', export_id)]
    monkeypatch.setattr(
        tasks, 'apply_due_media_governance',
        lambda *, limit: {'holdsExpired': limit, 'abuseCasesEnforced': 0},
    )
    assert tasks.apply_media_governance(limit=3) == {
        'holdsExpired': 3, 'abuseCasesEnforced': 0,
    }


class RuntimeCursor:
    def __init__(self, asset_id):
        self.asset_id = asset_id
        self.calls = []
        self.response = None

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, sql, params=()):
        compact = ' '.join(sql.split())
        self.calls.append((compact, params))
        self.response = None
        if compact.startswith('SELECT storage_key'):
            self.response = ('media/site-a/source.bin', DIGEST, 'quarantined', 'audio/mpeg', len(CONTENT), 1, 1)
        elif compact.startswith('SELECT id FROM sitecontent_mediaobjectversion'):
            self.response = (UUID(int=4110),)
        elif compact.startswith('UPDATE sitecontent_mediaasset') and 'RETURNING lock_version' in compact:
            self.response = (2,)
        elif compact.startswith('SELECT sequence, event_hash'):
            self.response = None

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
        'Preview', (),
        {'content': b'preview', 'sha256': hashlib.sha256(b'preview').hexdigest(),
         'media_type': 'image/png', 'width': 640, 'height': 160},
    )()
    outcome = InspectionOutcome(preview, 'clamav:1.4.3-27788', NOW, 'audio/mpeg', 'b' * 64)

    class Store:
        def get(self, key, *, expected_sha256):
            assert key == 'media/site-a/source.bin' and expected_sha256 == DIGEST
            return CONTENT

        def put(self, **kwargs):
            assert kwargs['namespace'] == 'variants' and kwargs['content'] == b'preview'
            return type('Stored', (), {
                'object_key': 'variants/site-a/safe.bin',
                'sha256': preview.sha256,
                'byte_size': len(preview.content),
            })()

    result = process_governed_media_asset(
        site_id='site-a', asset_id=asset_id, artifact_store=Store(),
        health_reader=lambda: ScannerHealth('clamav', '1.4.3', '27788', NOW),
        observed_at=NOW, inspector=lambda **_kwargs: outcome,
    )
    assert result == 'ready' and connection.commits == 1 and connection.rollbacks == 0
    statements = ' '.join(sql for sql, _params in cursor.calls)
    assert 'sitecontent_mediainspectionresult' in statements
    assert 'sitecontent_mediajob' in statements
    assert 'sitecontent_mediaauditevent' in statements
    assert "SET status='ready'" in statements


def test_audit_rejects_private_or_unbounded_detail_before_insert():
    cursor = RuntimeCursor(UUID(int=110))
    with pytest.raises(MediaRuntimeError, match='media_audit_detail_invalid'):
        append_media_audit(
            cursor, site_id='site-a', event_type='media.export.failed',
            actor_ref='system:worker', subject_ref='export:test',
            detail={'signed_url': 'https://private.example'},
        )
    assert cursor.calls == []


class ExportCursor(RuntimeCursor):
    def execute(self, sql, params=()):
        super().execute(sql, params)
        compact = ' '.join(sql.split())
        if compact.startswith('SELECT status,output_format'):
            self.response = (
                'queued', 'csv',
                {'fields': ['id', 'filename'],
                 'assetIds': [str(UUID(int=110))], 'filters': {}},
                'user:test', 'd' * 64, datetime.now(UTC) + timedelta(hours=1),
            )
        elif compact.startswith('SELECT sequence, event_hash'):
            self.response = (3, 'a' * 64)

    def fetchall(self):
        if self.calls and self.calls[-1][0].startswith('SELECT id,original_name'):
            return [(UUID(int=110), 'safe.mp3', 'audio/mpeg', 24, DIGEST,
                     'ready', 'private', NOW)]
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
            return type('Stored', (), {
                'object_key': 'media-exports/site-a/result.bin',
                'sha256': hashlib.sha256(kwargs['content']).hexdigest(),
            })()

    assert process_media_export(
        site_id='site-a', export_id=UUID(int=500), artifact_store=Store()
    ) == 'ready'
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


class GovernanceCursor(RuntimeCursor):
    def __init__(self):
        super().__init__(UUID(int=110))
        self.result_sets = []

    def execute(self, sql, params=()):
        super().execute(sql, params)
        compact = ' '.join(sql.split())
        if compact.startswith('UPDATE sitecontent_mediaretentionhold'):
            self.result_sets = [('site-a', UUID(int=110), 'legal_hold')]
        elif compact.startswith('SELECT c.site_id'):
            self.result_sets = [
                ('site-a', UUID(int=601), UUID(int=110), 'quarantined', 'ready', 2),
                ('site-b', UUID(int=602), UUID(int=111), 'removed', 'archived', 4),
            ]
        elif compact.startswith('SELECT sequence, event_hash'):
            self.response = None

    def fetchall(self):
        values, self.result_sets = self.result_sets, []
        return values


def test_governance_worker_expires_holds_and_enforces_only_reviewed_states(monkeypatch):
    from api.services import media_library_runtime as runtime

    cursor = GovernanceCursor()
    connection = RuntimeConnection(cursor)

    @contextmanager
    def bound(*, tenant_id=None):
        assert tenant_id is None
        yield connection

    monkeypatch.setattr(runtime, 'db_conn', bound)
    assert apply_due_media_governance(limit=10) == {
        'holdsExpired': 1, 'abuseCasesEnforced': 2,
    }
    assert connection.commits == 1 and connection.rollbacks == 0
    updates = [call for call in cursor.calls if call[0].startswith('UPDATE sitecontent_mediaasset')]
    assert [item[1][0] for item in updates] == ['archived', 'soft_deleted']
    statements = ' '.join(sql for sql, _params in cursor.calls)
    assert 'sitecontent_mediadeliverygrant' in statements
    assert sum(
        sql.startswith('INSERT INTO sitecontent_mediaauditevent') for sql, _params in cursor.calls
    ) == 3
