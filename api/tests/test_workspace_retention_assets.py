"""Local IO/transaction tests; database authority requires PostgreSQL acceptance."""

from contextlib import contextmanager
from uuid import UUID

import pytest

from api.services import workspace_retention_assets as retention
from api.services.content_workspace_storage import PrivateArtifactStore, ArtifactIntegrityError

ASSET = str(UUID(int=1))
PLAN = str(UUID(int=2))


def manifest(store):
    result = []
    for namespace, object_id in [('variants', f'{ASSET}-safe'), ('media', ASSET)]:
        obj = store.put(
            namespace=namespace, site_id='site-a', object_id=object_id, content=b'fixture'
        )
        result.append(
            dict(
                namespace=namespace,
                object_id=object_id,
                object_key=obj.object_key,
                sha256=obj.sha256,
                byte_size=obj.byte_size,
            )
        )
    return result


@pytest.fixture
def store(tmp_path):
    return PrivateArtifactStore(tmp_path / 'objects', key=b'x' * 32)


def bind(monkeypatch, objects, *, complete=True):
    events = []
    responses = [[(ASSET,)], [(PLAN, objects)], [(complete,)]]

    class Cursor:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def execute(self, sql, params=()):
            events.append(('sql', sql, params))

        def fetchall(self):
            return self.rows

        def fetchone(self):
            return self.rows.pop(0) if self.rows else None

    class Connection:
        def cursor(self):
            return self.cursor_obj

        def commit(self):
            events.append(('commit',))

        def rollback(self):
            events.append(('rollback',))

    @contextmanager
    def connection(**kwargs):
        conn = Connection()
        conn.cursor_obj = Cursor()
        conn.cursor_obj.rows = responses.pop(0)
        events.append(('open',))
        try:
            yield conn
        finally:
            events.append(('close',))

    monkeypatch.setattr(retention, 'db_conn', connection)
    return events


def test_committed_intent_precedes_io_and_finalization_follows_all_objects(monkeypatch, store):
    objects = manifest(store)
    events = bind(monkeypatch, objects)
    original = store.delete

    def delete(**kwargs):
        assert events[-1] == ('close',) or events[-1][0] == 'io'
        assert ('commit',) in events
        assert kwargs['missing_ok'] is False
        original(**kwargs)
        events.append(('io',))

    monkeypatch.setattr(store, 'delete', delete)
    assert retention.purge_workspace_assets(artifact_store=store, site_id='site-a', limit=1) == 1
    assert sum(e[0] == 'io' for e in events) == 2
    assert 'base2_complete_workspace_asset_purge' in next(
        e[1] for e in events if e[0] == 'sql' and 'complete' in e[1]
    )


def test_partial_io_failure_does_not_finalize_and_retry_uses_same_manifest(monkeypatch, store):
    objects = manifest(store)
    events = bind(monkeypatch, objects)
    original = store.delete

    def fail_second(**kwargs):
        if kwargs['namespace'] == 'media':
            raise OSError('fixture IO failure')
        return original(**kwargs)

    monkeypatch.setattr(store, 'delete', fail_second)
    with pytest.raises(OSError):
        retention.purge_workspace_assets(artifact_store=store, site_id='site-a', limit=1)
    assert not any(e[0] == 'sql' and 'complete_workspace' in e[1] for e in events)
    monkeypatch.setattr(store, 'delete', original)
    bind(monkeypatch, objects)
    assert retention.purge_workspace_assets(artifact_store=store, site_id='site-a', limit=1) == 1


def test_unavailable_is_not_evidence_of_missing(monkeypatch, store):
    objects = manifest(store)
    bind(monkeypatch, objects)

    def denied(**kwargs):
        try:
            raise PermissionError('fixture denied')
        except PermissionError as exc:
            raise ArtifactIntegrityError('content_artifact_unavailable') from exc

    monkeypatch.setattr(store, 'delete', denied)
    with pytest.raises(ArtifactIntegrityError):
        retention.purge_workspace_assets(artifact_store=store, site_id='site-a', limit=1)


@pytest.mark.parametrize('mutation', ['owner', 'digest', 'count', 'size', 'duplicate'])
def test_manifest_rejected_before_any_io(monkeypatch, store, mutation):
    objects = manifest(store)
    if mutation == 'owner':
        objects[-1]['object_id'] = str(UUID(int=99))
    if mutation == 'digest':
        objects[-1]['sha256'] = 'invalid'
    if mutation == 'count':
        objects *= 65
    if mutation == 'size':
        objects[-1]['byte_size'] = 100 * 1024 * 1024 + 1
    if mutation == 'duplicate':
        objects.append(objects[0])
    bind(monkeypatch, objects)
    monkeypatch.setattr(store, 'delete', lambda **kwargs: pytest.fail('IO before validation'))
    with pytest.raises(ValueError):
        retention.purge_workspace_assets(artifact_store=store, site_id='site-a', limit=1)


