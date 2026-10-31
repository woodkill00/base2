"""Disposable PostgreSQL proof obligations; never substitute mocks for these tests."""

import os
from contextlib import contextmanager
from uuid import uuid4

import pytest

pytestmark = pytest.mark.integration


@contextmanager
def connection(role, site=None):
    import psycopg2

    conn = psycopg2.connect(
        host=os.environ['DB_HOST'],
        port=os.environ.get('DB_PORT', '5432'),
        dbname=os.environ['DB_NAME'],
        user=os.environ[role + '_DB_USER'],
        password=os.environ[role + '_DB_PASSWORD'],
    )
    try:
        with conn.cursor() as cur:
            if site:
                cur.execute("SELECT set_config('app.tenant_id',%s,true)", (site,))
            yield conn, cur
    finally:
        conn.rollback()
        conn.close()


def approve(f):
    from api.repositories import workspace_policy

    workspace_policy.review_action(
        site_id=f['site_id'],
        type_key=f['type_key'],
        record_id=f['record_id'],
        user_id=f['reviewer_id'],
        expected_version=2,
    )


def claim(f, kind='deletion', stale=False):
    operation, token = uuid4(), uuid4()
    f['execute'](
        """INSERT INTO api_data_rights_operations
      (id,tenant_id,user_id,kind,status,request_ciphertext,retention_until,claim_token,claim_expires_at)
      VALUES(%s,%s,%s,%s,'running','synthetic',NOW()+INTERVAL '1 day',%s,
       NOW()+(%s*INTERVAL '1 minute'))""",
        (str(operation), f['site_id'], str(f['reviewer_id']), kind, str(token), -5 if stale else 5),
    )
    return operation, token


def test_runtime_cannot_erase_approvals_or_enter_private_maintenance(workspace_policy_fixture):
    import psycopg2

    f = workspace_policy_fixture
    approve(f)
    statements = [
        ('SELECT base2_purge_review_history(%s,%s)', (f['site_id'], str(f['record_id']))),
        ('SELECT * FROM public.base2_review_maintenance_capability', ()),
        (
            "SELECT base2_review_maintenance_allowed('sitecontent_reviewapproval',%s,'DELETE','{}',NULL)",
            (str(uuid4()),),
        ),
        ('DELETE FROM sitecontent_reviewapproval WHERE record_id=%s', (str(f['record_id']),)),
        (
            'UPDATE sitecontent_reviewapproval SET reviewer_id=%s WHERE record_id=%s',
            (str(uuid4()), str(f['record_id'])),
        ),
    ]
    for sql, params in statements:
        with connection('WORKSPACE', f['site_id']) as (_, cur), pytest.raises(psycopg2.Error):
            cur.execute(sql, params)
    assert (
        f['execute'](
            'SELECT count(*) FROM sitecontent_reviewapproval WHERE record_id=%s',
            (str(f['record_id']),),
        )[0][0]
        == 1
    )


@pytest.mark.parametrize(
    'state,age', [('deleted', 1), ('deleted', -1), ('deleted', None), ('draft', 40)]
)
def test_retention_rejects_unexpired_null_future_and_live_records(
    workspace_policy_fixture, state, age
):
    import psycopg2

    f = workspace_policy_fixture
    f['execute'](
        "UPDATE sitecontent_contentrecord SET state=%s,deleted_at=NOW()-(%s*INTERVAL '1 day') WHERE id=%s",
        (state, age, str(f['record_id'])),
    )
    with connection('WORKSPACE_WORKER', f['site_id']) as (_, cur), pytest.raises(
        psycopg2.Error, match='review_retention_not_eligible'
    ):
        cur.execute('SELECT base2_purge_review_history(%s,%s)', (f['site_id'], str(f['record_id'])))


