"""Disposable PostgreSQL retention authority and frozen-parent race obligations."""

import os
from contextlib import contextmanager
from uuid import uuid4

import pytest

pytestmark = pytest.mark.integration


@contextmanager
def connection(role, site, *, isolation=None):
    import psycopg2

    conn = psycopg2.connect(
        host=os.environ['DB_HOST'],
        port=os.environ.get('DB_PORT', '5432'),
        dbname=os.environ['DB_NAME'],
        user=os.environ[role + '_DB_USER'],
        password=os.environ[role + '_DB_PASSWORD'],
    )
    try:
        if isolation:
            conn.set_session(isolation_level=isolation)
        with conn.cursor() as cur:
            cur.execute("SELECT set_config('app.tenant_id',%s,true)", (site,))
            yield conn, cur
    finally:
        conn.rollback()
        conn.close()


def asset(f, *, age=31, key=None):
    identity = uuid4()
    f['execute'](
        """INSERT INTO sitecontent_mediaasset
      (id,site_id,storage_key,original_name,media_type,byte_size,sha256,status,
       owner_ref,attribution,metadata,visibility,lock_version,current_object_version,
       authorization_epoch,deleted_at,retention_until,created_at,updated_at)
      VALUES(%s,%s,%s,'fixture.txt','text/plain',1,%s,'deleted','system:test','','{}','private',
       1,1,1,NOW()-(%s*INTERVAL '1 day'),NOW()-INTERVAL '1 day',NOW(),NOW())""",
        (str(identity), f['site_id'], key or f"media/{f['site_id']}/{identity}.bin", 'a' * 64, age),
    )
    return str(identity)


def claim(f, identity):
    with connection('WORKSPACE_WORKER', f['site_id']) as (conn, cur):
        cur.execute(
            'SELECT * FROM base2_claim_workspace_asset_purge(%s,%s)', (f['site_id'], identity)
        )
        result = cur.fetchone()
        conn.commit()
        return result


def test_claim_is_committed_immutable_and_completion_is_retry_safe(workspace_policy_fixture):
    import psycopg2

    f = workspace_policy_fixture
    identity = asset(f)
    f['execute'](
        """UPDATE sitecontent_mediaasset SET original_name='private-fixture.txt',
      owner_ref='user:fixture',attribution='private-fixture',metadata='{"private":"fixture"}'
      WHERE id=%s""",
        (identity,),
    )
    plan, objects = claim(f, identity)
    assert len(objects) == 1 and objects[0]['object_id'] == identity
    assert claim(f, identity) == (plan, objects)
    assert (
        f['execute']('SELECT status FROM sitecontent_mediaasset WHERE id=%s', (identity,))[0][0]
        == 'purge_planned'
    )
    mutations = [
        ("UPDATE sitecontent_mediaasset SET status='ready' WHERE id=%s", (identity,)),
        ("UPDATE sitecontent_mediaasset SET storage_key='different' WHERE id=%s", (identity,)),
        ('UPDATE sitecontent_mediaasset SET current_object_version=2 WHERE id=%s', (identity,)),
        ('DELETE FROM sitecontent_mediaasset WHERE id=%s', (identity,)),
        ("UPDATE sitecontent_mediapurgeplan SET object_manifest='[]' WHERE id=%s", (str(plan),)),
        ('DELETE FROM sitecontent_mediapurgeplan WHERE id=%s', (str(plan),)),
        (
            """INSERT INTO sitecontent_assetbinding
          (id,site_id,record_id,asset_id,field_key,"order",alt_text,caption,credit,created_at,updated_at)
          VALUES(%s,%s,%s,%s,'fixture',0,'','','',NOW(),NOW())""",
            (str(uuid4()), f['site_id'], str(f['record_id']), identity),
        ),
        (
            """INSERT INTO sitecontent_mediaretentionhold
          (id,site_id,asset_id,reason_code,owner_ref,active,created_at,updated_at)
          VALUES(%s,%s,%s,'fixture','system:test',true,NOW(),NOW())""",
            (str(uuid4()), f['site_id'], identity),
        ),
    ]
    # Raw owner writes hit the same guards as native ORM/runtime mutation paths.
    for sql, params in mutations:
        with pytest.raises(psycopg2.Error, match='content_retention_intent_immutable'):
            f['execute'](sql, params)
    with connection('WORKSPACE_WORKER', f['site_id']) as (conn, cur):
        cur.execute(
            'SELECT base2_complete_workspace_asset_purge(%s,%s,%s)',
            (f['site_id'], str(plan), 'b' * 64),
        )
        assert cur.fetchone() == (True,)
        conn.commit()
    with connection('WORKSPACE_WORKER', f['site_id']) as (_, cur):
        cur.execute(
            'SELECT base2_complete_workspace_asset_purge(%s,%s,%s)',
            (f['site_id'], str(plan), 'b' * 64),
        )
        assert cur.fetchone() == (False,)
    assert (
        f['execute']('SELECT status FROM sitecontent_mediaasset WHERE id=%s', (identity,))[0][0]
        == 'purged'
    )
    assert (
        f['execute'](
            "SELECT count(*) FROM sitecontent_workspaceauditevent WHERE object_ref=%s AND action='content.asset_hard_delete'",
            (identity,),
        )[0][0]
        == 1
    )
    assert f['execute']('SELECT count(*) FROM public.base2_workspace_purge_capability')[0][0] == 0
    assert f['execute'](
        'SELECT original_name,owner_ref,attribution,metadata FROM sitecontent_mediaasset WHERE id=%s',
        (identity,),
    )[0] == ('purged', 'system:retention', '', {})


