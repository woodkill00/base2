import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from api.services.production_workflows import (
    WorkflowError,
    advance_job,
    break_glass,
    job_record,
    notification_decision,
    schedule_decision,
    secret_rotation,
    validate_workflow_policy,
)

ROOT = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 10, 25, 1, 30, tzinfo=UTC)


def test_workflow_policy_has_metadata_only_and_fixed_bounds():
    policy = json.loads((ROOT / 'shared/config/production-workflows-v1.json').read_text())
    assert validate_workflow_policy(policy)['jobs']['maximumAttempts'] == 5
    changed = json.loads(json.dumps(policy))
    changed['credentials'][0]['password'] = 'bad'
    with pytest.raises(WorkflowError):
        validate_workflow_policy(changed)


def test_secret_rotation_and_break_glass_are_short_lived_and_least_authority():
    rotation = secret_rotation(
        old_ref='vaultwarden://base2/db-old',
        new_ref='vaultwarden://base2/db-new',
        overlap_expires_at=NOW + timedelta(hours=1),
        now=NOW,
    )
    assert rotation['oldValueRevocationRequired']
    grant = break_glass(
        action='database.restore',
        owner='owner-1',
        recent_auth=True,
        expires_at=NOW + timedelta(minutes=15),
        now=NOW,
    )
    assert grant['arbitraryCommandAuthority'] is False
    with pytest.raises(WorkflowError):
        break_glass(
            action='database.restore',
            owner='owner-1',
            recent_auth=False,
            expires_at=NOW + timedelta(minutes=15),
            now=NOW,
        )


def test_job_lease_retry_dead_letter_recovery_cancel_and_replay_identity():
    base = job_record(
        tenant_id='tenant-one',
        job_id='export.run',
        owner='worker.export',
        generation=1,
        payload_digest='a' * 64,
        payload_schema=1,
        idempotency_key='export-request-0001',
    )
    leased = advance_job(base, outcome='lease', now=NOW)
    assert advance_job(leased, outcome='success', now=NOW)['state'] == 'succeeded'
    for _ in range(4):
        leased = advance_job(leased, outcome='failure', now=NOW)
        if leased['state'] == 'retry-wait':
            leased = advance_job(leased, outcome='lease', now=NOW)
    leased = advance_job(leased, outcome='failure', now=NOW)
    assert leased['state'] == 'dead-lettered'
    stale = advance_job(base, outcome='lease', now=NOW)
    assert (
        advance_job(stale, outcome='recover-stale', now=NOW + timedelta(minutes=6))['state']
        == 'retry-wait'
    )
    assert advance_job(base, outcome='cancel', now=NOW)['state'] == 'cancelled'


def test_schedule_is_timezone_dst_overlap_and_once_per_local_day_safe():
    due = schedule_decision(
        timezone_name='Europe/Berlin', local_hour=2, last_local_date=None, now=NOW, running=False
    )
    assert due['due'] is True
    assert (
        schedule_decision(
            timezone_name='Europe/Berlin',
            local_hour=2,
            last_local_date=due['localDate'],
            now=NOW + timedelta(hours=1),
            running=False,
        )['reason']
        == 'already-ran'
    )
    assert (
        schedule_decision(
            timezone_name='UTC', local_hour=0, last_local_date=None, now=NOW, running=True
        )['reason']
        == 'overlap'
    )


def test_notification_preferences_quiet_time_security_and_deduplication():
    digest = 'b' * 64
    assert notification_decision(
        category='account.security',
        mandatory_security=True,
        opted_out=True,
        quiet=True,
        prior_digest=None,
        message_digest=digest,
    )['deliver']
    assert (
        notification_decision(
            category='news.update',
            mandatory_security=False,
            opted_out=True,
            quiet=False,
            prior_digest=None,
            message_digest=digest,
        )['status']
        == 'suppressed-preference'
    )
    assert (
        notification_decision(
            category='news.update',
            mandatory_security=False,
            opted_out=False,
            quiet=True,
            prior_digest=None,
            message_digest=digest,
        )['status']
        == 'deferred-quiet-time'
    )
    assert (
        notification_decision(
            category='news.update',
            mandatory_security=False,
            opted_out=False,
            quiet=False,
            prior_digest=digest,
            message_digest=digest,
        )['status']
        == 'deduplicated'
    )
