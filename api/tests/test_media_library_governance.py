from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from api.security.identity import redact_audit_metadata
from api.services.media_library_governance import (
    AbuseCase,
    EncryptionEnvelope,
    JobSnapshot,
    JobState,
    MediaGovernanceError,
    QuotaWindow,
    SagaStep,
    admit_rate,
    advance_saga,
    appeal_abuse_case,
    backup_manifest,
    data_rights_decision,
    enforce_performance_budget,
    media_health_projection,
    recover_expired_lease,
    resolve_appeal,
    review_abuse_case,
    revoke_envelope,
    rotate_envelope,
    transition_job,
    verify_isolated_restore,
)


NOW = datetime(2026, 9, 6, 12, tzinfo=UTC)
DIGEST = 'a' * 64


def job(**changes):
    values = dict(
        job_id='job-1',
        site_id='base2-site',
        kind='inspect',
        state=JobState.QUEUED,
        version=1,
        attempt=0,
        maximum_attempts=3,
        request_digest=DIGEST,
    )
    values.update(changes)
    return JobSnapshot(**values)


def test_worker_leases_recover_bound_attempts_and_make_completion_idempotent():
    leased = transition_job(job(), target=JobState.LEASED, expected_version=1, observed_at=NOW)
    leased = leased.__class__(**{**leased.__dict__, 'lease_expires_at': NOW + timedelta(minutes=1)})
    running = transition_job(leased, target=JobState.RUNNING, expected_version=2, observed_at=NOW)
    assert (
        recover_expired_lease(running, observed_at=NOW + timedelta(minutes=2)).state
        is JobState.QUEUED
    )
    completed = transition_job(
        running,
        target=JobState.COMPLETED,
        expected_version=3,
        observed_at=NOW,
        output_digest=DIGEST,
    )
    assert (
        transition_job(
            completed,
            target=JobState.COMPLETED,
            expected_version=99,
            observed_at=NOW,
            output_digest=DIGEST,
        )
        == completed
    )
    with pytest.raises(MediaGovernanceError, match='replay_conflict'):
        transition_job(
            completed,
            target=JobState.COMPLETED,
            expected_version=99,
            observed_at=NOW,
            output_digest='b' * 64,
        )


def test_quota_returns_safe_retry_timing_and_resets_window():
    window = QuotaWindow('tenant:base2-site', 9, 10, NOW + timedelta(seconds=30))
    admitted, retry = admit_rate(window, amount=1, observed_at=NOW)
    assert admitted.used == 10 and retry == 0
    with pytest.raises(MediaGovernanceError, match='media_rate_limited:30'):
        admit_rate(admitted, amount=1, observed_at=NOW)
    reset, _ = admit_rate(admitted, amount=1, observed_at=NOW + timedelta(seconds=31))
    assert reset.used == 1


def test_key_rotation_revocation_and_restore_never_accept_plaintext_keys_or_live_targets():
    envelope = EncryptionEnvelope('opaque', 'secretref:base2/media-key', 1, DIGEST, 'b' * 64)
    rotated = rotate_envelope(
        envelope,
        new_key_ref='secretref:base2/media-key-v2',
        new_key_version=2,
        wrapped_data_key_sha256='c' * 64,
    )
    assert revoke_envelope(rotated, expected_key_version=2).state == 'revoked'
    with pytest.raises(MediaGovernanceError, match='rotation_invalid'):
        rotate_envelope(
            envelope, new_key_ref='plaintext', new_key_version=2, wrapped_data_key_sha256=DIGEST
        )
    manifest = backup_manifest(
        site_id='base2-site',
        members=[{'kind': 'asset', 'id': 'one', 'sha256': DIGEST, 'byteSize': 10}],
    )
    assert verify_isolated_restore(
        manifest, target_site_id='base2-site-restore', live_site_ids=frozenset({'base2-site'})
    )
    with pytest.raises(MediaGovernanceError, match='target_invalid'):
        verify_isolated_restore(
            manifest, target_site_id='base2-site', live_site_ids=frozenset({'base2-site'})
        )


def test_saga_replay_and_abuse_review_are_deterministic_and_separated():
    completed = advance_saga(SagaStep('copy', DIGEST), result_digest='b' * 64)
    assert advance_saga(completed, result_digest='b' * 64) == completed
    with pytest.raises(MediaGovernanceError, match='replay_conflict'):
        advance_saga(completed, result_digest='c' * 64)
    case = AbuseCase('case-1', 'asset-1', 'user:reporter', 'reported')
    with pytest.raises(MediaGovernanceError, match='separation_required'):
        review_abuse_case(case, reviewer_ref='user:reporter', decision='quarantined')
    reviewed = review_abuse_case(case, reviewer_ref='user:reviewer', decision='quarantined')
    appealed = appeal_abuse_case(reviewed, appellant_ref='user:owner')
    resolved = resolve_appeal(appealed, reviewer_ref='user:appeal-reviewer', restore=True)
    assert resolved.state == 'restored'


def test_data_rights_respects_shared_references_and_holds_before_deletion():
    assert data_rights_decision(
        owns_asset=True, shared_references=1, active_hold=False, retention_expired=True
    ) == {'action': 'anonymize_owner', 'reason': 'shared_reference'}
    assert (
        data_rights_decision(
            owns_asset=True, shared_references=0, active_hold=True, retention_expired=True
        )['reason']
        == 'retention_hold'
    )
    assert (
        data_rights_decision(
            owns_asset=True, shared_references=0, active_hold=False, retention_expired=True
        )['action']
        == 'purge_plan'
    )


def test_health_and_performance_evidence_are_bounded_and_identifier_free():
    health = media_health_projection(queued=2, retryable=1, failed=0, oldest_age_seconds=30)
    assert health['state'] == 'busy'
    assert 'site' not in str(health).lower() and 'filename' not in str(health).lower()
    enforce_performance_budget(
        query_ms=499,
        processing_ms=29_999,
        peak_bytes=512 * 1024 * 1024,
        output_bytes=100 * 1024 * 1024,
    )
    for field, value, code in (
        ('query_ms', 501, 'query'),
        ('processing_ms', 30_001, 'processing'),
        ('peak_bytes', 512 * 1024 * 1024 + 1, 'memory'),
        ('output_bytes', 100 * 1024 * 1024 + 1, 'output'),
    ):
        values = dict(query_ms=0, processing_ms=0, peak_bytes=0, output_bytes=0)
        values[field] = value
        with pytest.raises(MediaGovernanceError, match=f'media_{code}_budget_exceeded'):
            enforce_performance_budget(**values)


def test_media_sensitive_log_fields_are_centrally_redacted():
    redacted = redact_audit_metadata(
        {
            'filename': 'private-name.png',
            'storage_key': 'media/private/key',
            'grant': 'signed-secret',
            'scanner_detail': 'raw-signature',
            'nested': {'body': 'private-content'},
            'safe': 'media_scan_failed',
        }
    )
    assert redacted['safe'] == 'media_scan_failed'
    assert redacted['nested']['body'] == '[REDACTED]'
    assert 'private' not in str(redacted)
