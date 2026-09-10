#!/usr/bin/env python3
"""Closed database durability, migration, restore, and retention contracts."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DIGEST = re.compile(r"^[0-9a-f]{64}$")
COMPONENTS = {"relational", "objects", "search", "configuration", "tenants", "audit"}
RETENTION_STATES = {"active", "archived", "anonymized", "exported", "erased"}
TARGET_CLASSES = {"isolated", "preview", "test"}


class DataReadinessError(ValueError):
    pass


def validate_database_policy(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {
        "schemaVersion",
        "transport",
        "storageEncryption",
        "pool",
        "roles",
        "backup",
    }:
        raise DataReadinessError("data:policy_invalid")
    if value["schemaVersion"] != 1 or value["transport"] != "tls-verify-full":
        raise DataReadinessError("data:transport_invalid")
    if value["storageEncryption"] != "provider-managed-key-ref":
        raise DataReadinessError("data:encryption_invalid")
    if value["pool"] != {
        "maximumConnections": 40,
        "maximumPerProcess": 10,
        "statementTimeoutMs": 30000,
        "idleTransactionTimeoutMs": 60000,
        "saturationPercent": 85,
    }:
        raise DataReadinessError("data:pool_invalid")
    if value["roles"] != {
        "application": "tenant-crud-no-bypassrls",
        "worker": "bounded-discovery-tenant-mutation",
        "migration": "schema-owner-no-application-login",
        "breakGlass": "disabled-by-default-expiring",
    }:
        raise DataReadinessError("data:roles_invalid")
    if value["backup"] != {
        "maximumAgeHours": 24,
        "retentionDays": 30,
        "restoreTargetClasses": ["isolated", "preview", "test"],
    }:
        raise DataReadinessError("data:backup_invalid")
    return json.loads(json.dumps(value, sort_keys=True))


def migration_plan(
    *,
    migration_id: str,
    from_schema: int,
    to_schema: int,
    phase: str,
    compatible_from: int,
    expected_lock_ms: int,
    expected_runtime_ms: int,
    destructive_approval: bool = False,
) -> dict[str, Any]:
    if (
        not re.fullmatch(r"[a-z][a-z0-9_-]{2,95}", migration_id or "")
        or min(from_schema, to_schema, compatible_from) < 1
        or to_schema < from_schema
        or phase not in {"expand", "migrate", "contract"}
        or compatible_from > from_schema
        or not 0 <= expected_lock_ms <= 5000
        or not 1 <= expected_runtime_ms <= 3_600_000
    ):
        raise DataReadinessError("migration:plan_invalid")
    destructive = phase == "contract"
    if destructive and not destructive_approval:
        raise DataReadinessError("migration:destructive_approval_required")
    return {
        "migrationId": migration_id,
        "fromSchema": from_schema,
        "toSchema": to_schema,
        "phase": phase,
        "compatibleFrom": compatible_from,
        "expectedLockMs": expected_lock_ms,
        "expectedRuntimeMs": expected_runtime_ms,
        "destructive": destructive,
        "reverseMigrationAllowed": False,
        "codeRollbackAllowed": compatible_from <= from_schema,
    }


def validate_migration_catalog(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {
        "schemaVersion",
        "currentSchema",
        "minimumCompatibleSchema",
        "migrations",
    }:
        raise DataReadinessError("migration:catalog_invalid")
    if (
        value["schemaVersion"] != 1
        or type(value["currentSchema"]) is not int
        or type(value["minimumCompatibleSchema"]) is not int
        or not 1 <= value["minimumCompatibleSchema"] <= value["currentSchema"]
        or not isinstance(value["migrations"], list)
        or not value["migrations"]
    ):
        raise DataReadinessError("migration:catalog_invalid")
    expected = value["minimumCompatibleSchema"] + 1
    normalized = []
    for item in value["migrations"]:
        if not isinstance(item, dict) or set(item) != {
            "migrationId",
            "fromSchema",
            "toSchema",
            "phase",
            "compatibleFrom",
            "expectedLockMs",
            "expectedRuntimeMs",
            "destructive",
        }:
            raise DataReadinessError("migration:catalog_invalid")
        plan = migration_plan(
            migration_id=item["migrationId"],
            from_schema=item["fromSchema"],
            to_schema=item["toSchema"],
            phase=item["phase"],
            compatible_from=item["compatibleFrom"],
            expected_lock_ms=item["expectedLockMs"],
            expected_runtime_ms=item["expectedRuntimeMs"],
            destructive_approval=item["destructive"],
        )
        if item["toSchema"] != expected or item["destructive"] != plan["destructive"]:
            raise DataReadinessError("migration:catalog_sequence_invalid")
        normalized.append(item)
        expected += 1
    if normalized[-1]["toSchema"] != value["currentSchema"]:
        raise DataReadinessError("migration:catalog_sequence_invalid")
    return json.loads(json.dumps(value, sort_keys=True))


def recovery_strategy(capabilities: Any) -> dict[str, Any]:
    if not isinstance(capabilities, list) or any(
        not isinstance(item, str) for item in capabilities
    ):
        raise DataReadinessError("recovery:capabilities_invalid")
    if "point-in-time-recovery" in capabilities:
        return {"mode": "provider-pitr", "fallbackRequired": False, "status": "available"}
    return {
        "mode": "encrypted-snapshot-fallback",
        "fallbackRequired": True,
        "status": "pitr-unavailable",
    }


RESTORE_ROOT_MARKER = ".base2-restore-root.json"


def provision_restore_root(*, root: Path, target_class: str) -> dict[str, Any]:
    """Create an explicit, non-overwritable operator boundary for isolated restores."""
    path = Path(root)
    if target_class not in TARGET_CLASSES or target_class != "isolated" or path.is_symlink():
        raise DataReadinessError("restore:root_denied")
    try:
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
        path.chmod(0o700)
        resolved = path.resolve(strict=True)
        marker = resolved / RESTORE_ROOT_MARKER
        payload = json.dumps(
            {"schemaVersion": 1, "root": str(resolved), "targetClass": target_class},
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        descriptor = os.open(marker, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except (FileExistsError, OSError, RuntimeError, ValueError):
        raise DataReadinessError("restore:root_denied") from None
    return {"root": str(resolved), "targetClass": target_class, "marker": str(marker)}


def restore_target(*, target_id: str, target_class: str, target_path: Path) -> dict[str, Any]:
    """Validate a restore destination from observable filesystem state.

    Ownership and emptiness are never accepted as caller-provided booleans. The
    destination must be absent and its nearest existing ancestor must be owned
    by this process and not writable by its group or other users.
    """
    target = Path(target_path)
    ancestor = target.parent
    restore_root = None
    try:
        if not target.is_absolute() or target.exists() or target.is_symlink():
            raise DataReadinessError("restore:target_denied")
        while not ancestor.exists():
            if ancestor == ancestor.parent or ancestor.is_symlink():
                raise DataReadinessError("restore:target_denied")
            ancestor = ancestor.parent
        candidate = ancestor
        while candidate != candidate.parent:
            marker = candidate / RESTORE_ROOT_MARKER
            if marker.is_file() and not marker.is_symlink():
                marker_metadata = marker.stat()
                if (
                    marker_metadata.st_uid != os.geteuid()
                    or stat.S_IMODE(marker_metadata.st_mode) != 0o600
                ):
                    raise DataReadinessError("restore:target_denied")
                declaration = json.loads(marker.read_text(encoding="utf-8"))
                resolved_candidate = candidate.resolve(strict=True)
                if declaration != {
                    "schemaVersion": 1,
                    "root": str(resolved_candidate),
                    "targetClass": target_class,
                }:
                    raise DataReadinessError("restore:target_denied")
                restore_root = resolved_candidate
                break
            candidate = candidate.parent
        if restore_root is None:
            raise DataReadinessError("restore:target_denied")
        resolved_target = target.resolve(strict=False)
        resolved_target.relative_to(restore_root)
        metadata = restore_root.stat()
        securely_owned = metadata.st_uid == os.geteuid() and not (
            stat.S_IMODE(metadata.st_mode) & (stat.S_IWGRP | stat.S_IWOTH)
        )
    except (json.JSONDecodeError, OSError, RuntimeError, ValueError):
        raise DataReadinessError("restore:target_denied") from None
    if (
        target_class not in TARGET_CLASSES
        or not securely_owned
        or not re.fullmatch(r"[a-z][a-z0-9-]{2,63}", target_id or "")
        or re.search(r"(^|-)(prod|production|live)(-|$)", target_id)
    ):
        raise DataReadinessError("restore:target_denied")
    return {
        "targetId": target_id,
        "targetClass": target_class,
        "isolated": True,
        "targetPath": str(resolved_target),
        "restoreRoot": str(restore_root),
        "ownerUid": metadata.st_uid,
    }


def reconcile_restore(components: Any) -> dict[str, Any]:
    if not isinstance(components, dict) or set(components) != COMPONENTS:
        raise DataReadinessError("restore:components_invalid")
    normalized = {}
    for name in sorted(COMPONENTS):
        item = components[name]
        if (
            not isinstance(item, dict)
            or set(item) != {"count", "digest", "consistent"}
            or type(item["count"]) is not int
            or item["count"] < 0
            or not DIGEST.fullmatch(str(item["digest"]))
            or item["consistent"] is not True
        ):
            raise DataReadinessError(f"restore:component_invalid:{name}")
        normalized[name] = item
    return {
        "status": "reconciled",
        "components": normalized,
        "digest": hashlib.sha256(
            json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
    }


def retention_transition(
    *, current: str, target: str, legal_hold: bool, tenant_id: str, now: datetime
) -> dict[str, Any]:
    if (
        current not in RETENTION_STATES
        or target not in RETENTION_STATES
        or not re.fullmatch(r"[a-z][a-z0-9-]{2,62}", tenant_id or "")
        or now.tzinfo is None
    ):
        raise DataReadinessError("retention:transition_invalid")
    allowed = {
        "active": {"archived", "anonymized", "exported"},
        "archived": {"active", "anonymized", "exported", "erased"},
        "anonymized": {"exported", "erased"},
        "exported": {"archived", "erased"},
        "erased": set(),
    }
    if target not in allowed[current]:
        raise DataReadinessError("retention:transition_invalid")
    if legal_hold and target in {"anonymized", "erased"}:
        raise DataReadinessError("retention:legal_hold")
    receipt = {
        "tenantId": tenant_id,
        "from": current,
        "to": target,
        "occurredAt": now.astimezone(UTC).isoformat(),
        "legalHold": legal_hold,
    }
    receipt["digest"] = hashlib.sha256(
        json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return receipt
