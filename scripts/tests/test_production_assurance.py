import json
from pathlib import Path

import pytest

from scripts.python.production_assurance import (
    AssuranceError,
    budget_result,
    ephemeral_plan,
    fault_evidence,
    shell_parity,
    teardown,
    validate_policy,
)

ROOT = Path(__file__).resolve().parents[2]


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
    plan = ephemeral_plan(
        source_commit="a" * 40,
        environment="staging",
        hours=2,
        cost_usd=1.5,
        owned_resources=["app-106", "db-106"],
        approval_digest="b" * 64,
    )
    result = teardown(plan, discovered_resources=["app-106", "db-106"])
    assert result["status"] == "destroyed" and not result["remainingOwned"]
    with pytest.raises(AssuranceError, match="unowned"):
        teardown(plan, discovered_resources=["app-106", "foreign-production"])
    with pytest.raises(AssuranceError, match="production"):
        ephemeral_plan(
            source_commit="a" * 40,
            environment="production",
            hours=1,
            cost_usd=1,
            owned_resources=["app-106"],
            approval_digest="b" * 64,
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
