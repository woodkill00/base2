from contextlib import contextmanager
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest

from api.repositories.runtime_governance import (
    RuntimeRepositoryError,
    claim_jobs,
    dead_letter_action,
    dead_letters,
    due_schedules,
    enqueue_job,
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
    cursor.fetchone.side_effect = [None, (JOB_ID,)]
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
    assert 'pg_advisory_xact_lock' in cursor.execute.call_args_list[0].args[0]

    replay = MagicMock()
    replay.fetchone.return_value = (JOB_ID, 'owner:1', 'email', 'a' * 64, 1, 'queued')
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


def test_enqueue_changed_replay_fails_closed():
    cursor = MagicMock()
    cursor.fetchone.return_value = (JOB_ID, 'other', 'email', 'a' * 64, 1, 'queued')
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
    cursor.fetchone.return_value = ('retry',)
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
    schedules.fetchall.return_value = [
        (UUID(int=2), 'daily', 'email', 'UTC', 'every:60', 'once', 'forbid', NOW, None, 3),
    ]
    with patch(
        'api.repositories.runtime_governance.workspace_db_conn',
        return_value=connection(schedules),
    ):
        due = due_schedules(tenant_id='tenant-one', now=NOW, limit=0)
    assert due[0]['lastRunAt'] is None
    assert due[0]['revision'] == 4
    assert schedules.execute.call_args_list[0].args[1] == ('tenant-one', NOW, NOW, 1)

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