@pytest.mark.parametrize(
    'role', ['WORKSPACE', 'API_RUNTIME', 'RUNTIME_WORKER', 'DATA_RIGHTS_WORKER', 'EMAIL_WORKER']
)
def test_runtime_cannot_forge_private_authority_or_claim(workspace_policy_fixture, role):
    import psycopg2

    f = workspace_policy_fixture
    identity = asset(f)
    for sql, params in [
        ('SELECT * FROM base2_workspace_purge_proof', ()),
        ('SELECT * FROM base2_workspace_purge_capability', ()),
        ('SELECT * FROM base2_claim_workspace_asset_purge(%s,%s)', (f['site_id'], identity)),
        (
            'SELECT base2_complete_workspace_asset_purge(%s,%s,%s)',
            (f['site_id'], str(uuid4()), 'b' * 64),
        ),
    ]:
        with connection(role, f['site_id']) as (_, cur), pytest.raises(psycopg2.Error):
            cur.execute(sql, params)


def test_recovery_floor_null_evidence_remote_key_and_tenant_fences(workspace_policy_fixture):
    import psycopg2

    f = workspace_policy_fixture
    young = asset(f, age=29)
    assert claim(f, young) is None
    unknown = asset(f, age=None)
    with pytest.raises(psycopg2.Error, match='content_retention_recovery_evidence_missing'):
        claim(f, unknown)
    remote = asset(f, key='unsupported/remote/version::v1')
    with pytest.raises(psycopg2.Error, match='content_retention_storage_unsupported'):
        claim(f, remote)
    good = asset(f)
    with (
        connection('WORKSPACE_WORKER', 'foreign-site') as (_, cur),
        pytest.raises(psycopg2.Error, match='content_retention_role_required'),
    ):
        cur.execute('SELECT * FROM base2_claim_workspace_asset_purge(%s,%s)', (f['site_id'], good))
    assert (
        f['execute'](
            'SELECT count(*) FROM base2_workspace_purge_proof WHERE asset_id=ANY(%s::uuid[])',
            ([young, unknown, remote, good],),
        )[0][0]
        == 0
    )


