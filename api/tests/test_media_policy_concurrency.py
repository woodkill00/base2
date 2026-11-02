"""Local transaction-contract tests, not PostgreSQL race acceptance."""

from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID
import hashlib

import pytest

from api.services import media_library_runtime as runtime

ASSET = UUID(int=124)
JOB = UUID(int=125)
NOW = datetime.now(UTC)
SOURCE = b'bounded source'
DIGEST = hashlib.sha256(SOURCE).hexdigest()
ROW = ('media/site-a/source.bin', DIGEST, 'quarantined', 'image/png', len(SOURCE), 1, 1)


@pytest.fixture
def harness(monkeypatch):
    state = SimpleNamespace(
        active=False,
        statements=[],
        row=ROW,
        claim=True,
        commits=0,
        puts=[],
        reads=0,
        inspections=0,
        clock_valid=True,
        mutate=lambda: None,
    )
    manifest = {'modules': [{'id': name, 'enabled': True} for name in ('accounts', 'media')]}
    monkeypatch.setattr(runtime, 'SITE_MANIFEST', manifest, raising=False)
    monkeypatch.setenv('BASE2_PREVIEW_MODE', 'full')

    class Cursor:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def execute(self, sql, params=()):
            sql = ' '.join(sql.split())
            state.statements.append((sql, params))
            self.result = None
            if sql.startswith('SELECT storage_key'):
                self.result = state.row
            elif sql.startswith('SELECT 1 FROM sitecontent_mediajob'):
                self.result = (1,) if state.claim else None
            elif sql.startswith('SELECT %s>clock_timestamp()'):
                self.result = (state.clock_valid,)
            elif sql.startswith('SELECT id FROM sitecontent_mediaobjectversion'):
                self.result = (UUID(int=126),)
            elif sql.startswith('UPDATE sitecontent_mediaasset') and 'RETURNING' in sql:
                self.result = (2,)

        def fetchone(self):
            return self.result

    class Connection:
        def cursor(self):
            return Cursor()

        def commit(self):
            state.commits += 1

        def rollback(self):
            pass

    @contextmanager
    def db_conn(**_):
        assert not state.active
        state.active = True
        try:
            yield Connection()
        finally:
            state.active = False

    monkeypatch.setattr(runtime, 'db_conn', db_conn)

    class Store:
        def get(self, *_args, **_kwargs):
            assert not state.active
            state.reads += 1
            return SOURCE

        def put(self, **kwargs):
            assert not state.active
            state.puts.append(kwargs)
            return SimpleNamespace(
                object_key='variants/site-a/private.bin',
                sha256=hashlib.sha256(b'preview').hexdigest(),
                byte_size=7,
            )

        def delete(self, **_):
            pytest.fail('stale output must not be unlinked')

    def inspector(**_):
        assert not state.active
        state.inspections += 1
        state.mutate()
        return runtime.InspectionOutcome(
            SimpleNamespace(
                content=b'preview',
                sha256=hashlib.sha256(b'preview').hexdigest(),
                media_type='image/png',
                width=1,
                height=1,
            ),
            'clamav:1.4.3-27788',
            NOW,
            'image/png',
            'b' * 64,
        )

    state.run = lambda **extra: runtime.process_governed_media_asset(
        site_id='site-a',
        asset_id=ASSET,
        artifact_store=Store(),
        inspector=inspector,
        health_reader=lambda: None,
        job_id=JOB,
        attempt=1,
        lease_token=NOW + timedelta(minutes=5),
        **extra,
    )
    state.manifest = manifest
    state.store = Store()
    return state


def test_external_work_releases_transaction_and_effect_locks_policy_first(harness):
    assert harness.run() == 'ready'
    sql = [s for s, _ in harness.statements]
    lock = next(i for i, s in enumerate(sql) if 'pg_advisory_xact_lock(hashtext(' in s)
    asset = next(
        i for i, s in enumerate(sql) if s.startswith('SELECT storage_key') and 'FOR UPDATE' in s
    )
    assert lock < asset
    claims = [
        (s, p) for s, p in harness.statements if s.startswith('SELECT 1 FROM sitecontent_mediajob')
    ]
    assert len(claims) == 2
    for statement, params in claims:
        assert "kind='inspect'" in statement
        assert 'idempotency_key=%s' in statement and 'request_digest=%s' in statement
        assert 'lease_expires_at>clock_timestamp()' in statement
        assert f'inspect:{ASSET}:1' in params and DIGEST in params
    assert harness.commits == 1


@pytest.mark.parametrize(
    'index,value',
    [
        (0, 'media/site-a/new.bin'),
        (1, 'c' * 64),
        (2, 'deleted'),
        (2, 'archived'),
        (2, 'ready'),
        (3, 'image/jpeg'),
        (4, 99),
        (5, 2),
        (6, 2),
        (None, None),
    ],
)
def test_changed_or_deleted_snapshot_cancels_only_claim_and_never_binds(harness, index, value):
    def mutate():
        row = list(ROW)
        if index is not None:
            row[index] = value
        harness.row = tuple(row) if index is not None else None

    harness.mutate = mutate
    assert harness.run() == 'stale_snapshot'
    assert len(harness.puts) == 1
    writes = [s for s, _ in harness.statements if s.startswith(('INSERT', 'UPDATE'))]
    assert not any(
        'mediavariant' in s or 'mediaobjectversion' in s or 'UPDATE sitecontent_mediaasset' in s
        for s in writes
    )
    cancellation = next(
        (s, p) for s, p in harness.statements if s.startswith('UPDATE sitecontent_mediajob')
    )
    assert str(JOB) in cancellation[1] and 'site-a' in cancellation[1]
    assert harness.commits == 1


