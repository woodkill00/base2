"""Real migrated PostgreSQL + restricted worker integration contract.

These tests are NOT mock/SQLite acceptance. The gate-owned workspace_policy_fixture
must provision a disposable synthetic in-review subject and public identities, with
reviewer product/email immediate and all other recipients disabled. It supplies
execute(sql, params)->rows, preference(mode), submit()->new_intent_id. Fixture-owner
writes are limited to that random synthetic scope; consumer always uses real worker
credentials and the real 0038 helpers. No test silently skips missing infrastructure.
"""

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import UTC, datetime, time, timedelta
from threading import Barrier
from uuid import uuid4

import pytest

from api.services import workspace_review_notifications as worker

pytestmark = pytest.mark.integration


def run(fixture, now):
    return worker.process_review_notifications(site_id=fixture['site_id'], now=now)


def receipts(fixture):
    return fixture['execute'](
        'SELECT effect_key FROM sitecontent_reviewnotificationdelivery WHERE site_id=%s',
        (fixture['site_id'],),
    )


def test_two_real_workers_duplicate_cycle_and_restart_have_one_business_effect(
    workspace_policy_fixture,
):
    fixture = workspace_policy_fixture
    now = datetime.now(UTC) + timedelta(seconds=1)
    fixture['execute'](
        """INSERT INTO sitecontent_reviewnotificationintent
        (id,site_id,record_id,submission_id,subject_revision,recipient_id,channel,event,status,
         attempts,available_at,delivered_at,last_error_code,digest_batch_id,created_at,updated_at)
        SELECT %s,site_id,record_id,submission_id,subject_revision,recipient_id,channel,event,status,
         attempts,available_at,delivered_at,last_error_code,digest_batch_id,created_at,updated_at
        FROM sitecontent_reviewnotificationintent WHERE site_id=%s AND recipient_id=%s LIMIT 1
        ON CONFLICT (site_id,submission_id,recipient_id,channel) DO NOTHING""",
        (str(uuid4()), fixture['site_id'], str(fixture['reviewer_id'])),
    )
    barrier = Barrier(2, timeout=10)

    def consume():
        barrier.wait()
        return run(fixture, now)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(consume) for _ in range(2)]
        results = [future.result(timeout=30) for future in futures]
    assert sum(result['delivered'] for result in results) == 1
    assert len(receipts(fixture)) == 1
    assert run(fixture, now)['delivered'] == 0
    assert len(receipts(fixture)) == 1


def test_process_loss_after_receipt_rolls_back_then_restart_delivers(
    workspace_policy_fixture, monkeypatch
):
    fixture = workspace_policy_fixture
    now = datetime.now(UTC) + timedelta(seconds=1)
    original = worker._receipt

    def crash(*args, **kwargs):
        original(*args, **kwargs)
        raise KeyboardInterrupt('synthetic process loss')

    monkeypatch.setattr(worker, '_receipt', crash)
    with pytest.raises(KeyboardInterrupt):
        run(fixture, now)
    assert receipts(fixture) == []
    monkeypatch.setattr(worker, '_receipt', original)
    assert run(fixture, now)['delivered'] == 1
    assert len(receipts(fixture)) == 1


def test_lost_commit_response_replay_does_not_duplicate(workspace_policy_fixture, monkeypatch):
    fixture = workspace_policy_fixture
    now = datetime.now(UTC) + timedelta(seconds=1)
    original = worker.db_conn

    class LostResponse:
        def __init__(self, connection):
            self.connection = connection

        def __getattr__(self, key):
            return getattr(self.connection, key)

        def commit(self):
            self.connection.commit()
            raise RuntimeError('synthetic lost commit response')

    @contextmanager
    def connection(*, tenant_id):
        with original(tenant_id=tenant_id) as conn:
            yield LostResponse(conn)

    monkeypatch.setattr(worker, 'db_conn', connection)
    with pytest.raises(RuntimeError, match='lost commit'):
        run(fixture, now)
    monkeypatch.setattr(worker, 'db_conn', original)
    assert run(fixture, now)['delivered'] == 0
    assert len(receipts(fixture)) == 1


def test_real_savepoint_outage_retry_and_terminal_failure(workspace_policy_fixture, monkeypatch):
    fixture = workspace_policy_fixture
    now = datetime.now(UTC) + timedelta(seconds=1)
    original = worker._receipt

    def unavailable(cur, **kwargs):
        # PostgreSQL transaction is really aborted, not just a Python mock error.
        cur.execute('SELECT 1/0')

    monkeypatch.setattr(worker, '_receipt', unavailable)
    for attempt in range(8):
        result = run(fixture, now)
        assert result['retry' if attempt < 7 else 'failed'] == 1
        assert receipts(fixture) == []
        assert run(fixture, now)['retry'] == 0
        now += timedelta(seconds=min(60 * 2**attempt, 3600))
    monkeypatch.setattr(worker, '_receipt', original)
    assert run(fixture, now)['delivered'] == 0
    status = fixture['execute'](
        """SELECT status,attempts,last_error_code
        FROM sitecontent_reviewnotificationintent WHERE site_id=%s AND recipient_id=%s""",
        (fixture['site_id'], str(fixture['reviewer_id'])),
    )
    assert status == [('failed', 8, 'review_delivery_unavailable')]