def test_retention_bound_tenant_rollback_and_preserved_audit(workspace_policy_fixture):
    import psycopg2

    f = workspace_policy_fixture
    approve(f)
    f['execute'](
        "UPDATE sitecontent_contentrecord SET state='deleted',deleted_at=NOW()-INTERVAL '31 days' WHERE id=%s",
        (str(f['record_id']),),
    )
    with connection('WORKSPACE_WORKER', 'not-this-tenant') as (_, cur), pytest.raises(
        psycopg2.Error, match='review_retention_authority_required'
    ):
        cur.execute('SELECT base2_purge_review_history(%s,%s)', (f['site_id'], str(f['record_id'])))
    # The entire function, capability consumption and audit are rollback atomic.
    with connection('WORKSPACE_WORKER', f['site_id']) as (_, cur):
        cur.execute('SELECT base2_purge_review_history(%s,%s)', (f['site_id'], str(f['record_id'])))
        assert cur.fetchone()[0]['approvals'] == 1
    assert (
        f['execute'](
            'SELECT count(*) FROM sitecontent_reviewapproval WHERE record_id=%s',
            (str(f['record_id']),),
        )[0][0]
        == 1
    )
    with connection('WORKSPACE_WORKER', f['site_id']) as (conn, cur):
        cur.execute('CREATE TEMP TABLE base2_review_maintenance_capability (fake text)')
        cur.execute('SELECT base2_purge_review_history(%s,%s)', (f['site_id'], str(f['record_id'])))
        assert cur.fetchone()[0]['approvals'] == 1
        conn.commit()
    assert (
        f['execute'](
            'SELECT count(*) FROM sitecontent_reviewapproval WHERE record_id=%s',
            (str(f['record_id']),),
        )[0][0]
        == 0
    )
    assert (
        f['execute'](
            "SELECT count(*) FROM sitecontent_workspaceauditevent WHERE object_ref=%s AND action='content.review_history_retained_purge'",
            (str(f['record_id']),),
        )[0][0]
        == 1
    )
    assert (
        f['execute']('SELECT count(*) FROM public.base2_review_maintenance_capability')[0][0] == 0
    )


def test_stale_privacy_claim_cannot_change_history(workspace_policy_fixture):
    import psycopg2

    f = workspace_policy_fixture
    approve(f)
    operation, token = claim(f, stale=True)
    with connection('DATA_RIGHTS_WORKER') as (_, cur), pytest.raises(
        psycopg2.Error, match='data_rights_claim_invalid'
    ):
        cur.execute(
            "SELECT base2_apply_data_rights_subject_action(%s,%s,'deletion','{}')",
            (str(operation), str(token)),
        )
    assert str(
        f['execute'](
            'SELECT reviewer_id FROM sitecontent_reviewapproval WHERE record_id=%s',
            (str(f['record_id']),),
        )[0][0]
    ) == str(f['reviewer_id'])


def test_valid_erasure_preserves_history_but_invalidates_authorization(workspace_policy_fixture):
    f = workspace_policy_fixture
    approve(f)
    operation, token = claim(f)
    before = f['execute'](
        'SELECT semantic_revision FROM sitecontent_reviewsubject WHERE record_id=%s',
        (str(f['record_id']),),
    )[0][0]
    with connection('DATA_RIGHTS_WORKER') as (conn, cur):
        cur.execute(
            "SELECT base2_apply_data_rights_subject_action(%s,%s,'deletion','{}')",
            (str(operation), str(token)),
        )
        assert cur.fetchone()[0]['review_history']['approvals'] == 1
        conn.commit()
    row = f['execute'](
        'SELECT semantic_revision,submission_id,scheduled_by_id,fingerprint FROM sitecontent_reviewsubject WHERE record_id=%s',
        (str(f['record_id']),),
    )[0]
    assert row[0] != before and row[1:3] == (None, None) and row[3] == '0' * 64
    reviewer = f['execute'](
        'SELECT reviewer_id FROM sitecontent_reviewapproval WHERE record_id=%s',
        (str(f['record_id']),),
    )[0][0]
    assert str(reviewer) != str(f['reviewer_id'])
    assert (
        f['execute'](
            "SELECT base2_workspace_approval_valid(%s,%s,%s,'publish')",
            (f['site_id'], str(f['record_id']), str(f['second_reviewer_id'])),
        )[0][0]
        is False
    )
    assert not f['execute']('SELECT id FROM api_auth_users WHERE id=%s', (str(reviewer),))
    assert (
        f['execute']('SELECT count(*) FROM public.base2_review_maintenance_capability')[0][0] == 0
    )
    assert (
        f['execute'](
            "SELECT count(*) FROM sitecontent_workspaceauditevent WHERE action='content.review_maintenance' AND object_ref=%s",
            (str(operation),),
        )[0][0]
        == 1
    )


