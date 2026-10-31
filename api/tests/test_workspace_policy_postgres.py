"""Feature124 real-role/native-write regressions, invoked by disposable runner."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier
from uuid import uuid4

import psycopg2
import pytest

from api.db import db_conn, workspace_db_conn, workspace_worker_db_conn
from api.repositories import workspace_policy as policy
from api.services.content_workspace_worker import publish_scheduled_record

pytestmark = pytest.mark.integration


def approve(f):
    return policy.review_action(
        site_id=f['site_id'],
        type_key=f['type_key'],
        record_id=f['record_id'],
        user_id=f['reviewer_id'],
        expected_version=2,
    )


def transition(f, action, version=2, actor=None, when=None):
    return f['repo'].transition_record(
        site_id=f['site_id'],
        type_key=f['type_key'],
        record_id=f['record_id'],
        expected_version=version,
        actor_ref=f"user:{actor or f['reviewer_id']}",
        action=action,
        publish_at=when,
        timezone='UTC' if when else None,
    )


def test_self_approval_direct_publish_and_native_publish_are_denied(workspace_policy_fixture):
    f = workspace_policy_fixture
    f['execute'](
        "UPDATE api_identity_memberships SET role='admin' WHERE user_id=%s", (str(f['creator_id']),)
    )
    with pytest.raises(ValueError, match='independent_reviewer'):
        policy.review_action(
            site_id=f['site_id'],
            type_key=f['type_key'],
            record_id=f['record_id'],
            user_id=f['creator_id'],
            expected_version=2,
        )
    with pytest.raises(ValueError, match='review_required'):
        transition(f, 'publish')
    with pytest.raises(psycopg2.Error):
        f['execute'](
            "UPDATE sitecontent_contentrecord SET state='published' WHERE id=%s",
            (str(f['record_id']),),
        )
    assert (
        f['execute'](
            'SELECT count(*) FROM sitecontent_reviewapproval WHERE record_id=%s',
            (str(f['record_id']),),
        )[0][0]
        == 0
    )


def test_approval_exact_subject_publishes_but_native_semantic_edit_demotes(
    workspace_policy_fixture,
):
    f = workspace_policy_fixture
    approve(f)
    published = transition(f, 'publish')
    assert published['state'] == 'published'
    f['execute'](
        "UPDATE sitecontent_contentrecord SET body='Changed published body' WHERE id=%s",
        (str(f['record_id']),),
    )
    assert (
        f['execute'](
            'SELECT state FROM sitecontent_contentrecord WHERE id=%s', (str(f['record_id']),)
        )[0][0]
        == 'draft'
    )
    subject = f['execute'](
        'SELECT semantic_generation,submitter_id FROM sitecontent_reviewsubject WHERE record_id=%s',
        (str(f['record_id']),),
    )[0]
    assert subject[0] > 1 and subject[1] is None


@pytest.mark.parametrize('assignment', ['definition_id=NULL', "site_id='other-site'"])
def test_managed_record_cannot_escape_visibility_classification(
    workspace_policy_fixture, assignment
):
    f = workspace_policy_fixture
    with pytest.raises(psycopg2.Error):
        f['execute'](
            f'UPDATE sitecontent_contentrecord SET {assignment} WHERE id=%s', (str(f['record_id']),)
        )


def test_public_rls_changes_synchronously_and_never_grants_identity_reads(workspace_policy_fixture):
    f = workspace_policy_fixture
    approve(f)
    transition(f, 'publish')
    with db_conn(tenant_id=f['site_id']) as conn, conn.cursor() as cur:
        cur.execute('SELECT id FROM sitecontent_contentrecord WHERE id=%s', (str(f['record_id']),))
        assert cur.fetchall() == []
    policy.update_policy(
        site_id=f['site_id'],
        user_id=f['reviewer_id'],
        expected_version=1,
        require_review=True,
        public_access='public_allowed',
    )
    with db_conn(tenant_id=f['site_id']) as conn, conn.cursor() as cur:
        cur.execute('SELECT id FROM sitecontent_contentrecord WHERE id=%s', (str(f['record_id']),))
        assert len(cur.fetchall()) == 1
    policy.update_policy(
        site_id=f['site_id'],
        user_id=f['reviewer_id'],
        expected_version=2,
        require_review=True,
        public_access='members_only',
    )
    with db_conn(tenant_id=f['site_id']) as conn, conn.cursor() as cur:
        cur.execute('SELECT id FROM sitecontent_contentrecord WHERE id=%s', (str(f['record_id']),))
        assert cur.fetchall() == []


def test_scheduled_state_preserves_approval_but_revoked_scheduler_blocks(workspace_policy_fixture):
    f = workspace_policy_fixture
    approve(f)
    subject_before = f['execute'](
        'SELECT semantic_revision FROM sitecontent_reviewsubject WHERE record_id=%s',
        (str(f['record_id']),),
    )[0][0]
    scheduled = transition(
        f, 'schedule', actor=f['creator_id'], when=datetime.now(UTC) - timedelta(seconds=1)
    )
    assert scheduled['state'] == 'scheduled'
    assert (
        f['execute'](
            'SELECT semantic_revision FROM sitecontent_reviewsubject WHERE record_id=%s',
            (str(f['record_id']),),
        )[0][0]
        == subject_before
    )
    f['execute'](
        "UPDATE api_identity_memberships SET status='suspended' WHERE user_id=%s",
        (str(f['creator_id']),),
    )
    assert (
        publish_scheduled_record(site_id=f['site_id'], record_id=f['record_id'])
        == 'authorization_required'
    )
    assert (
        f['execute'](
            'SELECT state FROM sitecontent_contentrecord WHERE id=%s', (str(f['record_id']),)
        )[0][0]
        == 'scheduled'
    )


def test_native_schedule_edits_and_future_publish_cannot_bypass_authority(workspace_policy_fixture):
    f = workspace_policy_fixture
    approve(f)
    transition(f, 'schedule', actor=f['creator_id'], when=datetime.now(UTC) + timedelta(days=1))
    for assignment in (
        'publish_at=NOW()',
        "schedule_timezone='Pacific/Auckland'",
        "state='published'",
    ):
        with pytest.raises(psycopg2.Error):
            f['execute'](
                f'UPDATE sitecontent_contentrecord SET {assignment} WHERE id=%s',
                (str(f['record_id']),),
            )
    assert publish_scheduled_record(site_id=f['site_id'], record_id=f['record_id']) == 'not_due'


def test_policy_cas_two_real_sessions_one_winner(workspace_policy_fixture):
    f = workspace_policy_fixture
    gate = Barrier(2, timeout=10)

    def save(value):
        gate.wait()
        return policy.update_policy(
            site_id=f['site_id'],
            user_id=f['reviewer_id'],
            expected_version=1,
            require_review=True,
            public_access=value,
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(save, value) for value in ('public_allowed', 'members_only')]
        results = [future.result(timeout=30) for future in futures]
    assert sum(row is None for row in results) == 1
    assert policy.get_policy(site_id=f['site_id'], user_id=f['reviewer_id'])['version'] == 2


def test_native_creator_rewrite_and_generation_rewind_rejected(workspace_policy_fixture):
    f = workspace_policy_fixture
    for assignment in ('original_creator_id=NULL', 'semantic_generation=0'):
        with pytest.raises(psycopg2.Error):
            f['execute'](
                f'UPDATE sitecontent_reviewsubject SET {assignment} WHERE record_id=%s',
                (str(f['record_id']),),
            )


def test_unknown_subject_requires_explicit_adoption_not_transition(workspace_policy_fixture):
    f = workspace_policy_fixture
    # A native semantic change has no invented human actor and invalidates subject.
    f['execute'](
        "UPDATE sitecontent_contentrecord SET body='Legacy semantic edit' WHERE id=%s",
        (str(f['record_id']),),
    )
    with pytest.raises(ValueError, match='authorship_unknown'):
        transition(f, 'submit_review', actor=f['creator_id'])
    adopted = policy.review_action(
        site_id=f['site_id'],
        type_key=f['type_key'],
        record_id=f['record_id'],
        user_id=f['creator_id'],
        expected_version=2,
        adopt=True,
    )
    assert adopted['state'] == 'draft'
    transition(f, 'submit_review', version=3, actor=f['creator_id'])
    approved = policy.review_action(
        site_id=f['site_id'],
        type_key=f['type_key'],
        record_id=f['record_id'],
        user_id=f['reviewer_id'],
        expected_version=4,
    )
    assert approved['review_status'] == 'approved'


def test_helpers_require_bound_scope_and_do_not_grant_cross_tenant_membership(
    workspace_policy_fixture,
):
    f = workspace_policy_fixture
    with workspace_db_conn(tenant_id=f['site_id']) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM base2_workspace_member('wrong-site',%s,'review',true)",
            (str(f['reviewer_id']),),
        )
        assert cur.fetchall() == []
        cur.execute(
            'SELECT * FROM base2_workspace_member(%s,%s,%s,true)',
            (f['site_id'], str(uuid4()), 'review'),
        )
        assert cur.fetchall() == []
    with workspace_worker_db_conn(
        tenant_id=f['site_id']
    ) as conn, conn.cursor() as cur, pytest.raises(psycopg2.errors.InsufficientPrivilege):
        cur.execute('SELECT email FROM api_auth_users')


def test_return_and_resubmit_unchanged_requires_fresh_approval(workspace_policy_fixture):
    f = workspace_policy_fixture
    approve(f)
    transition(f, 'return_draft', actor=f['creator_id'])
    transition(f, 'submit_review', version=3, actor=f['creator_id'])
    with pytest.raises(ValueError, match='content_review_required'):
        transition(f, 'publish', version=4)
    policy.review_action(
        site_id=f['site_id'],
        type_key=f['type_key'],
        record_id=f['record_id'],
        user_id=f['reviewer_id'],
        expected_version=4,
    )
    assert transition(f, 'publish', version=4)['state'] == 'published'


def test_shared_audit_is_visible_to_exact_org_without_personal_choices(workspace_policy_fixture):
    from api.repositories.identity_admin import admin_overview

    f = workspace_policy_fixture
    approve(f)
    overview = admin_overview(user_id=f['reviewer_id'], tenant_id=f['site_id'])
    events = overview['audit']
    assert {'workspace.policy_updated', 'content.review_requested', 'content.review_approved'} <= {
        item['action'] for item in events
    }
    assert all(item['metadata']['tenant_id'] == f['site_id'] for item in events)
    assert not any('notification' in item['action'] for item in events)


def test_native_media_trigger_tables_invalidate_without_resurrecting_archived(
    workspace_policy_fixture,
):
    f = workspace_policy_fixture
    execute, site = f['execute'], f['site_id']
    asset, binding, variant, obj = (uuid4() for _ in range(4))
    execute(
        """INSERT INTO sitecontent_mediaasset
        (id,site_id,storage_key,original_name,media_type,byte_size,sha256,status,
         owner_ref,attribution,metadata,visibility,lock_version,current_object_version,
         authorization_epoch,created_at,updated_at)
        VALUES (%s,%s,%s,'test.png','image/png',1,%s,'quarantined',
                'system:test','','{}','private',1,1,1,NOW(),NOW())""",
        (str(asset), site, f'media/{site}/{asset}.bin', 'a' * 64),
    )
    execute(
        """INSERT INTO sitecontent_assetbinding
        (id,site_id,record_id,asset_id,field_key,"order",alt_text,caption,credit,created_at,updated_at)
        VALUES(%s,%s,%s,%s,'image',0,'Synthetic','','',NOW(),NOW())""",
        (str(binding), site, str(f['record_id']), str(asset)),
    )
    execute(
        "UPDATE sitecontent_contentrecord SET state='archived' WHERE id=%s", (str(f['record_id']),)
    )
    before = execute(
        'SELECT semantic_generation FROM sitecontent_reviewsubject WHERE record_id=%s',
        (str(f['record_id']),),
    )[0][0]
    execute(
        """INSERT INTO sitecontent_mediavariant
      (id,asset_id,name,storage_key,media_type,byte_size,sha256,recipe_id,recipe_version,
       source_sha256,processor_ref,inline_safe,created_at)
      VALUES(%s,%s,'safe',%s,'image/png',1,%s,'safe',1,%s,'test',true,NOW())""",
        (str(variant), str(asset), f'variants/{site}/{asset}-safe.bin', 'b' * 64, 'a' * 64),
    )
    with pytest.raises(psycopg2.Error, match='scope_immutable'):
        execute(
            'UPDATE sitecontent_mediavariant SET asset_id=%s WHERE id=%s',
            (str(uuid4()), str(variant)),
        )
    with pytest.raises(psycopg2.Error, match='scope_immutable'):
        execute(
            "UPDATE sitecontent_mediaasset SET site_id='foreign-site' WHERE id=%s", (str(asset),)
        )
    execute('UPDATE sitecontent_mediavariant SET sha256=%s WHERE id=%s', ('c' * 64, str(variant)))
    execute('DELETE FROM sitecontent_mediavariant WHERE id=%s', (str(variant),))
    execute(
        """INSERT INTO sitecontent_mediaobjectversion
      (id,site_id,asset_id,version,storage_key,sha256,byte_size,detected_type,
       inspection_state,scanner_ref,created_at,updated_at)
      VALUES(%s,%s,%s,1,%s,%s,1,'image/png','uploaded','',NOW(),NOW())""",
        (str(obj), site, str(asset), f'media/{site}/{asset}.bin', 'a' * 64),
    )
    execute(
        "UPDATE sitecontent_mediaobjectversion SET inspection_state='failed' WHERE id=%s",
        (str(obj),),
    )
    execute('DELETE FROM sitecontent_mediaobjectversion WHERE id=%s', (str(obj),))
    execute('UPDATE sitecontent_mediaasset SET sha256=%s WHERE id=%s', ('d' * 64, str(asset)))
    execute("UPDATE sitecontent_assetbinding SET caption='changed' WHERE id=%s", (str(binding),))
    after = execute(
        'SELECT semantic_generation,semantic_author_id FROM sitecontent_reviewsubject WHERE record_id=%s',
        (str(f['record_id']),),
    )[0]
    assert after[0] > before and after[1] is None
    assert (
        execute('SELECT state FROM sitecontent_contentrecord WHERE id=%s', (str(f['record_id']),))[
            0
        ][0]
        == 'archived'
    )
    with pytest.raises(psycopg2.Error, match='scope_invalid'):
        execute(
            "UPDATE sitecontent_assetbinding SET site_id='foreign-site' WHERE id=%s",
            (str(binding),),
        )
    execute('DELETE FROM sitecontent_assetbinding WHERE id=%s', (str(binding),))
    execute('DELETE FROM sitecontent_mediaasset WHERE id=%s', (str(asset),))


def test_notification_header_and_choices_raw_runtime_rls(workspace_policy_fixture):
    f = workspace_policy_fixture
    for tenant in ('foreign-tenant', None):
        with db_conn(tenant_id=tenant) as conn, conn.cursor() as cur:
            cur.execute('SELECT rolsuper,rolbypassrls FROM pg_roles WHERE rolname=current_user')
            assert cur.fetchone() == (False, False)
            for table in ('api_notification_preference_sets', 'api_notification_preferences'):
                cur.execute(
                    f'SELECT count(*) FROM {table} WHERE user_id=%s', (str(f['reviewer_id']),)
                )
                assert cur.fetchone()[0] == 0
                cur.execute('SAVEPOINT denied_update')
                if table == 'api_notification_preferences':
                    # Choices intentionally use replace DELETE+INSERT, not UPDATE grants.
                    with pytest.raises(psycopg2.errors.InsufficientPrivilege):
                        cur.execute(
                            f'UPDATE {table} SET tenant_id=tenant_id WHERE user_id=%s',
                            (str(f['reviewer_id']),),
                        )
                    cur.execute('ROLLBACK TO SAVEPOINT denied_update')
                else:
                    cur.execute(
                        f'UPDATE {table} SET tenant_id=tenant_id WHERE user_id=%s',
                        (str(f['reviewer_id']),),
                    )
                    assert cur.rowcount == 0
                cur.execute('RELEASE SAVEPOINT denied_update')
            with pytest.raises(psycopg2.errors.InsufficientPrivilege):
                cur.execute(
                    'INSERT INTO api_notification_preference_sets(id,user_id,tenant_id) VALUES(%s,%s,%s)',
                    (str(uuid4()), str(f['second_reviewer_id']), f['site_id']),
                )
            conn.rollback()
    with db_conn(tenant_id=f['site_id']) as conn, conn.cursor() as cur:
        with pytest.raises(psycopg2.errors.InsufficientPrivilege):
            cur.execute(
                "UPDATE api_notification_preference_sets SET tenant_id='foreign-tenant' WHERE user_id=%s",
                (str(f['reviewer_id']),),
            )
        conn.rollback()


def test_definition_version_clone_retirement_and_raw_immutability(workspace_policy_fixture):
    f = workspace_policy_fixture
    definition = f['repo'].create_definition(
        site_id=f['site_id'],
        actor_ref=f"user:{f['reviewer_id']}",
        payload={
            'type_key': 'article',
            'name': 'Article two',
            'fields': [{'field_key': 'note', 'label': 'Note', 'field_kind': 'short_text'}],
        },
    )
    definition_id = f['execute'](
        'SELECT id FROM sitecontent_contenttypedefinition WHERE site_id=%s AND version=%s',
        (f['site_id'], definition['version']),
    )[0][0]
    field = f['execute'](
        'SELECT id FROM sitecontent_contentfielddefinition WHERE definition_id=%s',
        (str(definition_id),),
    )[0][0]
    f['repo'].publish_definition(
        site_id=f['site_id'],
        type_key='article',
        version=definition['version'],
        expected_lock_version=definition['lockVersion'],
        confirm_lossy=False,
        actor_ref=f"user:{f['reviewer_id']}",
    )
    for sql, params in [
        (
            'UPDATE sitecontent_contentfielddefinition SET read_permission=%s WHERE id=%s',
            ('content.read', str(field)),
        ),
        ('DELETE FROM sitecontent_contentfielddefinition WHERE id=%s', (str(field),)),
        (
            "UPDATE sitecontent_contenttypedefinition SET status='draft' WHERE id=%s",
            (str(definition_id),),
        ),
        (
            "UPDATE sitecontent_contenttypedefinition SET name='Changed' WHERE id=%s",
            (str(definition_id),),
        ),
        ('DELETE FROM sitecontent_contenttypedefinition WHERE id=%s', (str(definition_id),)),
    ]:
        with pytest.raises(psycopg2.Error, match='published_definition_immutable'):
            f['execute'](sql, params)
    retired = f['repo'].retire_definition(
        site_id=f['site_id'],
        type_key='article',
        version=definition['version'],
        expected_lock_version=2,
        actor_ref=f"user:{f['reviewer_id']}",
    )
    assert retired['status'] == 'retired'
    with pytest.raises(psycopg2.Error, match='published_definition_immutable'):
        f['execute'](
            "UPDATE sitecontent_contenttypedefinition SET status='draft' WHERE id=%s",
            (str(definition_id),),
        )


def test_role_mutation_waits_for_effect_lock_before_membership_rows(
    workspace_policy_fixture, monkeypatch
):
    from contextlib import contextmanager
    from threading import Event
    from time import monotonic, sleep
    from api.repositories import identity_admin

    f = workspace_policy_fixture
    org, stamp = f['execute'](
        'SELECT organization_id,updated_at FROM api_identity_memberships WHERE user_id=%s',
        (str(f['reviewer_id']),),
    )[0]
    original = identity_admin.db_conn
    started = Event()
    pid = []

    @contextmanager
    def observed(**kwargs):
        with original(**kwargs) as conn:
            with conn.cursor() as cur:
                cur.execute("SET LOCAL statement_timeout='10s'")
                cur.execute('SELECT pg_backend_pid()')
                pid.append(cur.fetchone()[0])
            started.set()
            yield conn

    monkeypatch.setattr(identity_admin, 'db_conn', observed)
    with workspace_db_conn(tenant_id=f['site_id']) as holder, holder.cursor() as cur:
        policy.begin_effect(cur)
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(
                identity_admin.update_member_role,
                tenant_id=f['site_id'],
                organization_id=org,
                actor_id=f['second_reviewer_id'],
                member_id=f['reviewer_id'],
                new_role='viewer',
                expected_updated_at=stamp,
            )
            try:
                assert started.wait(5)
                deadline = monotonic() + 5
                while not f['execute'](
                    "SELECT count(*) FROM pg_locks WHERE pid=%s AND locktype='advisory' AND NOT granted",
                    (pid[0],),
                )[0][0]:
                    assert monotonic() < deadline, 'role update did not wait for advisory lock'
                    sleep(0.01)
                # If the mutator had locked this row first, this would fail immediately.
                cur.execute("SET LOCAL lock_timeout='100ms'")
                cur.execute(
                    "SELECT * FROM base2_workspace_member(%s,%s,'review',true)",
                    (f['site_id'], str(f['reviewer_id'])),
                )
                assert cur.fetchone() is not None
            finally:
                holder.rollback()
            assert future.result(timeout=5) is True


def test_same_upload_grant_concurrency_binds_once_without_holding_io_lock(
    workspace_policy_fixture, tmp_path, monkeypatch
):
    import hashlib
    from uuid import UUID
    from api.services.content_workspace_storage import PrivateArtifactStore
    from api.settings import settings

    monkeypatch.setattr(settings, 'TOKEN_PEPPER', 'synthetic-private-grant-key-124')
    f = workspace_policy_fixture
    content = (
        b'\x89PNG\r\n\x1a\n'
        + (13).to_bytes(4, 'big')
        + b'IHDR'
        + (1).to_bytes(4, 'big')
        + (1).to_bytes(4, 'big')
        + b'\x08\x06\x00\x00\x00\x00\x00\x00fixture'
    )
    digest = hashlib.sha256(content).hexdigest()
    actor = f"user:{f['creator_id']}"
    asset = f['repo'].create_asset_upload(
        site_id=f['site_id'],
        owner_ref=actor,
        payload={
            'filename': 'synthetic.png',
            'media_type': 'image/png',
            'byte_size': len(content),
            'sha256': digest,
        },
        idempotency_key=str(uuid4()),
        maximum_stored_bytes=10000,
        maximum_active_uploads=10,
        maximum_pending_processing=10,
    )
    store = PrivateArtifactStore(tmp_path / 'private', key=b's' * 32, max_bytes=10000)
    original = store.put
    gate = Barrier(2, timeout=5)

    def both_snapshots(**kwargs):
        gate.wait()
        # Acquiring the global lock here proves neither snapshot transaction retained it.
        with workspace_db_conn(tenant_id=f['site_id']) as conn, conn.cursor() as cur:
            cur.execute("SET LOCAL lock_timeout='100ms'")
            policy.begin_effect(cur)
            conn.rollback()
        return original(**kwargs)

    monkeypatch.setattr(store, 'put', both_snapshots)

    def complete():
        return f['repo'].complete_asset_upload(
            site_id=f['site_id'],
            asset_id=UUID(asset['id']),
            owner_ref=actor,
            upload_grant=asset['uploadGrant'],
            content=content,
            artifact_store=store,
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = [
            future.result(timeout=10) for future in [pool.submit(complete), pool.submit(complete)]
        ]
    assert sorted(item['replayed'] for item in results) == [False, True]
    assert (
        f['execute']('SELECT status FROM sitecontent_mediaasset WHERE id=%s', (asset['id'],))[0][0]
        == 'quarantined'
    )


def test_no_independent_reviewer_is_actionable_without_false_submission(workspace_policy_fixture):
    f = workspace_policy_fixture
    f['execute'](
        "UPDATE api_identity_memberships SET status='suspended' WHERE user_id IN (%s,%s)",
        (str(f['reviewer_id']), str(f['second_reviewer_id'])),
    )
    metadata = policy.review_metadata(
        site_id=f['site_id'], record_id=f['record_id'], user_id=f['creator_id']
    )
    assert metadata['review']['status'] == 'pending'
    assert metadata['review']['recoveryReason'] == 'no_independent_reviewer'
    transition(f, 'return_draft', actor=f['creator_id'])
    before = f['execute'](
        'SELECT count(*) FROM sitecontent_reviewnotificationintent WHERE site_id=%s',
        (f['site_id'],),
    )[0][0]
    audits = f['execute'](
        "SELECT count(*) FROM sitecontent_workspaceauditevent WHERE site_id=%s AND action='content.review_requested'",
        (f['site_id'],),
    )[0][0]
    org_audits = f['execute'](
        "SELECT count(*) FROM api_auth_audit_events WHERE metadata_json->>'tenant_id'=%s AND action='content.review_requested'",
        (f['site_id'],),
    )[0][0]
    with pytest.raises(ValueError, match='content_review_no_independent_reviewer'):
        transition(f, 'submit_review', version=3, actor=f['creator_id'])
    assert f['execute'](
        'SELECT state,version FROM sitecontent_contentrecord WHERE id=%s', (str(f['record_id']),)
    )[0] == ('draft', 3)
    assert (
        f['execute'](
            'SELECT count(*) FROM sitecontent_reviewnotificationintent WHERE site_id=%s',
            (f['site_id'],),
        )[0][0]
        == before
    )
    assert (
        f['execute'](
            "SELECT count(*) FROM sitecontent_workspaceauditevent WHERE site_id=%s AND action='content.review_requested'",
            (f['site_id'],),
        )[0][0]
        == audits
    )
    assert (
        f['execute'](
            "SELECT count(*) FROM api_auth_audit_events WHERE metadata_json->>'tenant_id'=%s AND action='content.review_requested'",
            (f['site_id'],),
        )[0][0]
        == org_audits
    )
    # Ordinary administrator membership recovery, not implicit promotion or self-review.
    f['execute'](
        "UPDATE api_identity_memberships SET status='active' WHERE user_id=%s",
        (str(f['reviewer_id']),),
    )
    assert transition(f, 'submit_review', version=3, actor=f['creator_id'])['state'] == 'in_review'


def test_optional_policy_sole_owner_can_publish_without_reviewer_or_fabricated_approval(
    workspace_policy_fixture,
):
    f = workspace_policy_fixture
    f['execute'](
        "UPDATE sitecontent_contentrecord SET body='Unattributed legacy edit' WHERE id=%s",
        (str(f['record_id']),),
    )
    f['execute'](
        "UPDATE api_identity_memberships SET role='owner' WHERE user_id=%s", (str(f['creator_id']),)
    )
    f['execute'](
        "UPDATE api_identity_memberships SET status='suspended' WHERE user_id IN (%s,%s)",
        (str(f['reviewer_id']), str(f['second_reviewer_id'])),
    )
    policy.update_policy(
        site_id=f['site_id'],
        user_id=f['creator_id'],
        expected_version=1,
        require_review=False,
        public_access='members_only',
    )
    before = f['execute'](
        'SELECT count(*) FROM sitecontent_reviewnotificationintent WHERE site_id=%s',
        (f['site_id'],),
    )[0][0]
    assert transition(f, 'submit_review', actor=f['creator_id'])['state'] == 'in_review'
    metadata = policy.review_metadata(
        site_id=f['site_id'], record_id=f['record_id'], user_id=f['creator_id']
    )
    assert metadata['review']['requiresReview'] is False
    assert metadata['review']['recoveryReason'] is None
    assert 'publish' in metadata['allowedActions']
    assert (
        f['execute'](
            'SELECT count(*) FROM sitecontent_reviewnotificationintent WHERE site_id=%s',
            (f['site_id'],),
        )[0][0]
        == before
    )
    assert transition(f, 'publish', version=3, actor=f['creator_id'])['state'] == 'published'
    assert (
        f['execute'](
            'SELECT count(*) FROM sitecontent_reviewapproval WHERE record_id=%s',
            (str(f['record_id']),),
        )[0][0]
        == 0
    )


@pytest.mark.parametrize('role', ['WORKSPACE', 'WORKSPACE_WORKER'])
def test_revision_parent_scope_allows_only_bound_tenant(workspace_policy_fixture, role):
    factory = workspace_db_conn if role == 'WORKSPACE' else workspace_worker_db_conn
    f = workspace_policy_fixture
    insert = """INSERT INTO sitecontent_contentrevision
      (id,content_id,revision,snapshot,actor_ref,created_at,schema_version,
       snapshot_sha256,action,restored_from_version)
      VALUES(%s,%s,999,'{}'::jsonb,%s,NOW(),1,%s,'rls-test',NULL)"""
    params = (str(uuid4()), str(f['record_id']), f"user:{f['creator_id']}", '0' * 64)
    with factory(tenant_id=f['site_id']) as conn, conn.cursor() as cur:
        cur.execute(insert, params)
        cur.execute('SELECT id FROM sitecontent_contentrevision WHERE id=%s', (params[0],))
        assert str(cur.fetchone()[0]) == params[0]
        conn.rollback()
    # A fresh actual-role connection has no inherited tenant session setting.
    from api.tests.test_workspace_review_history_postgres import connection

    with connection(role) as (_, cur):
        cur.execute("SELECT current_setting('app.tenant_id',true)")
        assert cur.fetchone()[0] in (None, '')
        cur.execute('SELECT count(*) FROM sitecontent_contentrevision WHERE content_id=%s',
                    (str(f['record_id']),))
        assert cur.fetchone()[0] == 0
        with pytest.raises(psycopg2.errors.InsufficientPrivilege):
            cur.execute(insert, params)
    persisted = f['execute'](
        'SELECT id FROM sitecontent_contentrevision WHERE content_id=%s LIMIT 1',
        (str(f['record_id']),),
    )[0][0]
    for site in ('unrelated-tenant', ''):
        with connection(role) as (conn, cur):
            cur.execute("SELECT set_config('app.tenant_id',%s,true)", (site,))
            cur.execute(
                'SELECT count(*) FROM sitecontent_contentrevision WHERE content_id=%s',
                (str(f['record_id']),),
            )
            assert cur.fetchone()[0] == 0
            cur.execute('DELETE FROM sitecontent_contentrevision WHERE id=%s', (str(persisted),))
            assert cur.rowcount == 0
            cur.execute(
                "UPDATE sitecontent_contentrevision SET action='forbidden' WHERE id=%s",
                (str(persisted),),
            )
            assert cur.rowcount == 0
            with pytest.raises(psycopg2.errors.InsufficientPrivilege):
                cur.execute(insert, params)
            conn.rollback()


@pytest.mark.parametrize('role', ['API_RUNTIME', 'RUNTIME_WORKER', 'DATA_RIGHTS_WORKER'])
def test_revision_history_not_exposed_to_other_roles(workspace_policy_fixture, role):
    from api.tests.test_workspace_review_history_postgres import connection

    f = workspace_policy_fixture
    with connection(role, f['site_id']) as (_, cur):
        try:
            cur.execute(
                'SELECT id FROM sitecontent_contentrevision WHERE content_id=%s',
                (str(f['record_id']),),
            )
        except psycopg2.errors.InsufficientPrivilege:
            pass  # Public/general worker has no history table grant.
        else:
            assert cur.fetchall() == []  # Rights worker without an exact durable claim.


@pytest.mark.parametrize('role', ['WORKSPACE', 'WORKSPACE_WORKER'])
def test_revision_reparent_cannot_escape_bound_tenant(workspace_policy_fixture, role):
    factory = workspace_db_conn if role == 'WORKSPACE' else workspace_worker_db_conn
    f = workspace_policy_fixture
    foreign_id = uuid4()
    f['execute'](
        """INSERT INTO sitecontent_contentrecord
        (id,site_id,content_type,slug,title,excerpt,body,metadata,state,
         sitemap_include,search_visible,version,schedule_timezone,schema_version,
         values,created_at,updated_at)
        VALUES(%s,%s,'legacy','foreign','Foreign','','','{}','draft',FALSE,FALSE,1,'',1,
               '{}',NOW(),NOW())""",
        (str(foreign_id), 'other-' + uuid4().hex[:20]),
    )
    with factory(tenant_id=f['site_id']) as conn, conn.cursor() as cur:
        with pytest.raises(psycopg2.errors.InsufficientPrivilege):
            cur.execute(
                'UPDATE sitecontent_contentrevision SET content_id=%s WHERE content_id=%s',
                (str(foreign_id), str(f['record_id'])),
            )
        conn.rollback()


def test_revision_upgrade_preserves_forced_rls_and_restrictive_claim_fence(
    workspace_policy_fixture,
):
    f = workspace_policy_fixture
    assert f['execute'](
        "SELECT count(*) FROM django_migrations WHERE app='sitecontent' "
        "AND name='0041_workspace_revision_tenant_scope'"
    )[0][0] == 1
    assert f['execute'](
        "SELECT relrowsecurity,relforcerowsecurity FROM pg_class "
        "WHERE oid='public.sitecontent_contentrevision'::regclass"
    )[0] == (True, True)
    policies = dict(f['execute'](
        "SELECT policyname,permissive FROM pg_policies "
        "WHERE schemaname='public' AND tablename='sitecontent_contentrevision'"
    ))
    assert policies['data_rights_claim_fence'] == 'RESTRICTIVE'
    assert policies['workspace_revision_tenant_scope'] == 'PERMISSIVE'


@pytest.mark.parametrize('isolation', ['REPEATABLE READ', 'SERIALIZABLE'])
def test_locked_policy_read_rejects_stale_snapshot_isolation(workspace_policy_fixture, isolation):
    from api.tests.test_workspace_review_history_postgres import connection

    f = workspace_policy_fixture
    with connection('WORKSPACE_WORKER') as (_, cur):
        cur.execute('SET TRANSACTION ISOLATION LEVEL ' + isolation)
        cur.execute("SELECT set_config('app.tenant_id',%s,true)", (f['site_id'],))
        with pytest.raises(psycopg2.errors.InvalidTransactionState, match='isolation_unsupported'):
            policy.read_policy(cur, site_id=f['site_id'], lock=True)


def test_worker_policy_read_after_lock_wait_observes_committed_policy(workspace_policy_fixture):
    from threading import Event
    from time import monotonic, sleep

    f = workspace_policy_fixture
    waiting = Event()
    reader_pid = []

    def read():
        with workspace_worker_db_conn(tenant_id=f['site_id']) as conn, conn.cursor() as cur:
            cur.execute("SET LOCAL lock_timeout='5s'")
            cur.execute('SELECT pg_backend_pid()')
            reader_pid.append(cur.fetchone()[0])
            waiting.set()
            result = policy.read_policy(cur, site_id=f['site_id'], lock=True)
            conn.rollback()
            return result

    with workspace_db_conn(tenant_id=f['site_id']) as writer, writer.cursor() as cur:
        cur.execute('SELECT pg_backend_pid()')
        writer_pid = cur.fetchone()[0]
        policy.begin_effect(cur, actor_ref=f"user:{f['reviewer_id']}")
        cur.execute(
            'UPDATE sitecontent_workspacepolicy SET require_review=FALSE,version=version+1 '
            'WHERE site_id=%s RETURNING version', (f['site_id'],),
        )
        version = cur.fetchone()[0]
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(read)
            try:
                assert waiting.wait(3)
                deadline = monotonic() + 3
                blocked = False
                while monotonic() < deadline:
                    blockers = f['execute']('SELECT pg_blocking_pids(%s)', (reader_pid[0],))[0][0]
                    if writer_pid in blockers:
                        blocked = True
                        break
                    sleep(0.01)
                assert blocked, 'reader must actually wait on the writer, not merely be unscheduled'
                assert not future.done()
            finally:
                writer.commit()
            result = future.result(timeout=5)
        assert result['version'] == version and result['require_review'] is False