@pytest.mark.parametrize('limit', [0, 501, True, 1.5])
def test_invalid_limit_never_opens_transaction(monkeypatch, store, limit):
    monkeypatch.setattr(
        retention, 'db_conn', lambda **kwargs: pytest.fail('invalid limit reached DB')
    )
    with pytest.raises(ValueError):
        retention.purge_workspace_assets(artifact_store=store, site_id='site-a', limit=limit)


def test_remote_backend_rejected_before_claim(monkeypatch):
    monkeypatch.setattr(
        retention, 'db_conn', lambda **kwargs: pytest.fail('unsupported backend reached DB')
    )
    with pytest.raises(ValueError, match='content_retention_local_storage_required'):
        retention.purge_workspace_assets(artifact_store=object(), site_id='site-a', limit=1)


def test_completed_replay_not_counted_again(monkeypatch, store):
    objects = manifest(store)
    bind(monkeypatch, objects, complete=False)
    assert retention.purge_workspace_assets(artifact_store=store, site_id='site-a', limit=1) == 0


def test_corrupt_ciphertext_blocks_completion(monkeypatch, store):
    objects = manifest(store)
    store._path(objects[0]['object_key']).write_bytes(b'corrupted fixture')
    events = bind(monkeypatch, objects)
    with pytest.raises(ArtifactIntegrityError, match='content_integrity_failed'):
        retention.purge_workspace_assets(artifact_store=store, site_id='site-a', limit=1)
    assert not any(e[0] == 'sql' and 'complete_workspace' in e[1] for e in events)


@pytest.mark.parametrize('objects', [None, [], [{}], [{'namespace': 'media'}]])
def test_malformed_manifest_is_rejected(objects):
    with pytest.raises(ValueError, match='content_retention_manifest_invalid'):
        retention._manifest(objects, site_id='site-a', asset_id=ASSET)


def test_missing_original_is_not_a_complete_manifest(store):
    objects = manifest(store)[:1]
    with pytest.raises(ValueError, match='content_retention_manifest_invalid'):
        retention._manifest(objects, site_id='site-a', asset_id=ASSET)


def test_no_claim_means_no_filesystem_access(monkeypatch, store):
    events = bind(monkeypatch, [])
    monkeypatch.setattr(retention, '_claim', lambda **kwargs: None)
    monkeypatch.setattr(store, 'delete', lambda **kwargs: pytest.fail('unclaimed IO'))
    assert retention.purge_workspace_assets(artifact_store=store, site_id='site-a', limit=1) == 0
    assert not any(e[0] == 'io' for e in events)


def test_unconfirmed_completion_rolls_back(monkeypatch, store):
    objects = manifest(store)
    events = bind(monkeypatch, objects, complete=None)
    with pytest.raises(ValueError, match='content_retention_completion_invalid'):
        retention.purge_workspace_assets(artifact_store=store, site_id='site-a', limit=1)
    assert events[-2] == ('rollback',)


def test_claim_failure_rolls_back_and_never_deletes(monkeypatch, store):
    events = []

    class Cursor:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def execute(self, *args):
            raise RuntimeError('fixture claim failure')

    class Connection:
        def cursor(self):
            return Cursor()

        def rollback(self):
            events.append('rollback')

    @contextmanager
    def connection(**kwargs):
        yield Connection()

    monkeypatch.setattr(retention, 'db_conn', connection)
    with pytest.raises(RuntimeError, match='fixture claim failure'):
        retention._claim(site_id='site-a', asset_id=ASSET)
    assert events == ['rollback']


def test_hash_mismatch_never_finalizes_or_deletes_mismatched_object(monkeypatch, store):
    objects = manifest(store)
    objects[0]['sha256'] = '0' * 64
    events = bind(monkeypatch, objects)
    with pytest.raises(ArtifactIntegrityError, match='content_integrity_failed'):
        retention.purge_workspace_assets(artifact_store=store, site_id='site-a', limit=1)
    assert store._path(objects[0]['object_key']).exists()
    assert not any(e[0] == 'sql' and 'complete_workspace' in e[1] for e in events)