def test_capability_cannot_be_reused_for_another_row_action_or_transaction(
    workspace_policy_fixture,
):
    f = workspace_policy_fixture
    # Owner fixture inserts an infrastructure token, never changing domain rows.
    f['execute']("""DO $$ DECLARE target uuid:=gen_random_uuid(); BEGIN
     INSERT INTO public.base2_review_maintenance_capability VALUES
      (pg_backend_pid(),txid_current(),'synthetic',target,'DELETE','{}',NULL);
     IF public.base2_review_maintenance_allowed('synthetic',gen_random_uuid(),'DELETE','{}',NULL)
       OR public.base2_review_maintenance_allowed('synthetic',target,'UPDATE','{}',NULL) THEN
       RAISE EXCEPTION 'capability_scope_bypass'; END IF;
     IF NOT public.base2_review_maintenance_allowed('synthetic',target,'DELETE','{}',NULL) THEN
       RAISE EXCEPTION 'capability_not_consumed'; END IF;
     IF public.base2_review_maintenance_allowed('synthetic',target,'DELETE','{}',NULL) THEN
       RAISE EXCEPTION 'capability_reused'; END IF;
     INSERT INTO public.base2_review_maintenance_capability VALUES
      (pg_backend_pid(),txid_current()-1,'synthetic',target,'DELETE','{}',NULL);
     IF public.base2_review_maintenance_allowed('synthetic',target,'DELETE','{}',NULL) THEN
       RAISE EXCEPTION 'capability_transaction_bypass'; END IF;
     DELETE FROM public.base2_review_maintenance_capability WHERE table_name='synthetic';
    END $$""")


@pytest.mark.parametrize(
    'kind,allowed',
    [
        ('export', True),
        ('correction', True),
        ('deletion', True),
        ('deactivation', False),
        ('global_deletion', False),
        ('global_deactivation', False),
    ],
)
def test_subject_projection_has_closed_compatible_claim_kinds(
    workspace_policy_fixture, kind, allowed
):
    import psycopg2

    f = workspace_policy_fixture
    operation, token = claim(f, kind=kind)
    with connection('DATA_RIGHTS_WORKER', f['site_id']) as (_, cur):
        cur.execute(
            "SELECT set_config('app.data_rights_operation_id',%s,true),set_config('app.data_rights_claim_token',%s,true)",
            (str(operation), str(token)),
        )
        if allowed:
            cur.execute('SELECT * FROM base2_export_data_rights_subject_surfaces()')
            assert any(row[0] == 'sitecontent_reviewnotificationintent' for row in cur.fetchall())
        else:
            with pytest.raises(psycopg2.Error, match='data_rights_claim_invalid'):
                cur.execute('SELECT * FROM base2_export_data_rights_subject_surfaces()')


def test_wrong_claim_token_action_and_cross_tenant_projection_are_denied(workspace_policy_fixture):
    import psycopg2

    f = workspace_policy_fixture
    operation, token = claim(f)
    for passed_token, action in [(uuid4(), 'deletion'), (token, 'global_deletion')]:
        with connection('DATA_RIGHTS_WORKER') as (_, cur), pytest.raises(
            psycopg2.Error, match='data_rights_claim_invalid'
        ):
            cur.execute(
                "SELECT base2_apply_data_rights_subject_action(%s,%s,%s,'{}')",
                (str(operation), str(passed_token), action),
            )
    with connection('DATA_RIGHTS_WORKER', 'not-this-tenant') as (_, cur):
        cur.execute(
            "SELECT set_config('app.data_rights_operation_id',%s,true),set_config('app.data_rights_claim_token',%s,true)",
            (str(operation), str(token)),
        )
        with pytest.raises(psycopg2.Error, match='data_rights_claim_invalid'):
            cur.execute('SELECT * FROM base2_export_data_rights_subject_surfaces()')
