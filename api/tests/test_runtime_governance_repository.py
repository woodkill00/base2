from contextlib import contextmanager
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest

from api.repositories.runtime_governance import (
    _next_schedule_run,
    _retry_delay_seconds,
    _stored_idempotency_key,
    RuntimeRepositoryError,
    claim_jobs,
    dead_letter_action,
    dead_letters,
    due_schedules,
    enqueue_job,
    renew_job_lease,
    settle_schedule_claim,
    settle_job,
)


@contextmanager
def connection(cursor):
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cursor
    yield conn


NOW = datetime(2026, 9, 8, tzinfo=UTC)
JOB_ID = UUID(int=1)


def test_enqueue_job_creates_and_exactly_replays():
    cursor = MagicMock()
    cursor.fetchone.side_effect = [('active',), None, (0, False), (JOB_ID,)]
    with patch(
        'api.repositories.runtime_governance.workspace_db_conn',
        return_value=connection(cursor),
    ):
        created = enqueue_job(
            tenant_id='tenant-one',
            owner_ref='owner:1',
            job_type='email',
            payload_digest='a' * 64,
            payload_schema=1,
            idempotency_key='job-1',
            available_at=NOW,
        )
    assert created == {'jobId': str(JOB_ID), 'state': 'queued', 'replayed': False}
    assert 'pg_advisory_xact_lock' in cursor.execute.call_args_list[1].args[0]

    replay = MagicMock()
    replay.fetchone.side_effect = [('active',), (JOB_ID, 'owner:1', 'email', 'a' * 64, 1, 'queued')]
    with patch(
        'api.repositories.runtime_governance.workspace_db_conn',
        return_value=connection(replay),
    ):
        result = enqueue_job(
            tenant_id='tenant-one',
            owner_ref='owner:1',
            job_type='email',
            payload_digest='a' * 64,
            payload_schema=1,
            idempotency_key='job-1',
            available_at=NOW,
        )
    assert result['replayed'] is True


def test_iso_schedule_idempotency_key_is_canonical_safe_and_exactly_stable():
    raw = f'schedule:{UUID(int=9)}:2026-09-08T00:00:00+00:00'
    stored = _stored_idempotency_key(raw)
    assert stored.startswith('schedule-iso:')
    assert stored == _stored_idempotency_key(raw)
    assert '+' not in stored
    assert len(stored) < 128

    cursor = MagicMock()
    cursor.fetchone.side_effect = [('active',), None, (100, True), (JOB_ID,)]
    with patch(
        'api.repositories.runtime_governance.workspace_db_conn',
        return_value=connection(cursor),
    ):
        enqueue_job(
            tenant_id='tenant-one',
            owner_ref=f'schedule:{UUID(int=9)}',
            job_type='operations.collect',
            payload_digest='a' * 64,
            payload_schema=1,
            idempotency_key=raw,
            available_at=NOW,
        )
    assert cursor.execute.call_args_list[2].args[1] == ('tenant-one', stored)
    assert cursor.execute.call_args_list[5].args[1][5] == stored


def test_enqueue_capacity_is_serialized_and_only_matching_schedule_reservation_converts():
    full = MagicMock()
    full.fetchone.side_effect = [('active',), None, (100, False)]
    with (
        patch(
            'api.repositories.runtime_governance.workspace_db_conn',
            return_value=connection(full),
        ),
        pytest.raises(RuntimeRepositoryError, match='capacity_exhausted'),
    ):
        enqueue_job(
            tenant_id='tenant-one',
            owner_ref='owner:1',
            job_type='operations.collect',
            payload_digest='a' * 64,
            payload_schema=1,
            idempotency_key='job-full',
            available_at=NOW,
        )
    assert 'schedule-capacity' in full.execute.call_args_list[3].args[1][0]


def test_enqueue_changed_replay_fails_closed():
    cursor = MagicMock()
    cursor.fetchone.side_effect = [('active',), (JOB_ID, 'other', 'email', 'a' * 64, 1, 'queued')]
    with (
        patch(
            'api.repositories.runtime_governance.workspace_db_conn', return_value=connection(cursor)
        ),
        pytest.raises(RuntimeRepositoryError, match='idempotency_conflict'),
    ):
        enqueue_job(
            tenant_id='tenant-one',
            owner_ref='owner:1',
            job_type='email',
            payload_digest='a' * 64,
            payload_schema=1,
            idempotency_key='job-1',
            available_at=NOW,
        )