def test_user_created_plan_and_status_do_not_authorize_deletion(workspace_policy_fixture):
    import psycopg2

    f = workspace_policy_fixture
    identity = asset(f)
    plan = str(uuid4())
    f['execute'](
        """INSERT INTO sitecontent_mediapurgeplan
      (id,site_id,asset_id,requested_by,reason_code,expected_version,object_manifest,reference_preview,
       status,scheduled_at,result_sha256,created_at,updated_at)
      VALUES(%s,%s,%s,'system:retention','workspace_retention',1,'[]','[]','scheduled',NOW(),'',NOW(),NOW())""",
        (plan, f['site_id'], identity),
    )
    f['execute'](
        "UPDATE sitecontent_mediaasset SET status='purge_planned' WHERE id=%s", (identity,)
    )
    assert claim(f, identity) is None
    with (
        connection('WORKSPACE_WORKER', f['site_id']) as (_, cur),
        pytest.raises(psycopg2.Error, match='content_retention_plan_invalid'),
    ):
        cur.execute(
            'SELECT base2_complete_workspace_asset_purge(%s,%s,%s)',
            (f['site_id'], plan, 'a' * 64),
        )


def test_uncommitted_claim_rolls_back_without_creating_execution_authority(
    workspace_policy_fixture,
):
    f = workspace_policy_fixture
    identity = asset(f)
    with connection('WORKSPACE_WORKER', f['site_id']) as (_, cur):
        cur.execute(
            'SELECT * FROM base2_claim_workspace_asset_purge(%s,%s)', (f['site_id'], identity)
        )
        assert cur.fetchone()
    assert (
        f['execute']('SELECT status FROM sitecontent_mediaasset WHERE id=%s', (identity,))[0][0]
        == 'deleted'
    )
    assert (
        f['execute'](
            'SELECT count(*) FROM base2_workspace_purge_proof WHERE asset_id=%s', (identity,)
        )[0][0]
        == 0
    )


def test_scoped_audit_retains_claim_organization_after_replacement(workspace_policy_fixture):
    f = workspace_policy_fixture
    identity = asset(f)
    original_org = f['execute'](
        'SELECT id FROM api_identity_organizations WHERE tenant_id=%s', (f['site_id'],)
    )[0][0]
    plan, _ = claim(f, identity)
    f['execute']('DELETE FROM api_identity_organizations WHERE id=%s', (str(original_org),))
    replacement = str(uuid4())
    f['execute'](
        'INSERT INTO api_identity_organizations(id,tenant_id,name) VALUES(%s,%s,%s)',
        (replacement, f['site_id'], 'Replacement synthetic scope'),
    )
    with connection('WORKSPACE_WORKER', f['site_id']) as (conn, cur):
        cur.execute(
            'SELECT base2_complete_workspace_asset_purge(%s,%s,%s)',
            (f['site_id'], str(plan), 'c' * 64),
        )
        assert cur.fetchone() == (True,)
        conn.commit()
    user, metadata = f['execute'](
        'SELECT user_id,metadata_json FROM api_auth_audit_events '
        "WHERE action='content.asset_hard_delete' AND metadata_json->>'asset_id'=%s",
        (identity,),
    )[0]
    assert user is None
    assert metadata == dict(
        tenant_id=f['site_id'],
        organization_id=str(original_org),
        asset_id=identity,
        count=1,
        actor_ref='system:retention',
    )
    assert metadata['organization_id'] != replacement


def test_unmapped_organization_blocks_before_claim(workspace_policy_fixture):
    import psycopg2

    f = workspace_policy_fixture
    identity = asset(f)
    f['execute']('DELETE FROM api_identity_organizations WHERE tenant_id=%s', (f['site_id'],))
    with pytest.raises(psycopg2.Error, match='content_retention_organization_unavailable'):
        claim(f, identity)
    assert (
        f['execute']('SELECT status FROM sitecontent_mediaasset WHERE id=%s', (identity,))[0][0]
        == 'deleted'
    )


