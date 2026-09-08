import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from scripts.python.data_readiness import (
    DataReadinessError,
    migration_plan,
    provision_restore_root,
    reconcile_restore,
    recovery_strategy,
    restore_target,
    retention_transition,
    validate_database_policy,
    validate_migration_catalog,
)

ROOT = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 9, 8, 12, tzinfo=UTC)


def test_database_policy_is_closed_encrypted_and_bounded():
    value = json.loads((ROOT / "shared/config/data-readiness-v1.json").read_text())
    assert validate_database_policy(value)["transport"] == "tls-verify-full"
    changed = dict(value)
    changed["password"] = "forbidden"
    with pytest.raises(DataReadinessError, match="policy_invalid"):
        validate_database_policy(changed)


def test_expand_and_migrate_are_compatible_while_contract_needs_approval():
    plan = migration_plan(
        migration_id="add_operations",
        from_schema=18,
        to_schema=19,
        phase="expand",
        compatible_from=18,
        expected_lock_ms=100,
        expected_runtime_ms=5000,
    )
    assert plan["codeRollbackAllowed"] is True
    assert plan["reverseMigrationAllowed"] is False
    with pytest.raises(DataReadinessError, match="destructive_approval"):
        migration_plan(
            migration_id="remove_legacy",
            from_schema=19,
            to_schema=20,
            phase="contract",
            compatible_from=19,
            expected_lock_ms=100,
            expected_runtime_ms=5000,
        )


def test_migration_catalog_is_contiguous_compatible_and_non_destructive():
    catalog = json.loads((ROOT / "shared/config/migration-compatibility-v1.json").read_text())
    assert validate_migration_catalog(catalog)["currentSchema"] == 27
    changed = json.loads(json.dumps(catalog))
    changed["migrations"][1]["toSchema"] = 99
    with pytest.raises(DataReadinessError, match="sequence_invalid"):
        validate_migration_catalog(changed)


def test_pitr_is_truthful_and_has_an_explicit_fallback():
    assert recovery_strategy(["point-in-time-recovery"])["mode"] == "provider-pitr"
    fallback = recovery_strategy([])
    assert fallback == {
        "mode": "encrypted-snapshot-fallback",
        "fallbackRequired": True,
        "status": "pitr-unavailable",
    }


def test_restore_target_rejects_live_ambiguous_unowned_and_nonempty_destinations(tmp_path):
    restore_root = tmp_path / "isolated"
    provision_restore_root(root=restore_root, target_class="isolated")
    target = restore_root / "restore.bin"
    assert restore_target(
        target_id="restore-drill-001", target_class="isolated", target_path=target
    )["isolated"]
    existing = restore_root / "existing.bin"
    existing.write_bytes(b"occupied")
    for overrides in (
        {"target_id": "production"},
        {"target_class": "live"},
        {"target_path": existing},
        {"target_path": Path("relative.bin")},
    ):
        values = {
            "target_id": "restore-drill-001",
            "target_class": "isolated",
            "target_path": target,
            **overrides,
        }
        with pytest.raises(DataReadinessError, match="target_denied"):
            restore_target(**values)


def test_restore_target_requires_an_explicit_secure_restore_root(tmp_path):
    with pytest.raises(DataReadinessError, match="target_denied"):
        restore_target(
            target_id="restore-drill-001",
            target_class="isolated",
            target_path=tmp_path / "unprovisioned" / "restore.bin",
        )
    restore_root = tmp_path / "authorized"
    receipt = provision_restore_root(root=restore_root, target_class="isolated")
    assert receipt["root"] == str(restore_root.resolve())
    with pytest.raises(DataReadinessError, match="root_denied"):
        provision_restore_root(root=restore_root, target_class="isolated")


def test_restore_reconciliation_requires_all_consistent_integrity_bound_components():
    components = {
        name: {"count": index, "digest": format(index + 1, "x") * 64, "consistent": True}
        for index, name in enumerate(
            ("relational", "objects", "search", "configuration", "tenants", "audit")
        )
    }
    result = reconcile_restore(components)
    assert result["status"] == "reconciled"
    changed = json.loads(json.dumps(components))
    changed["objects"]["consistent"] = False
    with pytest.raises(DataReadinessError, match="component_invalid:objects"):
        reconcile_restore(changed)


def test_retention_is_tenant_bound_replay_stable_and_legal_hold_safe():
    first = retention_transition(
        current="active", target="archived", legal_hold=False, tenant_id="tenant-one", now=NOW
    )
    assert first == retention_transition(
        current="active", target="archived", legal_hold=False, tenant_id="tenant-one", now=NOW
    )
    with pytest.raises(DataReadinessError, match="legal_hold"):
        retention_transition(
            current="archived",
            target="erased",
            legal_hold=True,
            tenant_id="tenant-one",
            now=NOW,
        )