@pytest.mark.parametrize(
    ('field', 'value'),
    (
        ('owner_ref', '../owner'),
        ('job_type', 'UPPER'),
        ('payload_digest', 'not-a-digest'),
        ('idempotency_key', 'x'),
    ),
)
def test_enqueue_rejects_malformed_durable_identity_before_database(field, value):
    values = {
        'tenant_id': 'tenant-one',
        'owner_ref': 'owner:1',
        'job_type': 'email',
        'payload_digest': 'a' * 64,
        'payload_schema': 1,
        'idempotency_key': 'job-1',
        'available_at': NOW,
    }
    values[field] = value
    with (
        patch('api.repositories.runtime_governance.workspace_db_conn') as connect,
        pytest.raises(RuntimeRepositoryError, match='input_invalid'),
    ):
        enqueue_job(**values)
    connect.assert_not_called()


def test_claim_jobs_validates_limit_and_maps_rows():
    with pytest.raises(RuntimeRepositoryError, match='limit_invalid'):
        claim_jobs(tenant_id='tenant-one', worker='worker-1', now=NOW, limit=0)
    cursor = MagicMock()
    cursor.fetchall.return_value = [(JOB_ID, 'email', 'a' * 64, 1, 2, 1, UUID(int=3))]
    with patch(
        'api.repositories.runtime_governance.workspace_db_conn',
        return_value=connection(cursor),
    ):
        rows = claim_jobs(tenant_id='tenant-one', worker='worker-1', now=NOW)
    assert rows == [
        {
            'jobId': str(JOB_ID),
            'jobType': 'email',
            'payloadDigest': 'a' * 64,
            'payloadSchema': 1,
            'attempts': 2,
            'generation': 1,
            'leaseToken': str(UUID(int=3)),
        }
    ]
    assert 'attempts_exhausted' in cursor.execute.call_args_list[0].args[0]
    assert 'SKIP LOCKED' in cursor.execute.call_args.args[0]
    assert 'lease_expires_at<=NOW()' in cursor.execute.call_args_list[0].args[0]
    assert "NOW()+INTERVAL '15 minutes'" in cursor.execute.call_args.args[0]


def test_settle_job_validates_outcome_and_lease_ownership():
    with pytest.raises(RuntimeRepositoryError, match='outcome_invalid'):
        settle_job(
            tenant_id='tenant-one',
            job_id=JOB_ID,
            worker='worker-1',
            lease_token=UUID(int=3),
            generation=1,
            outcome='unknown',
            now=NOW,
        )
    cursor = MagicMock()
    cursor.fetchone.side_effect = [(2,), ('retry',)]
    with patch(
        'api.repositories.runtime_governance.workspace_db_conn',
        return_value=connection(cursor),
    ):
        assert (
            settle_job(
                tenant_id='tenant-one',
                job_id=JOB_ID,
                worker='worker-1',
                lease_token=UUID(int=3),
                generation=1,
                outcome='retry',
                now=NOW,
                error_code='temporary',
            )
            == 'retry'
        )
    retry_delay = cursor.execute.call_args_list[1].args[1][5]
    assert 20 <= retry_delay <= 24
    assert 'lease_expires_at>NOW()' in cursor.execute.call_args_list[0].args[0]
    assert 'lease_expires_at>NOW()' in cursor.execute.call_args_list[1].args[0]

    lost = MagicMock()
    lost.fetchone.return_value = None
    with (
        patch(
            'api.repositories.runtime_governance.workspace_db_conn', return_value=connection(lost)
        ),
        pytest.raises(RuntimeRepositoryError, match='lease_lost'),
    ):
        settle_job(
            tenant_id='tenant-one',
            job_id=JOB_ID,
            worker='worker-1',
            lease_token=UUID(int=3),
            generation=1,
            outcome='succeeded',
            now=NOW,
        )