def test_new_reference_cannot_cross_uncommitted_claim(workspace_policy_fixture):
    import psycopg2

    f = workspace_policy_fixture
    identity = asset(f)
    statement = """INSERT INTO sitecontent_mediaretentionhold
      (id,site_id,asset_id,reason_code,owner_ref,active,created_at,updated_at)
      VALUES(%s,%s,%s,'fixture','system:test',true,NOW(),NOW())"""
    params = (str(uuid4()), f['site_id'], identity)
    with connection('WORKSPACE_WORKER', f['site_id']) as (claim_conn, claim_cur):
        claim_cur.execute(
            'SELECT * FROM base2_claim_workspace_asset_purge(%s,%s)', (f['site_id'], identity)
        )
        assert claim_cur.fetchone()
        with connection('WORKSPACE', f['site_id']) as (_, ref_cur):
            ref_cur.execute("SET LOCAL lock_timeout='100ms'")
            with pytest.raises(psycopg2.errors.LockNotAvailable):
                ref_cur.execute(statement, params)
        claim_conn.commit()
    with (
        connection('WORKSPACE', f['site_id']) as (_, ref_cur),
        pytest.raises(psycopg2.Error, match='content_retention_intent_immutable'),
    ):
        ref_cur.execute(statement, params)
    assert (
        f['execute'](
            'SELECT count(*) FROM sitecontent_mediaretentionhold WHERE asset_id=%s', (identity,)
        )[0][0]
        == 0
    )


def test_partial_local_io_leaves_frozen_intent_and_retry_completes(
    workspace_policy_fixture, tmp_path, monkeypatch
):
    import psycopg2
    from api.services import workspace_retention_assets as retention
    from api.services.content_workspace_storage import PrivateArtifactStore

    f = workspace_policy_fixture
    identity = asset(f)
    store = PrivateArtifactStore(tmp_path / 'retention-fixture', key=b'f' * 32)
    original = store.put(
        namespace='media', site_id=f['site_id'], object_id=identity, content=b'original'
    )
    variant = store.put(
        namespace='variants', site_id=f['site_id'], object_id=identity + '-safe', content=b'variant'
    )
    f['execute'](
        'UPDATE sitecontent_mediaasset SET sha256=%s,byte_size=%s WHERE id=%s',
        (original.sha256, original.byte_size, identity),
    )
    f['execute'](
        """INSERT INTO sitecontent_mediavariant
      (id,asset_id,name,storage_key,media_type,byte_size,sha256,recipe_id,recipe_version,
       source_sha256,processor_ref,inline_safe,created_at)
      VALUES(%s,%s,'safe',%s,'text/plain',%s,%s,'safe',1,%s,'test',true,NOW())""",
        (
            str(uuid4()),
            identity,
            variant.object_key,
            variant.byte_size,
            variant.sha256,
            original.sha256,
        ),
    )

    @contextmanager
    def worker_connection(**kwargs):
        with connection('WORKSPACE_WORKER', kwargs['tenant_id']) as (conn, _):
            yield conn

    monkeypatch.setattr(retention, 'db_conn', worker_connection)
    delete = store.delete

    def fail_original(**kwargs):
        if kwargs['namespace'] == 'media':
            raise OSError('synthetic local IO failure')
        return delete(**kwargs)

    monkeypatch.setattr(store, 'delete', fail_original)
    with pytest.raises(OSError, match='synthetic local IO failure'):
        retention.purge_workspace_assets(artifact_store=store, site_id=f['site_id'], limit=1)
    assert (
        f['execute']('SELECT status FROM sitecontent_mediaasset WHERE id=%s', (identity,))[0][0]
        == 'purge_planned'
    )
    with pytest.raises(psycopg2.Error, match='content_retention_intent_immutable'):
        f['execute']("UPDATE sitecontent_mediaasset SET status='ready' WHERE id=%s", (identity,))
    monkeypatch.setattr(store, 'delete', delete)
    assert (
        retention.purge_workspace_assets(artifact_store=store, site_id=f['site_id'], limit=1) == 1
    )
    assert (
        retention.purge_workspace_assets(artifact_store=store, site_id=f['site_id'], limit=1) == 0
    )
    assert (
        f['execute']('SELECT status FROM sitecontent_mediaasset WHERE id=%s', (identity,))[0][0]
        == 'purged'
    )


