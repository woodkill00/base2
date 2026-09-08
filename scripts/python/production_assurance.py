#!/usr/bin/env python3
"""Validate production budgets and bounded synthetic assurance operations."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class AssuranceError(ValueError):
    pass


def validate_policy(value: Any) -> dict[str, Any]:
    required = {
        "schemaVersion",
        "performanceBudgets",
        "loadModels",
        "actors",
        "scaling",
        "ephemeral",
        "faults",
        "governance",
    }
    if not isinstance(value, dict) or set(value) != required or value.get("schemaVersion") != 1:
        raise AssuranceError("assurance:policy_invalid")
    if value["loadModels"] != ["small", "medium", "large"] or len(value["actors"]) != 5:
        raise AssuranceError("assurance:load_models_invalid")
    if any(
        type(number) not in {int, float} or number <= 0
        for number in value["performanceBudgets"].values()
    ):
        raise AssuranceError("assurance:budget_invalid")
    scaling = value["scaling"]
    if not 0 < scaling["scaleDownAtPercent"] < scaling["scaleUpAtPercent"] <= 100:
        raise AssuranceError("assurance:scaling_invalid")
    ephemeral = value["ephemeral"]
    if (
        not ephemeral["stagingCertificatesOnly"]
        or not ephemeral["exactOwnershipRequired"]
        or not ephemeral["productionForbidden"]
        or not 0 < ephemeral["maximumHours"] <= 8
        or not 0 < ephemeral["maximumCostUsd"] <= 10
    ):
        raise AssuranceError("assurance:ephemeral_invalid")
    if len(value["faults"]) != 11 or len(value["governance"]) != 9:
        raise AssuranceError("assurance:coverage_invalid")
    return json.loads(json.dumps(value, sort_keys=True))


def budget_result(policy: dict[str, Any], measured: dict[str, float]) -> dict[str, Any]:
    budgets = policy["performanceBudgets"]
    if set(measured) != set(budgets):
        raise AssuranceError("assurance:measurement_incomplete")
    failures = sorted(name for name, limit in budgets.items() if measured[name] > limit)
    return {
        "status": "passed" if not failures else "failed",
        "failedBudgets": failures,
        "measured": measured,
    }


def ephemeral_plan(
    *,
    source_commit: str,
    environment: str,
    hours: int,
    cost_usd: float,
    owned_resources: list[str],
    approval_digest: str | None,
) -> dict[str, Any]:
    if environment == "production":
        raise AssuranceError("ephemeral:production_forbidden")
    if not approval_digest:
        raise AssuranceError("ephemeral:approval_required")
    if not 1 <= hours <= 4 or not 0 < cost_usd <= 5 or not owned_resources:
        raise AssuranceError("ephemeral:bounds_exceeded")
    if len(source_commit) != 40 or any(len(item) < 3 for item in owned_resources):
        raise AssuranceError("ephemeral:identity_invalid")
    plan = {
        "sourceCommit": source_commit,
        "environment": environment,
        "maximumHours": hours,
        "costCeilingUsd": cost_usd,
        "ownedResources": sorted(set(owned_resources)),
        "approvalDigest": approval_digest,
        "stagingCertificatesOnly": True,
    }
    plan["digest"] = hashlib.sha256(
        json.dumps(plan, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return plan


def teardown(plan: dict[str, Any], *, discovered_resources: list[str]) -> dict[str, Any]:
    owned = set(plan["ownedResources"])
    discovered = set(discovered_resources)
    foreign = sorted(discovered - owned)
    if foreign:
        raise AssuranceError("teardown:unowned_resource")
    return {
        "status": "destroyed",
        "destroyed": sorted(discovered),
        "remainingOwned": sorted(owned - discovered),
    }


def fault_evidence(
    *, fault: str, recovered: bool, elapsed_seconds: int, objective_seconds: int
) -> dict[str, Any]:
    if elapsed_seconds < 0 or objective_seconds < 1:
        raise AssuranceError("fault:measurement_invalid")
    return {
        "fault": fault,
        "recovered": recovered,
        "elapsedSeconds": elapsed_seconds,
        "objectiveSeconds": objective_seconds,
        "objectiveMet": recovered and elapsed_seconds <= objective_seconds,
        "incidentRequired": not recovered or elapsed_seconds > objective_seconds,
        "residualRiskRequired": True,
    }


def shell_parity(root: Path) -> dict[str, Any]:
    bash = {path.stem for path in (root / "scripts/bash").glob("*.sh")}
    powershell = {path.stem for path in (root / "scripts/powershell").glob("*.ps1")}
    required = {"setup", "migrate", "test", "start", "content-workspace-recovery"}
    missing = sorted(name for name in required if name not in bash or name not in powershell)
    return {"status": "passed" if not missing else "failed", "missing": missing}
