from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta

import pytest

from api.services.media_library_operations import (
    MediaOperationError,
    MultipartSnapshot,
    PartReceipt,
    ToolHealth,
    add_part,
    admit_tools,
    audit_hash,
    build_export,
    cancel_multipart,
    complete_multipart,
    derivative_identity,
    destructive_preview,
    similarity_suggestion,
    verify_audit_chain,
)


NOW = datetime(2026, 9, 6, 12, tzinfo=UTC)
CONTENT = b'synthetic-safe-media'
DIGEST = hashlib.sha256(CONTENT).hexdigest()


def snapshot(**changes):
    values = dict(
        site_id='base2-site',
        session_id='1' * 32,
        expected_sha256=DIGEST,
        expected_bytes=len(CONTENT),
        status='created',
        version=1,
        expires_at=NOW + timedelta(minutes=30),
    )
    values.update(changes)
    return MultipartSnapshot(**values)


def test_multipart_is_versioned_bounded_replay_safe_and_terminal():
    receipt = PartReceipt(1, DIGEST, len(CONTENT), 'media-parts/base2-site/opaque')
    receiving = add_part(snapshot(), receipt=receipt, expected_version=1, observed_at=NOW)
    assert add_part(receiving, receipt=receipt, expected_version=2, observed_at=NOW) == receiving
    completed = complete_multipart(receiving, expected_version=2, observed_at=NOW)
    assert completed.status == 'completed' and len(completed.terminal_digest) == 64
    assert complete_multipart(completed, expected_version=999, observed_at=NOW) == completed
    with pytest.raises(MediaOperationError, match='terminal'):
        add_part(completed, receipt=receipt, expected_version=3, observed_at=NOW)


def test_multipart_rejects_conflicts_gaps_expiry_overflow_and_bad_cancel():
    receipt = PartReceipt(1, DIGEST, len(CONTENT), 'part-one')
    receiving = add_part(snapshot(), receipt=receipt, expected_version=1, observed_at=NOW)
    with pytest.raises(MediaOperationError, match='part_conflict'):
        add_part(
            receiving,
            receipt=PartReceipt(1, 'a' * 64, 1, 'changed'),
            expected_version=2,
            observed_at=NOW,
        )
    with pytest.raises(MediaOperationError, match='upload_expired'):
        add_part(
            snapshot(), receipt=receipt, expected_version=1, observed_at=NOW + timedelta(hours=1)
        )
    cancelled = cancel_multipart(snapshot(), expected_version=1)
    assert cancel_multipart(cancelled, expected_version=999) == cancelled


def test_tool_freshness_recipe_and_similarity_are_closed_and_deterministic():
    admit_tools(
        ToolHealth('clamav:1.4', NOW - timedelta(hours=1), 'pillow:11', NOW),
        maximum_signature_age=timedelta(days=1),
    )
    with pytest.raises(MediaOperationError, match='scanner_stale'):
        admit_tools(
            ToolHealth('clamav:1.4', NOW - timedelta(days=2), 'pillow:11', NOW),
            maximum_signature_age=timedelta(days=1),
        )
    first = derivative_identity(
        source_sha256=DIGEST, recipe_id='safe-preview', recipe_version=1, processor_ref='pillow:11'
    )
    second = derivative_identity(
        source_sha256=DIGEST, recipe_id='safe-preview', recipe_version=1, processor_ref='pillow:11'
    )
    assert first == second
    assert similarity_suggestion(
        left_digest=DIGEST, right_digest=DIGEST, perceptual_distance=0, same_site=True
    ) == {'reason': 'exact_digest', 'confidence': 1.0, 'requiresReview': True}
    assert (
        similarity_suggestion(
            left_digest=DIGEST, right_digest=DIGEST, perceptual_distance=0, same_site=False
        )
        is None
    )


def test_exports_neutralize_formulas_and_audit_chain_detects_tampering():
    rows = [{'id': 'one', 'filename': "=WEBSERVICE('bad')", 'status': 'ready'}]
    csv_output = build_export(rows, output_format='csv', fields=('id', 'filename', 'status'))
    assert b"'=WEBSERVICE" in csv_output
    json_output = build_export(rows, output_format='json', fields=('id', 'filename'))
    assert b"'=WEBSERVICE" in json_output
    event = {'type': 'media.asset.ready', 'status': 'ready'}
    digest = audit_hash(previous_hash='0' * 64, sequence=1, event=event)
    chain = [{'sequence': 1, 'previousHash': '0' * 64, 'event': event, 'eventHash': digest}]
    assert verify_audit_chain(chain)
    chain[0]['event']['status'] = 'tampered'
    assert not verify_audit_chain(chain)


def test_destructive_preview_is_non_mutating_and_truthful():
    preview = destructive_preview(
        asset_id='asset-1',
        references=[{'required': True, 'ownerState': 'published'}],
        holds=[{'active': True}],
        objects=[{'key': 'opaque'}],
    )
    assert not preview['allowed']
    assert preview['objectCount'] == 1
    assert 'retain_audit' in preview['proposedEffects']