def test_runtime_cannot_backdate_deletion_clock_or_shorten_later_retention(
    workspace_policy_fixture,
):
    import psycopg2

    f = workspace_policy_fixture
    identity = asset(f)
    historical = f['execute'](
        'SELECT deleted_at FROM sitecontent_mediaasset WHERE id=%s', (identity,)
    )[0][0]
    for sql, error in [
        (
            "UPDATE sitecontent_mediaasset SET deleted_at=NOW()-INTERVAL '90 days' WHERE id=%s",
            'content_retention_deletion_clock_immutable',
        ),
        (
            "UPDATE sitecontent_mediaasset SET retention_until=NOW()-INTERVAL '90 days' WHERE id=%s",
            'content_retention_schedule_cannot_shorten',
        ),
    ]:
        with (
            connection('WORKSPACE', f['site_id']) as (_, cur),
            pytest.raises(psycopg2.Error, match=error),
        ):
            cur.execute(sql, (identity,))
    assert (
        f['execute']('SELECT deleted_at FROM sitecontent_mediaasset WHERE id=%s', (identity,))[0][0]
        == historical
    )
    # Owner-created historical migration evidence remains usable, not silently rewritten.
    assert claim(f, identity)


def test_runtime_restore_then_redelete_starts_new_clock(workspace_policy_fixture):
    f = workspace_policy_fixture
    identity = asset(f)
    with connection('WORKSPACE', f['site_id']) as (conn, cur):
        cur.execute("UPDATE sitecontent_mediaasset SET status='ready' WHERE id=%s", (identity,))
        cur.execute(
            """UPDATE sitecontent_mediaasset SET status='deleted',
          deleted_at=NOW()-INTERVAL '90 days' WHERE id=%s
          RETURNING deleted_at>=statement_timestamp(),retention_until<NOW()""",
            (identity,),
        )
        assert cur.fetchone() == (True, True)
        conn.commit()
    assert claim(f, identity) is None
    assert (
        f['execute'](
            'SELECT count(*) FROM base2_workspace_purge_proof WHERE asset_id=%s', (identity,)
        )[0][0]
        == 0
    )


def test_reference_committed_first_blocks_claim_without_lock_inversion(workspace_policy_fixture):
    import psycopg2

    f = workspace_policy_fixture
    identity = asset(f)
    with connection('WORKSPACE', f['site_id']) as (hold_conn, hold_cur):
        hold_cur.execute(
            """INSERT INTO sitecontent_mediaretentionhold
          (id,site_id,asset_id,reason_code,owner_ref,active,created_at,updated_at)
          VALUES(%s,%s,%s,'fixture','system:test',true,NOW(),NOW())""",
            (str(uuid4()), f['site_id'], identity),
        )
        with connection('WORKSPACE_WORKER', f['site_id']) as (_, claim_cur):
            claim_cur.execute("SET LOCAL lock_timeout='100ms'")
            with pytest.raises(psycopg2.errors.LockNotAvailable):
                claim_cur.execute(
                    'SELECT * FROM base2_claim_workspace_asset_purge(%s,%s)',
                    (f['site_id'], identity),
                )
        hold_conn.commit()
    assert claim(f, identity) is None
    assert (
        f['execute']('SELECT status FROM sitecontent_mediaasset WHERE id=%s', (identity,))[0][0]
        == 'deleted'
    )


def test_moving_reference_to_frozen_parent_is_atomic(workspace_policy_fixture):
    import psycopg2

    f = workspace_policy_fixture
    source, target, hold = asset(f), asset(f), str(uuid4())
    f['execute'](
        """INSERT INTO sitecontent_mediaretentionhold
      (id,site_id,asset_id,reason_code,owner_ref,active,created_at,updated_at)
      VALUES(%s,%s,%s,'fixture','system:test',true,NOW(),NOW())""",
        (hold, f['site_id'], source),
    )
    assert claim(f, target)
    with pytest.raises(psycopg2.Error, match='content_retention_intent_immutable'):
        f['execute'](
            'UPDATE sitecontent_mediaretentionhold SET asset_id=%s WHERE id=%s', (target, hold)
        )
    assert (
        str(
            f['execute'](
                'SELECT asset_id FROM sitecontent_mediaretentionhold WHERE id=%s', (hold,)
            )[0][0]
        )
        == source
    )


