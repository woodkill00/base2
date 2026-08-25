#!/usr/bin/env python3
"""Fail-closed preservation policy for destructive preview transitions."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{6,126}[A-Za-z0-9]$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
KEY_REF = re.compile(r"^vaultwarden://[A-Za-z0-9][A-Za-z0-9._/-]{2,254}$")
CLASSIFICATIONS = {
    "ephemeral",
    "retained",
    "snapshot-before-destroy",
    "restore-required",
}
DECLARATION_FIELDS = {
    "schemaVersion",
    "leaseId",
    "classification",
    "retentionExpiresAt",
    "encryptionKeyRef",
}
SNAPSHOT_FIELDS = {
    "schemaVersion",
    "leaseId",
    "status",
    "sha256",
    "size",
    "encrypted",
    "keyRef",
    "verifiedAt",
    "retentionExpiresAt",
}


class PreservationDenied(RuntimeError):
    """Preservation evidence does not authorize destructive transition."""


def _timestamp(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp must be text")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp requires timezone")
    return parsed.astimezone(UTC)


def _validate_declaration(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != DECLARATION_FIELDS:
        raise ValueError("declaration fields are invalid")
    if value["schemaVersion"] != 1:
        raise ValueError("declaration schema is invalid")
    if not isinstance(value["leaseId"], str) or not SAFE_ID.fullmatch(value["leaseId"]):
        raise ValueError("lease identity is invalid")
    if value["classification"] not in CLASSIFICATIONS:
        raise ValueError("classification is invalid")
    if value["retentionExpiresAt"] is not None:
        _timestamp(value["retentionExpiresAt"])
    key_ref = value["encryptionKeyRef"]
    if key_ref is not None and (not isinstance(key_ref, str) or not KEY_REF.fullmatch(key_ref)):
        raise ValueError("key reference is invalid")
    return value


def _validate_snapshot(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != SNAPSHOT_FIELDS:
        raise ValueError("snapshot fields are invalid")
    if value["schemaVersion"] != 1:
        raise ValueError("snapshot schema is invalid")
    if not isinstance(value["leaseId"], str) or not SAFE_ID.fullmatch(value["leaseId"]):
        raise ValueError("snapshot lease is invalid")
    if value["status"] not in {"complete", "interrupted"}:
        raise ValueError("snapshot status is invalid")
    if not isinstance(value["sha256"], str) or not HEX64.fullmatch(value["sha256"]):
        raise ValueError("snapshot digest is invalid")
    if isinstance(value["size"], bool) or not isinstance(value["size"], int) or value["size"] < 1:
        raise ValueError("snapshot size is invalid")
    if not isinstance(value["encrypted"], bool):
        raise ValueError("snapshot encryption flag is invalid")
    if not isinstance(value["keyRef"], str) or not KEY_REF.fullmatch(value["keyRef"]):
        raise ValueError("snapshot key reference is invalid")
    _timestamp(value["verifiedAt"])
    _timestamp(value["retentionExpiresAt"])
    return value


def authorize_destructive_transition(
    declaration: Any,
    snapshot: Any,
    *,
    now: datetime,
) -> dict[str, Any]:
    """Return bounded preservation authority or raise a stable denial code."""
    try:
        item = _validate_declaration(declaration)
        current = now.astimezone(UTC)
    except (AttributeError, TypeError, ValueError):
        raise PreservationDenied("declaration_invalid") from None

    classification = item["classification"]
    if classification == "ephemeral":
        return {
            "allowed": True,
            "classification": classification,
            "requiresRestore": False,
            "snapshotSha256": None,
        }
    if classification == "retained":
        expiry = item["retentionExpiresAt"]
        if expiry is None:
            raise PreservationDenied("retention_expiry_missing")
        if _timestamp(expiry) > current:
            raise PreservationDenied("retention_active")
        return {
            "allowed": True,
            "classification": classification,
            "requiresRestore": False,
            "snapshotSha256": None,
        }

    key_ref = item["encryptionKeyRef"]
    if key_ref is None:
        raise PreservationDenied("key_missing")
    if snapshot is None:
        raise PreservationDenied("snapshot_missing")
    try:
        receipt = _validate_snapshot(snapshot)
    except (TypeError, ValueError):
        raise PreservationDenied("snapshot_invalid") from None
    if receipt["leaseId"] != item["leaseId"]:
        raise PreservationDenied("snapshot_lease_mismatch")
    if receipt["status"] != "complete":
        raise PreservationDenied("snapshot_incomplete")
    if receipt["encrypted"] is not True:
        raise PreservationDenied("snapshot_unencrypted")
    if receipt["keyRef"] != key_ref:
        raise PreservationDenied("snapshot_key_mismatch")
    if _timestamp(receipt["verifiedAt"]) > current:
        raise PreservationDenied("snapshot_invalid")
    if _timestamp(receipt["retentionExpiresAt"]) <= current:
        raise PreservationDenied("snapshot_expired")
    return {
        "allowed": True,
        "classification": classification,
        "requiresRestore": classification == "restore-required",
        "snapshotSha256": receipt["sha256"],
    }
