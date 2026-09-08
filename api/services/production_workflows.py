"""Least-authority secret, job, schedule, and notification contracts."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

CODE = re.compile(r'^[a-z][a-z0-9_.-]{2,95}$')
REF = re.compile(r'^vaultwarden://[A-Za-z0-9][A-Za-z0-9._/-]{2,254}$')
DIGEST = re.compile(r'^[0-9a-f]{64}$')
JOB_STATES = {'queued', 'leased', 'retry-wait', 'succeeded', 'dead-lettered', 'cancelled'}


class WorkflowError(ValueError):
    pass


def validate_workflow_policy(value: Any) -> dict[str, Any]:
    if (
        not isinstance(value, dict)
        or set(value) != {'schemaVersion', 'credentials', 'jobs', 'schedules', 'notifications'}
        or value.get('schemaVersion') != 1
    ):
        raise WorkflowError('workflow:policy_invalid')
    credentials = value['credentials']
    if not isinstance(credentials, list) or len(credentials) != 6:
        raise WorkflowError('workflow:credentials_invalid')
    seen = set()
    for item in credentials:
        if (
            not isinstance(item, dict)
            or set(item) != {'class', 'owner', 'scope', 'source', 'maximumLifetimeDays'}
            or item['class'] in seen
            or item['source'] != 'vaultwarden-ref'
            or not 1 <= item['maximumLifetimeDays'] <= 90
        ):
            raise WorkflowError('workflow:credentials_invalid')
        seen.add(item['class'])
    if (
        value['jobs']
        != {
            'maximumAttempts': 5,
            'leaseSeconds': 300,
            'maximumConcurrentPerTenant': 8,
            'deadLetterRetentionDays': 30,
        }
        or value['schedules']
        != {
            'maximumCatchUpRuns': 1,
            'maximumLatenessSeconds': 3600,
            'overlap': 'forbid',
        }
        or value['notifications']
        != {
            'maximumAttempts': 5,
            'historyDays': 90,
            'quietTimeDefault': 'respect',
            'securityException': 'mandatory',
        }
    ):
        raise WorkflowError('workflow:bounds_invalid')
    encoded = json.dumps(value).lower()
    if any(marker in encoded for marker in ('password', 'token=', 'secret=')):
        raise WorkflowError('workflow:secret_value_forbidden')
    return json.loads(json.dumps(value, sort_keys=True))


def secret_rotation(
    *, old_ref: str, new_ref: str, overlap_expires_at: datetime, now: datetime
) -> dict[str, Any]:
    if not REF.fullmatch(old_ref or '') or not REF.fullmatch(new_ref or '') or old_ref == new_ref:
        raise WorkflowError('secret:rotation_invalid')
    if (
        now.tzinfo is None
        or overlap_expires_at.tzinfo is None
        or not now < overlap_expires_at <= now + timedelta(hours=24)
    ):
        raise WorkflowError('secret:overlap_invalid')
    return {
        'oldRef': old_ref,
        'newRef': new_ref,
        'overlapExpiresAt': overlap_expires_at.astimezone(UTC).isoformat(),
        'restartRequired': True,
        'oldValueRevocationRequired': True,
    }


def break_glass(
    *, action: str, owner: str, recent_auth: bool, expires_at: datetime, now: datetime
) -> dict[str, Any]:
    if not CODE.fullmatch(action or '') or not re.fullmatch(r'[A-Za-z0-9._-]{3,127}', owner or ''):
        raise WorkflowError('break_glass:scope_invalid')
    if (
        not recent_auth
        or now.tzinfo is None
        or expires_at.tzinfo is None
        or not now < expires_at <= now + timedelta(minutes=30)
    ):
        raise WorkflowError('break_glass:authorization_invalid')
    value = {
        'action': action,
        'owner': owner,
        'expiresAt': expires_at.astimezone(UTC).isoformat(),
        'followUpReviewRequired': True,
        'arbitraryCommandAuthority': False,
    }
    value['digest'] = hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(',', ':')).encode()
    ).hexdigest()
    return value


def job_record(
    *,
    tenant_id: str,
    job_id: str,
    owner: str,
    generation: int,
    payload_digest: str,
    payload_schema: int,
    idempotency_key: str,
) -> dict[str, Any]:
    if (
        not re.fullmatch(r'[a-z][a-z0-9-]{2,62}', tenant_id or '')
        or not CODE.fullmatch(job_id or '')
        or not CODE.fullmatch(owner or '')
        or type(generation) is not int
        or generation < 1
        or not DIGEST.fullmatch(payload_digest or '')
        or payload_schema < 1
        or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:-]{7,127}', idempotency_key or '')
    ):
        raise WorkflowError('job:invalid')
    return {
        'tenantId': tenant_id,
        'jobId': job_id,
        'owner': owner,
        'generation': generation,
        'payloadDigest': payload_digest,
        'payloadSchema': payload_schema,
        'idempotencyKey': idempotency_key,
        'state': 'queued',
        'attempts': 0,
        'leaseExpiresAt': None,
    }


def advance_job(job: dict[str, Any], *, outcome: str, now: datetime) -> dict[str, Any]:
    if job.get('state') not in JOB_STATES or now.tzinfo is None:
        raise WorkflowError('job:state_invalid')
    value = json.loads(json.dumps(job))
    if outcome == 'lease' and value['state'] in {'queued', 'retry-wait'}:
        value['state'] = 'leased'
        value['attempts'] += 1
        value['leaseExpiresAt'] = (now + timedelta(seconds=300)).isoformat()
    elif outcome == 'success' and value['state'] == 'leased':
        value['state'], value['leaseExpiresAt'] = 'succeeded', None
    elif outcome == 'failure' and value['state'] == 'leased':
        value['state'] = 'dead-lettered' if value['attempts'] >= 5 else 'retry-wait'
        value['leaseExpiresAt'] = None
        value['retryAt'] = (
            None
            if value['state'] == 'dead-lettered'
            else (now + timedelta(seconds=min(900, 15 * 2 ** value['attempts']))).isoformat()
        )
    elif (
        outcome == 'recover-stale'
        and value['state'] == 'leased'
        and datetime.fromisoformat(value['leaseExpiresAt']) <= now
    ):
        value['state'], value['leaseExpiresAt'] = 'retry-wait', None
    elif outcome == 'cancel' and value['state'] not in {'succeeded', 'cancelled'}:
        value['state'], value['leaseExpiresAt'] = 'cancelled', None
    else:
        raise WorkflowError('job:transition_invalid')
    return value


def schedule_decision(
    *,
    timezone_name: str,
    local_hour: int,
    last_local_date: str | None,
    now: datetime,
    running: bool,
) -> dict[str, Any]:
    if now.tzinfo is None or not 0 <= local_hour <= 23:
        raise WorkflowError('schedule:time_invalid')
    try:
        local = now.astimezone(ZoneInfo(timezone_name))
    except ZoneInfoNotFoundError as exc:
        raise WorkflowError('schedule:timezone_invalid') from exc
    local_date = local.date().isoformat()
    due = local.hour >= local_hour and last_local_date != local_date and not running
    reason = (
        'due'
        if due
        else 'overlap'
        if running
        else 'already-ran'
        if last_local_date == local_date
        else 'not-due'
    )
    return {
        'due': due,
        'reason': reason,
        'localDate': local_date,
        'timezone': timezone_name,
        'maximumCatchUpRuns': 1,
    }


def notification_decision(
    *,
    category: str,
    mandatory_security: bool,
    opted_out: bool,
    quiet: bool,
    prior_digest: str | None,
    message_digest: str,
) -> dict[str, Any]:
    if (
        not CODE.fullmatch(category or '')
        or not DIGEST.fullmatch(message_digest or '')
        or (prior_digest is not None and not DIGEST.fullmatch(prior_digest))
    ):
        raise WorkflowError('notification:invalid')
    if prior_digest == message_digest:
        return {'status': 'deduplicated', 'deliver': False}
    if opted_out and not mandatory_security:
        return {'status': 'suppressed-preference', 'deliver': False}
    if quiet and not mandatory_security:
        return {'status': 'deferred-quiet-time', 'deliver': False}
    return {'status': 'mandatory-security' if mandatory_security else 'queued', 'deliver': True}