@pytest.mark.parametrize('isolation', ['REPEATABLE READ', 'SERIALIZABLE'])
def test_unsupported_isolation_blocks_claim_and_reference_mutation(
    workspace_policy_fixture, isolation
):
    import psycopg2

    f = workspace_policy_fixture
    identity = asset(f)
    with (
        connection('WORKSPACE_WORKER', f['site_id'], isolation=isolation) as (_, cur),
        pytest.raises(psycopg2.Error, match='content_retention_isolation_unsupported'),
    ):
        cur.execute(
            'SELECT * FROM base2_claim_workspace_asset_purge(%s,%s)', (f['site_id'], identity)
        )
    with (
        connection('WORKSPACE', f['site_id'], isolation=isolation) as (_, cur),
        pytest.raises(psycopg2.Error, match='content_retention_isolation_unsupported'),
    ):
        cur.execute(
            """INSERT INTO sitecontent_mediaretentionhold
          (id,site_id,asset_id,reason_code,owner_ref,active,created_at,updated_at)
          VALUES(%s,%s,%s,'fixture','system:test',true,NOW(),NOW())""",
            (str(uuid4()), f['site_id'], identity),
        )


def test_nonsemantic_bookkeeping_does_not_wait_for_parent_lock(workspace_policy_fixture):
    f = workspace_policy_fixture
    identity, hold = asset(f), str(uuid4())
    f['execute'](
        """INSERT INTO sitecontent_mediaretentionhold
      (id,site_id,asset_id,reason_code,owner_ref,active,created_at,updated_at)
      VALUES(%s,%s,%s,'fixture','system:test',true,NOW(),NOW())""",
        (hold, f['site_id'], identity),
    )
    with connection('WORKSPACE_WORKER', f['site_id']) as (_, claim_cur):
        claim_cur.execute(
            'SELECT * FROM base2_claim_workspace_asset_purge(%s,%s)', (f['site_id'], identity)
        )
        assert claim_cur.fetchone() is None  # Parent lock remains held until transaction exits.
        with connection('WORKSPACE', f['site_id']) as (ref_conn, ref_cur):
            ref_cur.execute("SET LOCAL lock_timeout='100ms'")
            ref_cur.execute(
                "UPDATE sitecontent_mediaretentionhold SET reason_code='fixture_changed' WHERE id=%s",
                (hold,),
            )
            ref_conn.commit()


def test_proof_bound_plan_rejects_before_waiting_for_parent(workspace_policy_fixture):
    import psycopg2

    f = workspace_policy_fixture
    identity = asset(f)
    plan, _ = claim(f, identity)
    with connection('WORKSPACE_WORKER', f['site_id']) as (_, asset_cur):
        asset_cur.execute(
            'SELECT id FROM sitecontent_mediaasset WHERE id=%s FOR UPDATE', (identity,)
        )
        with connection('WORKSPACE', f['site_id']) as (_, plan_cur):
            plan_cur.execute("SET LOCAL lock_timeout='100ms'")
            with pytest.raises(psycopg2.Error, match='content_retention_intent_immutable'):
                plan_cur.execute(
                    "UPDATE sitecontent_mediapurgeplan SET status='cancelled' WHERE id=%s",
                    (str(plan),),
                )


def test_governed_metadata_history_blocks_claim_and_new_history_is_fenced(workspace_policy_fixture):
    import psycopg2

    f = workspace_policy_fixture
    historical, planned = asset(f), asset(f)
    statement = """INSERT INTO sitecontent_mediametadatarevision
      (id,site_id,asset_id,revision,locale,alt_text,decorative,caption,transcript,credit,
       license_code,ordering_hint,actor_ref,created_at,updated_at)
      VALUES(%s,%s,%s,1,'en','',false,'','synthetic private transcript','','',0,
       'system:test',NOW(),NOW())"""
    f['execute'](statement, (str(uuid4()), f['site_id'], historical))
    with pytest.raises(psycopg2.Error, match='content_retention_storage_unsupported'):
        claim(f, historical)
    assert claim(f, planned)
    with pytest.raises(psycopg2.Error, match='content_retention_intent_immutable'):
        f['execute'](statement, (str(uuid4()), f['site_id'], planned))
    assert (
        f['execute'](
            'SELECT transcript FROM sitecontent_mediametadatarevision WHERE asset_id=%s',
            (historical,),
        )[0][0]
        == 'synthetic private transcript'
    )
