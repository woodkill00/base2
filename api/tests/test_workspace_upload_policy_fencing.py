"""Upload admission/private IO precedes policy locks; final authority is live."""

import hashlib
from contextlib import contextmanager
from types import SimpleNamespace
from uuid import UUID

import pytest
from api.repositories import content_workspace as repository
from api.security.content_workspace import CursorCodec


@pytest.mark.parametrize(
    'case',
    [
        'pending',
        'same_grant_completed',
        'expired',
        'replaced',
        'deleted',
        'owner_revoked',
        'invalid_grant',
        'missing',
        'integrity',
        'already_deleted',
    ],
)
def test_upload_final_fence_never_binds_expired_replaced_or_revoked_result(monkeypatch, case):
    asset = UUID(int=7104)
    actor = 'user:' + str(UUID(int=11))
    content = (
        b'\x89PNG\r\n\x1a\n'
        + (13).to_bytes(4, 'big')
        + b'IHDR'
        + (1).to_bytes(4, 'big')
        + (1).to_bytes(4, 'big')
        + b'\x08\x06\x00\x00\x00\x00\x00\x00fixture'
    )
    digest = hashlib.sha256(content).hexdigest()
    row = (asset, 'safe.png', 'image/png', len(content), digest, 'pending', 1, 1)
    if case == 'integrity':
        row = (*row[:3], len(content) + 1, *row[4:])
    if case == 'already_deleted':
        row = (*row[:5], 'deleted', 1, 1)
    current = row
    if case == 'same_grant_completed':
        current = (*row[:5], 'quarantined', 1, 1)
    if case == 'replaced':
        current = (*row[:6], 2, 2)
    if case == 'deleted':
        current = (*row[:5], 'deleted', 1, 1)
    active = []
    calls = []
    times = [1000, 1400 if case == 'expired' else 1000]
    monkeypatch.setattr('api.security.content_workspace.time.time', lambda: 1000)
    monkeypatch.setattr(repository.settings, 'TOKEN_PEPPER', 'synthetic-test-upload-pepper')

    def member(_cur, **kwargs):
        if case == 'owner_revoked' and kwargs.get('lock'):
            raise PermissionError('workspace_policy_forbidden')
        return {'role': 'editor'}

    monkeypatch.setattr(repository.policy_repo, 'member', member)
    responses = iter([None if case == 'missing' else row, current, (times[1],), (asset,)])

    class Cursor:
        sql = ''

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def execute(self, sql, params=()):
            assert active, 'database used after transaction closed'
            self.sql = ' '.join(sql.split())
            calls.append((self.sql, params))

        def fetchone(self):
            return next(responses)

    cur = Cursor()

    class Connection:
        commits = 0

        def cursor(self):
            return cur

        def commit(self):
            self.commits += 1

        def rollback(self):
            pass

    conn = Connection()

    @contextmanager
    def db(*, tenant_id):
        assert tenant_id == 'site-a'
        active.append(True)
        try:
            yield conn
        finally:
            active.pop()

    monkeypatch.setattr(repository, 'db_conn', db)
    puts = []

    class Store:
        def put(self, **kwargs):
            assert not active, 'private IO held database transaction'
            puts.append(kwargs)
            return SimpleNamespace(
                object_key=f'media/site-a/{asset}.bin', sha256=digest, byte_size=len(content)
            )

    scope = {
        'site': 'site-a',
        'owner': actor,
        'asset': str(asset),
        'sha256': digest,
        'bytes': row[3],
        'purpose': 'asset-upload',
    }
    grant = CursorCodec('synthetic-test-upload-pepper', ttl_seconds=300).encode(
        scope=scope, position={'assetId': str(asset)}
    )

    if case == 'invalid_grant':
        grant = 'invalid-grant-value'

    def complete():
        return repository.PostgresContentWorkspaceRepository().complete_asset_upload(
            site_id='site-a',
            asset_id=asset,
            owner_ref=actor,
            upload_grant=grant,
            content=content,
            artifact_store=Store(),
        )

    if case in {'pending', 'same_grant_completed'}:
        assert complete()['replayed'] == (case == 'same_grant_completed')
        assert conn.commits == 1
    else:
        with pytest.raises(PermissionError if case == 'owner_revoked' else ValueError):
            complete()
        assert conn.commits == 0
        assert not any(sql.startswith('UPDATE') for sql, _ in calls)
    assert len(puts) == (
        0 if case in {'invalid_grant', 'missing', 'integrity', 'already_deleted'} else 1
    )  # At most one exact private key; never unsafe orphan unlink.
    locks = [i for i, (sql, _) in enumerate(calls) if 'FOR UPDATE' in sql]
    if not puts:
        assert not any('pg_advisory_xact_lock' in sql for sql, _ in calls)
        return
    global_lock = next(i for i, (sql, _) in enumerate(calls) if 'pg_advisory_xact_lock' in sql)
    assert not locks or global_lock < locks[0]
    if case == 'expired':
        assert next(i for i, (sql, _) in enumerate(calls) if 'clock_timestamp' in sql) > locks[0]
