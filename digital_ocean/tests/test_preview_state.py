from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from digital_ocean.scripts.python.preview_state import (
    PreservationDenied,
    authorize_destructive_transition,
)

NOW = datetime(2026, 8, 24, 20, 0, tzinfo=UTC)


def declaration(classification, **changes):
    value = {
        "schemaVersion": 1,
        "leaseId": "lease-state-001",
        "classification": classification,
        "retentionExpiresAt": None,
        "encryptionKeyRef": None,
    }
    value.update(changes)
    return value


def snapshot(**changes):
    value = {
        "schemaVersion": 1,
        "leaseId": "lease-state-001",
        "status": "complete",
        "sha256": "a" * 64,
        "size": 42,
        "encrypted": True,
        "keyRef": "vaultwarden://base2/preview-state-key",
        "verifiedAt": "2026-08-24T19:59:00Z",
        "retentionExpiresAt": "2026-08-31T20:00:00Z",
    }
    value.update(changes)
    return value


def test_ephemeral_state_allows_destroy_without_snapshot():
    result = authorize_destructive_transition(declaration("ephemeral"), None, now=NOW)
    assert result == {
        "allowed": True,
        "classification": "ephemeral",
        "requiresRestore": False,
        "snapshotSha256": None,
    }


def test_retained_state_denies_before_retention_expiry():
    item = declaration("retained", retentionExpiresAt=(NOW + timedelta(hours=1)).isoformat())
    with pytest.raises(PreservationDenied, match="retention_active"):
        authorize_destructive_transition(item, None, now=NOW)


def test_retained_state_allows_after_retention_expiry():
    item = declaration("retained", retentionExpiresAt=(NOW - timedelta(seconds=1)).isoformat())
    assert authorize_destructive_transition(item, None, now=NOW)["allowed"] is True


@pytest.mark.parametrize("classification", ["snapshot-before-destroy", "restore-required"])
def test_preserved_state_requires_verified_encrypted_snapshot_and_key(classification):
    key = "vaultwarden://base2/preview-state-key"
    result = authorize_destructive_transition(
        declaration(classification, encryptionKeyRef=key), snapshot(), now=NOW
    )
    assert result["snapshotSha256"] == "a" * 64
    assert result["requiresRestore"] is (classification == "restore-required")


@pytest.mark.parametrize(
    ("receipt", "code"),
    [
        (None, "snapshot_missing"),
        (snapshot(status="interrupted"), "snapshot_incomplete"),
        (snapshot(sha256="corrupt"), "snapshot_invalid"),
        (snapshot(encrypted=False), "snapshot_unencrypted"),
        (snapshot(keyRef="vaultwarden://other/key"), "snapshot_key_mismatch"),
        (snapshot(leaseId="other-lease"), "snapshot_lease_mismatch"),
        (snapshot(retentionExpiresAt="2026-08-24T19:00:00Z"), "snapshot_expired"),
    ],
)
def test_invalid_snapshot_evidence_denies_destroy(receipt, code):
    item = declaration(
        "snapshot-before-destroy",
        encryptionKeyRef="vaultwarden://base2/preview-state-key",
    )
    with pytest.raises(PreservationDenied, match=code):
        authorize_destructive_transition(item, receipt, now=NOW)


def test_missing_encryption_key_reference_denies_before_snapshot_use():
    with pytest.raises(PreservationDenied, match="key_missing"):
        authorize_destructive_transition(declaration("restore-required"), snapshot(), now=NOW)


def test_unknown_fields_and_naive_timestamps_fail_closed():
    with pytest.raises(PreservationDenied, match="declaration_invalid"):
        authorize_destructive_transition(
            {**declaration("ephemeral"), "command": "rm -rf /"}, None, now=NOW
        )
    with pytest.raises(PreservationDenied, match="declaration_invalid"):
        authorize_destructive_transition(
            declaration("retained", retentionExpiresAt="2026-08-25T00:00:00"),
            None,
            now=NOW,
        )
