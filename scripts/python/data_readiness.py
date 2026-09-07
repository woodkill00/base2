#!/usr/bin/env python3
"""Closed database durability, migration, restore, and retention contracts."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
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
        "transactionTimeoutMs": 60000,
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


def restore_target(
    *, target_id: str, target_class: str, owned: bool, empty: bool
) -> dict[str, Any]:
    if (
        target_class not in TARGET_CLASSES
        or not owned
        or not empty
        or not re.fullmatch(r"[a-z][a-z0-9-]{2,63}", target_id or "")
        or re.search(r"(^|-)(prod|production|live)(-|$)", target_id)
    ):
        raise DataReadinessError("restore:target_denied")
    return {"targetId": target_id, "targetClass": target_class, "isolated": True}


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
