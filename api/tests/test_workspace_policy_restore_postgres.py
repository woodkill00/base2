"""Dedicated guarded whole-database restoration; excluded from ordinary CI slice.

Uses production encrypted backup/restore and existing role identities only. No
restored runtime connection is opened until authenticated catalog parity passes.
"""
import json
import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import psycopg2
import pytest

from api import db
from api.repositories import settings as preferences
from api.repositories import workspace_policy as policy
from api.services.workspace_review_notifications import process_review_notifications
from api.tests.conftest import workspace_policy_fixture
from scripts.python.workspace_policy_restore_fixture import (
    DisposableRestore,
    private_write,
    runtime_database,
)

pytestmark = pytest.mark.integration


def test_encrypted_restore_preserves_policy_history_and_restricted_effects(tmp_path, monkeypatch):
    harness = DisposableRestore(tmp_path / 'backup-proof')
    report_path = Path(os.environ['WORKSPACE_RESTORE_REPORT'])
    main_before = harness.digest(harness.main)
    try:
        harness.create()
        harness.migrate_source()
        with runtime_database(harness.source, monkeypatch, verified=True) as source_patch:
            seed = workspace_policy_fixture.__wrapped__(source_patch)
            f = next(seed)
            try:
                site = f['site_id']
                updated = policy.update_policy(
                    site_id=site, user_id=f['reviewer_id'], expected_version=1,
                    require_review=True, public_access='public_allowed',
                )
                assert updated is not None and updated['version'] == 2
                f['preference']('digest')
                f['preference']('immediate')
                saved_preferences = preferences.get_notifications(user_id=f['reviewer_id'], tenant_id=site)
                assert saved_preferences['version'] >= 3
                delivered = process_review_notifications(site_id=site, now=datetime.now(UTC) + timedelta(seconds=1))
                assert delivered['adapter'] == 'local_test' and delivered['delivered'] == 1
                pending = f['submit']()  # Creates a distinct record, not a new cycle on the approved record.
                pending_record = f['execute'](
                    'SELECT record_id FROM sitecontent_reviewnotificationintent WHERE id=%s',
                    (str(pending),),
                )[0][0]
                assert str(pending_record) != str(f['record_id'])
                policy.review_action(site_id=site, type_key=f['type_key'], record_id=f['record_id'],
                                     user_id=f['reviewer_id'], expected_version=2)
                assert f['execute'](
                    """SELECT a.subject_revision=s.semantic_revision,
                    a.semantic_generation=s.semantic_generation,a.fingerprint=s.fingerprint,
                    a.policy_version=p.version FROM sitecontent_reviewapproval a
                    JOIN sitecontent_reviewsubject s ON s.record_id=a.record_id AND s.site_id=a.site_id
                    JOIN sitecontent_workspacepolicy p ON p.site_id=a.site_id
                    WHERE a.record_id=%s AND a.site_id=%s""", (str(f['record_id']), site),
                )[0] == (True, True, True, True)

                def approval_valid():
                    with db.workspace_db_conn(tenant_id=site) as conn, conn.cursor() as cur:
                        policy.begin_effect(cur)
                        cur.execute('SELECT base2_workspace_approval_valid(%s,%s,%s,%s)',
                                    (site, str(f['record_id']), str(f['second_reviewer_id']), 'publish'))
                        valid = cur.fetchone()[0]
                        conn.rollback()
                        return valid

                assert approval_valid() is True
                f['execute']("UPDATE api_identity_memberships SET status='suspended' WHERE user_id=%s",
                             (str(f['reviewer_id']),))
                assert approval_valid() is False  # Revocation alone changed eligibility.
                source_before = harness.digest(harness.source)
                assert source_before['sitecontent_reviewapproval']['count'] == 1
                assert source_before['sitecontent_reviewnotificationdelivery']['count'] == 1
                assert f['execute']("SELECT count(*) FROM sitecontent_reviewnotificationintent WHERE status='pending'")[0][0] > 0
                restored = harness.backup_restore()
                # This is an owner-only table comparison, not a function invocation.
                assert restored['databaseRestoreExecuted'] is True
                assert harness.digest(harness.target) == source_before
                with runtime_database(harness.target, monkeypatch, verified=harness.security_verified) as target_patch:
                    target_patch.setenv('DB_USER', os.environ['API_RUNTIME_DB_USER'])
                    target_patch.setenv('DB_PASSWORD', os.environ['API_RUNTIME_DB_PASSWORD'])
                    current_policy = policy.get_policy(site_id=site, user_id=f['second_reviewer_id'])
                    assert current_policy['version'] == 2
                    assert current_policy['require_review'] is True
                    assert current_policy['public_access'] == 'public_allowed'
                    current_preferences = preferences.get_notifications(user_id=f['reviewer_id'], tenant_id=site)
                    assert current_preferences == saved_preferences
                    assert preferences.replace_notifications(
                        user_id=f['reviewer_id'], tenant_id=site,
                        expected_version=current_preferences['version'] - 1,
                        preferences=current_preferences['preferences'],
                    ) is None
                    with pytest.raises(ValueError, match='review_required'):
                        f['repo'].transition_record(
                            site_id=site, type_key=f['type_key'], record_id=f['record_id'],
                            expected_version=2, actor_ref=f"user:{f['second_reviewer_id']}",
                            action='publish', publish_at=None, timezone=None,
                        )
                    with db.workspace_db_conn(tenant_id='foreign-scope') as conn, conn.cursor() as cur:
                        for table in ('sitecontent_reviewsubject', 'sitecontent_reviewapproval'):
                            cur.execute(f'SELECT count(*) FROM {table}')
                            assert cur.fetchone()[0] == 0
                        conn.rollback()
                    with db.db_conn(tenant_id=site) as conn, conn.cursor() as cur:
                        with pytest.raises(psycopg2.errors.InsufficientPrivilege):
                            cur.execute('SELECT * FROM sitecontent_reviewapproval')
                        conn.rollback()
                    with db.workspace_worker_db_conn(tenant_id=site) as conn, conn.cursor() as cur:
                        assert policy.read_policy(cur, site_id=site, lock=True)['version'] == 2
                        with pytest.raises(psycopg2.errors.InsufficientPrivilege):
                            cur.execute('UPDATE sitecontent_workspacepolicy SET version=version WHERE site_id=%s', (site,))
                        conn.rollback()
                    now = datetime.now(UTC) + timedelta(seconds=2)
                    first = process_review_notifications(site_id=site, now=now)
                    second = process_review_notifications(site_id=site, now=now + timedelta(seconds=1))
                    assert first['delivered'] == second['delivered'] == 0
                    assert first['suppressed'] >= 1
                target_after = harness.digest(harness.target)
                assert target_after['sitecontent_reviewnotificationdelivery'] == source_before['sitecontent_reviewnotificationdelivery']
                assert target_after['sitecontent_reviewapproval'] == source_before['sitecontent_reviewapproval']
                assert harness.digest(harness.source) == source_before
                assert harness.digest(harness.main) == main_before
            finally:
                seed.close()
    finally:
        harness.cleanup(primary_failure=sys.exc_info()[0] is not None)
    private_write(report_path, json.dumps({
        'schemaVersion': 1, 'status': 'passed', 'caseCount': 1,
        'runId': os.environ['WORKSPACE_RESTORE_RUN_ID'],
        'sourceCommit': subprocess.check_output(['git', 'rev-parse', 'HEAD'],
            cwd=Path(__file__).resolve().parents[2], text=True, timeout=5).strip(),
        'securityVerified': True, 'sourceUnchanged': True, 'mainUnchanged': True,
        'restrictedChecks': ['policy', 'cas', 'revoked-approval', 'cross-tenant',
                             'public-history', 'worker-policy-read-only', 'delivery-replay'],
    }, sort_keys=True).encode())
