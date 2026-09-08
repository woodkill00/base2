import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from scripts.python.production_assurance import (
    AssuranceError,
    budget_result,
    create_ephemeral_approval,
    ephemeral_plan,
    fault_evidence,
    shell_parity,
    teardown,
    validate_policy,
)

ROOT = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 9, 8, tzinfo=UTC)
APPROVAL_KEY = b"a" * 32
PLAN_KEY = b"p" * 32


def policy():
    return validate_policy(
        json.loads((ROOT / "shared/config/production-assurance-v1.json").read_text())
    )


def test_policy_closes_budget_scaling_cost_fault_and_governance_dimensions():
    value = policy()
    assert len(value["performanceBudgets"]) == 12
    assert len(value["faults"]) == 11 and len(value["governance"]) == 9
    assert value["scaling"]["scaleDownAtPercent"] < value["scaling"]["scaleUpAtPercent"]


def test_measurements_are_complete_and_fail_visibly():
    value = policy()
    measured = {name: limit for name, limit in value["performanceBudgets"].items()}
    assert budget_result(value, measured)["status"] == "passed"
    measured["apiP95Milliseconds"] += 1
    assert budget_result(value, measured)["failedBudgets"] == ["apiP95Milliseconds"]
    measured.pop("cpuPercent")
    with pytest.raises(AssuranceError, match="incomplete"):
        budget_result(value, measured)


def test_ephemeral_plan_requires_approval_and_exact_owned_teardown():
    approval = create_ephemeral_approval(
        source_commit="a" * 40,
        environment="staging",
        owned_resources=["app-106", "db-106"],
        expires_at=NOW + timedelta(minutes=30),
        owner="owner-one",
        key=APPROVAL_KEY,
    )
    plan = ephemeral_plan(
        source_commit="a" * 40,
        environment="staging",
        hours=2,
        cost_usd=1.5,
        owned_resources=["app-106", "db-106"],
        approval=approval,
        now=NOW,
        approval_key=APPROVAL_KEY,
        plan_key=PLAN_KEY,
    )
    resources = {"app-106", "db-106"}
    result = teardown(
        plan,
        inventory=lambda: sorted(resources),
        delete=lambda resource: (resources.remove(resource) or f"deleted.{resource}"),
        plan_key=PLAN_KEY,
    )
    assert result["status"] == "destroyed" and not result["remainingOwned"]
    assert result["verifiedInventory"] == [] and len(result["deleted"]) == 2
    with pytest.raises(AssuranceError, match="unowned"):
        teardown(
            plan,
            inventory=lambda: ["app-106", "foreign-production"],
            delete=lambda resource: f"deleted.{resource}",
            plan_key=PLAN_KEY,
        )
    remaining = {"app-106"}
    pending = teardown(
        plan,
        inventory=lambda: sorted(remaining),
        delete=lambda resource: f"pending.{resource}",
        plan_key=PLAN_KEY,
    )
    assert pending == {
        "status": "pending",
        "deleted": [{"resource": "app-106", "receipt": "pending.app-106"}],
        "remainingOwned": ["app-106"],
    }
    changed = {**plan, "costCeilingUsd": 0.01}
    with pytest.raises(AssuranceError, match="integrity"):
        teardown(
            changed,
            inventory=lambda: ["app-106", "db-106"],
            delete=lambda resource: f"deleted.{resource}",
            plan_key=PLAN_KEY,
        )
    with pytest.raises(AssuranceError, match="production"):
        ephemeral_plan(
            source_commit="a" * 40,
            environment="production",
            hours=1,
            cost_usd=1,
            owned_resources=["app-106"],
            approval=approval,
            now=NOW,
            approval_key=APPROVAL_KEY,
            plan_key=PLAN_KEY,
        )
    with pytest.raises(AssuranceError, match="approval"):
        ephemeral_plan(
            source_commit="b" * 40,
            environment="staging",
            hours=1,
            cost_usd=1,
            owned_resources=["app-106", "db-106"],
            approval=approval,
            now=NOW,
            approval_key=APPROVAL_KEY,
            plan_key=PLAN_KEY,
        )


def test_fault_evidence_is_honest_and_links_failed_objectives():
    failed = fault_evidence(
        fault="database", recovered=True, elapsed_seconds=61, objective_seconds=60
    )
    assert (
        not failed["objectiveMet"] and failed["incidentRequired"] and failed["residualRiskRequired"]
    )
    passed = fault_evidence(
        fault="worker", recovered=True, elapsed_seconds=12, objective_seconds=60
    )
    assert passed["objectiveMet"] and not passed["incidentRequired"]


def test_golden_path_has_bash_and_powershell_parity():
    assert shell_parity(ROOT) == {"status": "passed", "missing": []}
