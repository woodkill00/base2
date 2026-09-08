#!/usr/bin/env python3
"""Validate production budgets and bounded synthetic assurance operations."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class AssuranceError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def create_ephemeral_approval(
    *,
    source_commit: str,
    environment: str,
    owned_resources: list[str],
    expires_at: datetime,
    owner: str,
    key: bytes,
) -> dict[str, Any]:
    if (
        not re.fullmatch(r"[0-9a-f]{40}", source_commit or "")
        or environment not in {"preview", "staging"}
        or not owned_resources
        or expires_at.tzinfo is None
        or not re.fullmatch(r"[A-Za-z0-9._-]{3,127}", owner or "")
        or len(key) < 32
    ):
        raise AssuranceError("ephemeral:approval_invalid")
    resources = sorted(set(owned_resources))
    if any(
        not re.fullmatch(r"[a-z][a-z0-9-]{2,62}", item or "")
        or re.search(r"(^|-)(prod|production|live)(-|$)", item)
        for item in resources
    ):
        raise AssuranceError("ephemeral:resource_invalid")
    approval = {
        "sourceCommit": source_commit,
        "environment": environment,
        "ownedResources": resources,
        "expiresAt": expires_at.astimezone(UTC).isoformat(),
        "owner": owner,
        "action": "ephemeral-canary",
    }
    approval["signature"] = hmac.new(key, _canonical(approval), hashlib.sha256).hexdigest()
    return approval


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
    approval: dict[str, Any],
    now: datetime,
    approval_key: bytes,
    plan_key: bytes,
) -> dict[str, Any]:
    if environment == "production":
        raise AssuranceError("ephemeral:production_forbidden")
    if len(approval_key) < 32 or len(plan_key) < 32 or approval_key == plan_key:
        raise AssuranceError("ephemeral:key_invalid")
    if not 1 <= hours <= 4 or not 0 < cost_usd <= 5 or not owned_resources:
        raise AssuranceError("ephemeral:bounds_exceeded")
    resources = sorted(set(owned_resources))
    if (
        not re.fullmatch(r"[0-9a-f]{40}", source_commit or "")
        or environment not in {"preview", "staging"}
        or any(
            not re.fullmatch(r"[a-z][a-z0-9-]{2,62}", item or "")
            or re.search(r"(^|-)(prod|production|live)(-|$)", item)
            for item in resources
        )
    ):
        raise AssuranceError("ephemeral:identity_invalid")
    if not isinstance(approval, dict) or set(approval) != {
        "sourceCommit",
        "environment",
        "ownedResources",
        "expiresAt",
        "owner",
        "action",
        "signature",
    }:
        raise AssuranceError("ephemeral:approval_required")
    unsigned_approval = {key: approval[key] for key in approval if key != "signature"}
    expected_approval = hmac.new(
        approval_key, _canonical(unsigned_approval), hashlib.sha256
    ).hexdigest()
    try:
        expiry = datetime.fromisoformat(str(approval["expiresAt"]))
    except ValueError as exc:
        raise AssuranceError("ephemeral:approval_invalid") from exc
    if (
        not hmac.compare_digest(str(approval["signature"]), expected_approval)
        or approval["sourceCommit"] != source_commit
        or approval["environment"] != environment
        or approval["ownedResources"] != resources
        or approval["action"] != "ephemeral-canary"
        or now.tzinfo is None
        or expiry <= now
    ):
        raise AssuranceError("ephemeral:approval_invalid")
    plan = {
        "sourceCommit": source_commit,
        "environment": environment,
        "maximumHours": hours,
        "costCeilingUsd": cost_usd,
        "ownedResources": resources,
        "approvalSignature": approval["signature"],
        "stagingCertificatesOnly": True,
    }
    plan["signature"] = hmac.new(plan_key, _canonical(plan), hashlib.sha256).hexdigest()
    return plan


def teardown(
    plan: dict[str, Any], *, discovered_resources: list[str], plan_key: bytes
) -> dict[str, Any]:
    if (
        not isinstance(plan, dict)
        or set(plan)
        != {
            "sourceCommit",
            "environment",
            "maximumHours",
            "costCeilingUsd",
            "ownedResources",
            "approvalSignature",
            "stagingCertificatesOnly",
            "signature",
        }
        or len(plan_key) < 32
    ):
        raise AssuranceError("teardown:plan_invalid")
    unsigned = {key: plan[key] for key in plan if key != "signature"}
    expected = hmac.new(plan_key, _canonical(unsigned), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(str(plan["signature"]), expected):
        raise AssuranceError("teardown:plan_integrity")
    owned = set(plan["ownedResources"])
    discovered = set(discovered_resources)
    foreign = sorted(discovered - owned)
    if foreign:
        raise AssuranceError("teardown:unowned_resource")
    missing = sorted(owned - discovered)
    if missing:
        return {"status": "pending", "destroyed": sorted(discovered), "remainingOwned": missing}
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
    required = {"setup", "migrate", "test", "start", "content-workspace-recovery", "production-ready"}
    missing = sorted(name for name in required if name not in bash or name not in powershell)
    return {"status": "passed" if not missing else "failed", "missing": missing}
