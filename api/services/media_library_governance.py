"""Bounded governance, recovery, encryption, and worker-state contracts."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum
from typing import Any


class MediaGovernanceError(ValueError):
    pass


class JobState(StrEnum):
    QUEUED = 'queued'
    LEASED = 'leased'
    RUNNING = 'running'
    COMPLETED = 'completed'
    RETRYABLE = 'retryable'
    FAILED = 'failed'
    CANCELLED = 'cancelled'


JOB_TRANSITIONS = {
    JobState.QUEUED: {JobState.LEASED, JobState.CANCELLED},
    JobState.LEASED: {JobState.RUNNING, JobState.QUEUED, JobState.CANCELLED},
    JobState.RUNNING: {JobState.COMPLETED, JobState.RETRYABLE, JobState.FAILED},
    JobState.RETRYABLE: {JobState.QUEUED, JobState.FAILED, JobState.CANCELLED},
    JobState.COMPLETED: set(),
    JobState.FAILED: set(),
    JobState.CANCELLED: set(),
}


@dataclass(frozen=True)
class JobSnapshot:
    job_id: str
    site_id: str
    kind: str
    state: JobState
    version: int
    attempt: int
    maximum_attempts: int
    request_digest: str
    lease_expires_at: datetime | None = None
    output_digest: str = ''
    error_code: str = ''


def transition_job(
    job: JobSnapshot,
    *,
    target: JobState,
    expected_version: int,
    observed_at: datetime,
    output_digest: str = '',
    error_code: str = '',
) -> JobSnapshot:
    if job.state is JobState.COMPLETED and target is JobState.COMPLETED:
        if output_digest == job.output_digest:
            return job
        raise MediaGovernanceError('media_job_replay_conflict')
    if expected_version != job.version or target not in JOB_TRANSITIONS[job.state]:
        raise MediaGovernanceError('media_job_transition_invalid')
    if observed_at.tzinfo is None:
        raise MediaGovernanceError('media_time_invalid')
    attempt = job.attempt + (1 if target is JobState.RUNNING else 0)
    if attempt > job.maximum_attempts:
        raise MediaGovernanceError('media_job_attempt_exhausted')
    if target is JobState.COMPLETED and not re.fullmatch(r'[a-f0-9]{64}', output_digest or ''):
        raise MediaGovernanceError('media_job_output_invalid')
    if target in {JobState.RETRYABLE, JobState.FAILED} and not re.fullmatch(
        r'media_[a-z0-9_]{3,63}', error_code or ''
    ):
        raise MediaGovernanceError('media_job_error_invalid')
    return replace(
        job,
        state=target,
        version=job.version + 1,
        attempt=attempt,
        output_digest=output_digest if target is JobState.COMPLETED else job.output_digest,
        error_code=error_code if target in {JobState.RETRYABLE, JobState.FAILED} else '',
        lease_expires_at=None
        if target not in {JobState.LEASED, JobState.RUNNING}
        else job.lease_expires_at,
    )


def recover_expired_lease(job: JobSnapshot, *, observed_at: datetime) -> JobSnapshot:
    if job.state not in {JobState.LEASED, JobState.RUNNING}:
        return job
    if (
        observed_at.tzinfo is None
        or job.lease_expires_at is None
        or job.lease_expires_at.tzinfo is None
    ):
        raise MediaGovernanceError('media_job_lease_invalid')
    if observed_at < job.lease_expires_at:
        return job
    if job.attempt >= job.maximum_attempts:
        return replace(
            job,
            state=JobState.FAILED,
            version=job.version + 1,
            error_code='media_job_attempt_exhausted',
            lease_expires_at=None,
        )
    return replace(job, state=JobState.QUEUED, version=job.version + 1, lease_expires_at=None)


@dataclass(frozen=True)
class QuotaWindow:
    scope: str
    used: int
    maximum: int
    resets_at: datetime


def admit_rate(
    window: QuotaWindow, *, amount: int, observed_at: datetime
) -> tuple[QuotaWindow, int]:
    if (
        not re.fullmatch(
            r'(user|tenant|site|session|object|storage|processing|delivery):[a-z0-9._-]{1,128}',
            window.scope or '',
        )
        or not isinstance(amount, int)
        or isinstance(amount, bool)
        or amount < 1
        or window.used < 0
        or window.maximum < 1
        or observed_at.tzinfo is None
        or window.resets_at.tzinfo is None
    ):
        raise MediaGovernanceError('media_quota_invalid')
    if observed_at >= window.resets_at:
        window = replace(window, used=0)
    if window.used + amount > window.maximum:
        retry = max(1, int((window.resets_at - observed_at).total_seconds()))
        raise MediaGovernanceError(f'media_rate_limited:{retry}')
    return replace(window, used=window.used + amount), 0


@dataclass(frozen=True)
class EncryptionEnvelope:
    object_key: str
    key_ref: str
    key_version: int
    wrapped_data_key_sha256: str
    content_sha256: str
    state: str = 'active'


def rotate_envelope(
    envelope: EncryptionEnvelope,
    *,
    new_key_ref: str,
    new_key_version: int,
    wrapped_data_key_sha256: str,
) -> EncryptionEnvelope:
    if envelope.state != 'active':
        raise MediaGovernanceError('media_key_state_invalid')
    if (
        not re.fullmatch(r'secretref:[a-z][a-z0-9/_-]{2,127}', new_key_ref or '')
        or new_key_version <= envelope.key_version
        or not re.fullmatch(r'[a-f0-9]{64}', wrapped_data_key_sha256 or '')
    ):
        raise MediaGovernanceError('media_key_rotation_invalid')
    return replace(
        envelope,
        key_ref=new_key_ref,
        key_version=new_key_version,
        wrapped_data_key_sha256=wrapped_data_key_sha256,
    )


def revoke_envelope(
    envelope: EncryptionEnvelope, *, expected_key_version: int
) -> EncryptionEnvelope:
    if envelope.key_version != expected_key_version or envelope.state != 'active':
        raise MediaGovernanceError('media_key_state_invalid')
    return replace(envelope, state='revoked')


def backup_manifest(*, site_id: str, members: list[dict[str, Any]]) -> dict[str, Any]:
    if not re.fullmatch(r'[a-z][a-z0-9-]{2,62}', site_id or '') or len(members) > 100_000:
        raise MediaGovernanceError('media_backup_invalid')
    normalized = []
    for member in members:
        if set(member) != {'kind', 'id', 'sha256', 'byteSize'}:
            raise MediaGovernanceError('media_backup_invalid')
        if (
            not re.fullmatch(r'[a-f0-9]{64}', member['sha256'] or '')
            or not 0 <= member['byteSize'] <= 100 * 1024 * 1024
        ):
            raise MediaGovernanceError('media_backup_invalid')
        normalized.append(dict(member))
    normalized.sort(key=lambda item: (item['kind'], item['id']))
    encoded = json.dumps(normalized, sort_keys=True, separators=(',', ':')).encode()
    return {
        'schemaVersion': 1,
        'siteId': site_id,
        'members': normalized,
        'manifestSha256': hashlib.sha256(encoded).hexdigest(),
    }


def verify_isolated_restore(
    manifest: dict[str, Any], *, target_site_id: str, live_site_ids: frozenset[str]
) -> bool:
    if target_site_id in live_site_ids or not target_site_id.endswith('-restore'):
        raise MediaGovernanceError('media_restore_target_invalid')
    rebuilt = backup_manifest(
        site_id=manifest.get('siteId', ''), members=manifest.get('members', [])
    )
    if rebuilt['manifestSha256'] != manifest.get('manifestSha256'):
        raise MediaGovernanceError('media_restore_integrity_failed')
    return True


@dataclass(frozen=True)
class SagaStep:
    name: str
    request_digest: str
    state: str = 'pending'
    result_digest: str = ''


def advance_saga(step: SagaStep, *, result_digest: str) -> SagaStep:
    if step.state == 'completed':
        if step.result_digest == result_digest:
            return step
        raise MediaGovernanceError('media_saga_replay_conflict')
    if step.state not in {'pending', 'retryable'} or not re.fullmatch(
        r'[a-f0-9]{64}', result_digest or ''
    ):
        raise MediaGovernanceError('media_saga_state_invalid')
    return replace(step, state='completed', result_digest=result_digest)


@dataclass(frozen=True)
class AbuseCase:
    case_id: str
    asset_id: str
    reporter_ref: str
    state: str
    reviewer_ref: str = ''
    appeal_ref: str = ''


def review_abuse_case(case: AbuseCase, *, reviewer_ref: str, decision: str) -> AbuseCase:
    if case.state != 'reported' or decision not in {'quarantined', 'dismissed'}:
        raise MediaGovernanceError('media_abuse_transition_invalid')
    if reviewer_ref == case.reporter_ref:
        raise MediaGovernanceError('media_abuse_separation_required')
    return replace(case, state=decision, reviewer_ref=reviewer_ref)


def appeal_abuse_case(case: AbuseCase, *, appellant_ref: str) -> AbuseCase:
    if case.state != 'quarantined' or appellant_ref in {case.reporter_ref, case.reviewer_ref}:
        raise MediaGovernanceError('media_abuse_appeal_invalid')
    return replace(case, state='appealed', appeal_ref=appellant_ref)


def resolve_appeal(case: AbuseCase, *, reviewer_ref: str, restore: bool) -> AbuseCase:
    if case.state != 'appealed' or reviewer_ref in {
        case.reporter_ref,
        case.reviewer_ref,
        case.appeal_ref,
    }:
        raise MediaGovernanceError('media_abuse_separation_required')
    return replace(case, state='restored' if restore else 'removed', reviewer_ref=reviewer_ref)


def data_rights_decision(
    *, owns_asset: bool, shared_references: int, active_hold: bool, retention_expired: bool
) -> dict[str, Any]:
    if shared_references < 0:
        raise MediaGovernanceError('media_data_rights_invalid')
    if not owns_asset:
        return {'action': 'none', 'reason': 'not_owner'}
    if active_hold:
        return {'action': 'anonymize_owner', 'reason': 'retention_hold'}
    if shared_references:
        return {'action': 'anonymize_owner', 'reason': 'shared_reference'}
    if retention_expired:
        return {'action': 'purge_plan', 'reason': 'retention_expired'}
    return {'action': 'soft_delete', 'reason': 'owner_request'}


def media_health_projection(
    *, queued: int, retryable: int, failed: int, oldest_age_seconds: int
) -> dict[str, Any]:
    values = (queued, retryable, failed, oldest_age_seconds)
    if any(not isinstance(item, int) or isinstance(item, bool) or item < 0 for item in values):
        raise MediaGovernanceError('media_health_invalid')
    state = (
        'degraded'
        if failed or oldest_age_seconds > 900
        else 'busy'
        if queued or retryable
        else 'healthy'
    )
    return {
        'schemaVersion': 1,
        'state': state,
        'counts': {'queued': queued, 'retryable': retryable, 'failed': failed},
        'oldestAgeBucket': (
            'over-15m'
            if oldest_age_seconds > 900
            else 'under-15m'
            if oldest_age_seconds
            else 'none'
        ),
    }


def enforce_performance_budget(
    *, query_ms: int, processing_ms: int, peak_bytes: int, output_bytes: int
) -> None:
    values = (query_ms, processing_ms, peak_bytes, output_bytes)
    if any(not isinstance(item, int) or isinstance(item, bool) or item < 0 for item in values):
        raise MediaGovernanceError('media_performance_measurement_invalid')
    if query_ms > 500:
        raise MediaGovernanceError('media_query_budget_exceeded')
    if processing_ms > 30_000:
        raise MediaGovernanceError('media_processing_budget_exceeded')
    if peak_bytes > 512 * 1024 * 1024:
        raise MediaGovernanceError('media_memory_budget_exceeded')
    if output_bytes > 100 * 1024 * 1024:
        raise MediaGovernanceError('media_output_budget_exceeded')