def test_job_lease_is_revalidated_and_renewed_immediately_before_work():
    cursor = MagicMock()
    cursor.rowcount = 1
    with patch(
        'api.repositories.runtime_governance.workspace_db_conn',
        return_value=connection(cursor),
    ):
        renew_job_lease(
            tenant_id='tenant-one',
            job_id=JOB_ID,
            worker='worker-1',
            lease_token=UUID(int=3),
            generation=2,
            now=NOW,
        )
    assert 'lease_expires_at>NOW()' in cursor.execute.call_args.args[0]
    assert "NOW()+INTERVAL '15 minutes'" in cursor.execute.call_args.args[0]

    cursor.rowcount = 0
    with (
        patch(
            'api.repositories.runtime_governance.workspace_db_conn',
            return_value=connection(cursor),
        ),
        pytest.raises(RuntimeRepositoryError, match='lease_lost'),
    ):
        renew_job_lease(
            tenant_id='tenant-one',
            job_id=JOB_ID,
            worker='worker-1',
            lease_token=UUID(int=3),
            generation=2,
            now=NOW,
        )


def test_dead_letter_inventory_actions_and_due_schedules():
    cursor = MagicMock()
    cursor.fetchall.return_value = [(JOB_ID, 'email', 'failed', 5, NOW)]
    with patch(
        'api.repositories.runtime_governance.workspace_db_conn',
        return_value=connection(cursor),
    ):
        rows = dead_letters(tenant_id='tenant-one', limit=100)
    assert rows[0]['updatedAt'] == NOW.isoformat()
    assert cursor.execute.call_args.args[1] == ('tenant-one', 25)

    action_cursor = MagicMock()
    action_cursor.rowcount = 1
    with patch(
        'api.repositories.runtime_governance.workspace_db_conn',
        side_effect=lambda **_: connection(action_cursor),
    ):
        assert (
            dead_letter_action(
                tenant_id='tenant-one',
                job_id=JOB_ID,
                action='replay',
                now=NOW,
            )
            == 'queued'
        )
        assert (
            dead_letter_action(
                tenant_id='tenant-one',
                job_id=JOB_ID,
                action='cancel',
                now=NOW,
            )
            == 'cancelled'
        )
    with pytest.raises(RuntimeRepositoryError, match='action_invalid'):
        dead_letter_action(
            tenant_id='tenant-one',
            job_id=JOB_ID,
            action='delete',
            now=NOW,
        )
    action_cursor.rowcount = 0
    with (
        patch(
            'api.repositories.runtime_governance.workspace_db_conn',
            return_value=connection(action_cursor),
        ),
        pytest.raises(RuntimeRepositoryError, match='state_invalid'),
    ):
        dead_letter_action(
            tenant_id='tenant-one',
            job_id=JOB_ID,
            action='replay',
            now=NOW,
        )

    schedules = MagicMock()
    schedules.rowcount = 1
    schedules.fetchone.side_effect = [(NOW,), (1,)]
    schedules.fetchall.return_value = [
        (UUID(int=2), 'daily', 'email', 'UTC', 'every:60', 'once', 'forbid', NOW, None, 3),
    ]
    with patch(
        'api.repositories.runtime_governance.workspace_db_conn',
        return_value=connection(schedules),
    ):
        due = due_schedules(tenant_id='tenant-one', now=NOW, limit=0)
    assert due[0]['scheduledFor'] == NOW.isoformat()
    assert due[0]['lastRunAt'] == NOW.isoformat()
    assert due[0]['revision'] == 4
    assert schedules.execute.call_args_list[3].args[1] == (
        'tenant-one',
        'tenant-one',
        'tenant-one',
        1,
    )

    settled = MagicMock()
    settled.rowcount = 1
    with patch(
        'api.repositories.runtime_governance.workspace_db_conn',
        return_value=connection(settled),
    ):
        settle_schedule_claim(
            tenant_id='tenant-one',
            schedule_id=UUID(int=2),
            claim_token=UUID(int=3),
            revision=4,
            succeeded=False,
            original_next_run_at=NOW,
        )
    assert settled.execute.call_args.args[1] == (
        False,
        NOW,
        'tenant-one',
        str(UUID(int=2)),
        str(UUID(int=3)),
        4,
    )