def test_digest_revoke_all_suppressed_is_terminal_without_receipt(workspace_policy_fixture):
    fixture = workspace_policy_fixture
    fixture['preference']('digest')
    now = datetime.now(UTC) + timedelta(seconds=1)
    assert run(fixture, now)['digest'] == 1
    fixture['execute'](
        'UPDATE api_identity_memberships SET status=%s WHERE user_id=%s',
        ('suspended', str(fixture['reviewer_id'])),
    )
    boundary = datetime.combine(now.date() + timedelta(days=1), time.min, tzinfo=UTC)
    assert run(fixture, boundary)['suppressed'] == 1
    assert receipts(fixture) == []
    batches = fixture['execute'](
        'SELECT status,delivered_at FROM sitecontent_reviewdigestbatch WHERE site_id=%s',
        (fixture['site_id'],),
    )
    assert batches == [('closed', None)]
    # Actual second SELECT must not reclaim the closed/all-suppressed batch.
    repeated = run(fixture, boundary + timedelta(days=1))
    assert repeated == dict(
        adapter='local_test', delivered=0, digest=0, suppressed=0, retry=0, failed=0
    )
    assert receipts(fixture) == []


def test_closed_digest_late_arrival_gets_new_batch_and_exact_membership(workspace_policy_fixture):
    fixture = workspace_policy_fixture
    fixture['preference']('digest')
    now = datetime.now(UTC) + timedelta(seconds=1)
    assert run(fixture, now)['digest'] == 1
    boundary = datetime.combine(now.date() + timedelta(days=1), time.min, tzinfo=UTC)
    assert run(fixture, boundary)['delivered'] == 1
    first_receipts = receipts(fixture)
    new_intent = fixture['submit']()
    assert run(fixture, boundary)['digest'] == 1
    batches = fixture['execute'](
        """SELECT b.digest_date,b.status,i.id
        FROM sitecontent_reviewdigestbatch b JOIN sitecontent_reviewnotificationintent i
        ON i.digest_batch_id=b.id AND i.site_id=b.site_id
        WHERE b.site_id=%s ORDER BY b.digest_date""",
        (fixture['site_id'],),
    )
    assert len(batches) == 2
    assert batches[0][0] == boundary.date() and batches[0][1] == 'delivered'
    assert batches[1][0] == boundary.date() + timedelta(days=1) and str(batches[1][2]) == str(
        new_intent
    )
    assert receipts(fixture) == first_receipts
    assert run(fixture, boundary + timedelta(days=1))['delivered'] == 1
    assert len(receipts(fixture)) == 2


@pytest.mark.parametrize('mutation', ['preference', 'state', 'revision', 'submission', 'user'])
def test_live_eligibility_changes_suppress_before_real_effect(workspace_policy_fixture, mutation):
    fixture = workspace_policy_fixture
    site = fixture['site_id']
    if mutation == 'preference':
        fixture['preference']('disabled')
    elif mutation == 'state':
        fixture['execute'](
            "UPDATE sitecontent_contentrecord SET state='draft' WHERE site_id=%s AND id=%s",
            (site, str(fixture['record_id'])),
        )
    elif mutation in {'revision', 'submission'}:
        column = 'semantic_revision' if mutation == 'revision' else 'submission_id'
        revision_change = ',semantic_revision=gen_random_uuid()' if mutation == 'submission' else ''
        fixture['execute'](
            f'UPDATE sitecontent_reviewsubject SET {column}=%s{revision_change} WHERE site_id=%s AND record_id=%s',
            (str(uuid4()), site, str(fixture['record_id'])),
        )
    else:
        fixture['execute'](
            'UPDATE api_auth_users SET is_active=false WHERE id=%s', (str(fixture['reviewer_id']),)
        )
    result = run(fixture, datetime.now(UTC) + timedelta(seconds=1))
    assert result['delivered'] == 0 and result['suppressed'] >= 1
    assert receipts(fixture) == []


def test_worker_cannot_read_other_site_or_identity_tables(workspace_policy_fixture):
    fixture = workspace_policy_fixture
    with worker.db_conn(tenant_id='unrelated-notification-site') as conn, conn.cursor() as cur:
        cur.execute(
            'SELECT id FROM sitecontent_reviewnotificationintent WHERE site_id=%s',
            (fixture['site_id'],),
        )
        assert cur.fetchall() == []
    with worker.db_conn(tenant_id=fixture['site_id']) as conn, conn.cursor() as cur:
        with pytest.raises(Exception) as error:
            cur.execute('SELECT email FROM api_auth_users')
        assert getattr(error.value, 'pgcode', None) == '42501'
        conn.rollback()


@pytest.mark.parametrize('before,after,expected', [(True, False, 1), (False, True, 0)])
def test_policy_flip_rechecks_optional_author_recipient_without_backfill(
    workspace_policy_fixture, before, after, expected
):
    fixture = workspace_policy_fixture
    site = fixture['site_id']
    from api.repositories import workspace_policy

    def set_policy(required):
        current = workspace_policy.get_policy(site_id=site, user_id=fixture['reviewer_id'])
        updated = workspace_policy.update_policy(
            site_id=site, user_id=fixture['reviewer_id'],
            expected_version=current['version'], require_review=required,
            public_access=current['public_access'],
        )
        assert updated is not None

    set_policy(before)
    # Existing durable recipient is now an author, but not the request's submitter.
    # The final current policy, not the enqueue-time policy, governs its eligibility.
    fixture['execute'](
        """UPDATE sitecontent_reviewsubject SET semantic_author_id=%s
           WHERE site_id=%s AND record_id=%s""",
        (str(fixture['reviewer_id']), site, str(fixture['record_id'])),
    )
    set_policy(after)
    result = run(fixture, datetime.now(UTC) + timedelta(seconds=1))
    assert result['delivered'] == expected
    assert len(receipts(fixture)) == expected
    assert run(fixture, datetime.now(UTC) + timedelta(seconds=2))['delivered'] == 0