def test_lost_or_expired_claim_after_inspection_never_binds_or_cancels_successor(harness):
    harness.mutate = lambda: setattr(harness, 'claim', False)
    assert harness.run() == 'stale_attempt'
    assert len(harness.puts) == 1
    assert not any(s.startswith(('INSERT', 'UPDATE')) for s, _ in harness.statements)
    assert harness.commits == 0


def test_invalid_claim_never_reads_or_inspects(harness):
    harness.claim = False
    assert harness.run() == 'stale_attempt'
    assert harness.reads == harness.inspections == 0


@pytest.mark.parametrize('module', ['accounts', 'media'])
def test_disabled_module_denies_before_io(harness, module):
    next(m for m in harness.manifest['modules'] if m['id'] == module)['enabled'] = False
    with pytest.raises(ValueError, match='media_capability_disabled'):
        harness.run()
    assert not harness.statements and harness.reads == 0


def test_module_revoked_during_inspection_never_binds(harness):
    harness.mutate = lambda: harness.manifest.update(modules=[])
    with pytest.raises(ValueError, match='media_capability_disabled'):
        harness.run()
    assert not any(s.startswith(('INSERT', 'UPDATE')) for s, _ in harness.statements)


def test_restricted_preview_denies_before_io(harness, monkeypatch):
    monkeypatch.setenv('BASE2_PREVIEW_MODE', 'restricted')
    with pytest.raises(ValueError, match='media_disabled_in_restricted_preview'):
        harness.run()
    assert not harness.statements


@pytest.mark.parametrize(
    'attempt,token', [(None, NOW), (True, NOW), (0, NOW), (1, None), (1, datetime(2026, 1, 1))]
)
def test_partial_or_malformed_claim_rejected_before_io(harness, attempt, token):
    with pytest.raises(runtime.MediaRuntimeError, match='media_attempt_invalid'):
        runtime.process_governed_media_asset(
            site_id='site-a',
            asset_id=ASSET,
            artifact_store=None,
            job_id=JOB,
            attempt=attempt,
            lease_token=token,
        )
    assert not harness.statements


def test_error_result_is_also_fenced_by_snapshot(harness):
    def rejected_after_replacement():
        harness.row = ROW[:-1] + (2,)
        raise runtime.MediaRuntimeError('media_inspection_rejected')

    harness.mutate = rejected_after_replacement
    assert harness.run() == 'stale_snapshot'
    assert not harness.puts
    assert not any(s.startswith('UPDATE sitecontent_mediaasset') for s, _ in harness.statements)


def test_repeated_stale_outputs_reuse_one_private_immutable_local_key(tmp_path):
    from api.services.content_workspace_storage import PrivateArtifactStore, ArtifactIntegrityError

    store = PrivateArtifactStore(tmp_path / 'artifacts', key=b'x' * 32)
    kwargs = dict(namespace='variants', site_id='site-a', object_id=f'{ASSET}-v1-safe')
    first = store.put(**kwargs, content=b'preview')
    for _ in range(3):
        assert store.put(**kwargs, content=b'preview') == first
    with pytest.raises(ArtifactIntegrityError, match='content_artifact_conflict'):
        store.put(**kwargs, content=b'different stale preview')
    files = [p for p in tmp_path.rglob('*') if p.is_file()]
    assert len(files) == 1
    assert files[0].stat().st_mode & 0o777 == 0o600
    assert b'preview' not in files[0].read_bytes()
    assert store.get(first.object_key, expected_sha256=first.sha256) == b'preview'


def test_claim_expiring_while_job_lock_waits_is_rechecked_after_lock(harness):
    # The WHERE clock predicate was true before waiting, but is false once the
    # lock is granted. The locked ownership row itself is unchanged.
    harness.clock_valid = False
    assert harness.run() == 'stale_attempt'
    assert harness.reads == 0
    sql = [s for s, _ in harness.statements]
    claim = next(i for i, s in enumerate(sql) if s.startswith('SELECT 1 FROM sitecontent_mediajob'))
    assert sql[claim + 1] == 'SELECT %s>clock_timestamp()'


@pytest.mark.parametrize(
    'status,expected',
    [
        (None, 'not_found'),
        ('ready', 'already_ready'),
        ('rejected', 'already_rejected'),
        ('purged', 'already_purged'),
        ('deleted', 'not_ready'),
    ],
)
def test_initial_ineligible_snapshot_performs_no_external_work(harness, status, expected):
    harness.row = ROW[:2] + (status,) + ROW[3:] if status else None
    assert harness.run() == expected
    assert not harness.puts and harness.reads == 0


def test_claim_fields_without_job_are_rejected_before_io(harness):
    with pytest.raises(runtime.MediaRuntimeError, match='media_attempt_invalid'):
        runtime.process_governed_media_asset(
            site_id='site-a', asset_id=ASSET, artifact_store=None, attempt=1
        )
    assert not harness.statements


def test_derivative_digest_mismatch_never_enters_effect_transaction(harness, monkeypatch):
    original = runtime.InspectionOutcome

    def bad_outcome(preview, *args):
        preview.sha256 = 'c' * 64
        return original(preview, *args)

    monkeypatch.setattr(runtime, 'InspectionOutcome', bad_outcome)
    with pytest.raises(runtime.MediaRuntimeError, match='media_derivative_integrity_failed'):
        harness.run()
    assert not any('pg_advisory_xact_lock' in s for s, _ in harness.statements)
    assert harness.commits == 0