def test_schedule_policy_validation_and_replace_are_enforced_atomically():
    invalid = MagicMock()
    invalid.rowcount = 1
    invalid.fetchone.side_effect = [(NOW,), (25,)]
    invalid.fetchall.return_value = [
        (UUID(int=2), 'daily', 'email', 'Not/AZone', 'every:60', 'once', 'forbid', NOW, None, 1),
    ]
    with (
        patch(
            'api.repositories.runtime_governance.workspace_db_conn',
            return_value=connection(invalid),
        ),
        pytest.raises(RuntimeRepositoryError, match='timezone_invalid'),
    ):
        due_schedules(tenant_id='tenant-one', now=NOW)

    replacement = MagicMock()
    replacement.rowcount = 1
    replacement.fetchone.side_effect = [(NOW,), (25,)]
    replacement.fetchall.return_value = [
        (UUID(int=2), 'daily', 'email', 'UTC', 'every:60', 'skip', 'replace', NOW, None, 1),
    ]
    with patch(
        'api.repositories.runtime_governance.workspace_db_conn',
        return_value=connection(replacement),
    ):
        claimed = due_schedules(tenant_id='tenant-one', now=NOW)
    assert claimed[0]['missedPolicy'] == 'skip'
    assert claimed[0]['overlapPolicy'] == 'replace'
    assert "state='cancelled'" in replacement.execute.call_args_list[4].args[0]
    assert 'claim_token=%s' in replacement.execute.call_args_list[5].args[0]


def test_schedule_capacity_is_reserved_exactly_and_zero_capacity_is_a_noop():
    full = MagicMock()
    full.fetchone.side_effect = [(NOW,), (0,)]
    with patch(
        'api.repositories.runtime_governance.workspace_db_conn',
        return_value=connection(full),
    ):
        assert due_schedules(tenant_id='tenant-one', now=NOW) == []
    assert len(full.execute.call_args_list) == 3
    assert full.execute.call_args_list[2].args[1] == ('tenant-one', 'tenant-one')

    one_slot = MagicMock()
    one_slot.fetchone.side_effect = [(NOW,), (1,)]
    one_slot.fetchall.return_value = []
    with patch(
        'api.repositories.runtime_governance.workspace_db_conn',
        return_value=connection(one_slot),
    ):
        assert due_schedules(tenant_id='tenant-one', now=NOW, limit=25) == []
    assert one_slot.execute.call_args_list[3].args[1][-1] == 1
    assert 'claim_expires_at>NOW()' in one_slot.execute.call_args_list[2].args[0]


def test_daily_schedule_uses_timezone_and_has_explicit_dst_gap_and_fold_behavior():
    from zoneinfo import ZoneInfo

    berlin = ZoneInfo('Europe/Berlin')
    # 02:30 does not exist on the spring-forward day, so the next valid wall
    # time is the following day rather than an invented instant.
    spring = _next_schedule_run(
        rule='daily:02:30',
        zone=berlin,
        due=datetime(2026, 3, 28, 1, 30, tzinfo=UTC),
        now=datetime(2026, 3, 29, 0, 0, tzinfo=UTC),
        missed='once',
    )
    assert spring.isoformat() == '2026-03-30T02:30:00+02:00'

    # On the fall-back day the first occurrence is selected once; after that
    # occurrence the rule advances to the following day, not fold=1.
    autumn = _next_schedule_run(
        rule='daily:02:30',
        zone=berlin,
        due=datetime(2026, 10, 24, 0, 30, tzinfo=UTC),
        now=datetime(2026, 10, 25, 1, 0, tzinfo=UTC),
        missed='once',
    )
    assert autumn.isoformat() == '2026-10-26T02:30:00+01:00'


def test_retry_jitter_is_deterministic_bounded_and_varies_by_identity():
    first = _retry_delay_seconds(job_id=UUID(int=1), generation=1, attempts=3)
    assert first == _retry_delay_seconds(job_id=UUID(int=1), generation=1, attempts=3)
    assert 40 <= first <= 48
    assert _retry_delay_seconds(job_id=UUID(int=2), generation=1, attempts=3) != first
    assert _retry_delay_seconds(job_id=UUID(int=1), generation=1, attempts=20) == 3600
