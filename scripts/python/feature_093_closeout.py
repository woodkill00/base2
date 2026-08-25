#!/usr/bin/env python3
"""Build integrity-checked final experience and recovery ledgers from exact evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


class CloseoutError(ValueError):
    pass


EXPERIENCE_CHECKS = {
    "site-profile-builds",
    "visual-harness",
    "visual-baseline-contract",
    "accessibility-matrix-contract",
    "content-pack-contract",
    "interaction-pack-contract",
    "scheduling-pack-contract",
    "engagement-pack-contract",
    "commercial-pack-contract",
    "module-checkpoint",
    "public-experience-contract",
    "browser-compatibility-matrix",
    "public-experience-checkpoint",
    "frontend-build",
}
RECOVERY_CHECKS = {
    "operations-telemetry-contract",
    "recovery-assurance-contract",
    "immutable-release-contract",
    "capacity-assurance-contract",
    "operations-checkpoint",
    "preview-state-contract",
    "providerless-deployment-canary",
}


def _load(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CloseoutError(f"{label}:invalid") from exc
    if not isinstance(payload, dict):
        raise CloseoutError(f"{label}:invalid")
    return payload


def _passed_gate(path: Path, required: set[str]) -> tuple[dict[str, Any], dict[str, dict]]:
    gate = _load(path, "gate")
    if gate.get("overallStatus") != "passed" or not isinstance(gate.get("sourceCommit"), str):
        raise CloseoutError("gate:not_passed")
    checks = {item.get("id"): item for item in gate.get("checks", []) if isinstance(item, dict)}
    missing = sorted(required - set(checks))
    failed = sorted(name for name in required if checks.get(name, {}).get("status") != "passed")
    if missing:
        raise CloseoutError("gate:missing:" + ",".join(missing))
    if failed:
        raise CloseoutError("gate:failed:" + ",".join(failed))
    return gate, checks


def experience_ledger(repo: Path, gate_path: Path) -> dict[str, Any]:
    gate, checks = _passed_gate(gate_path, EXPERIENCE_CHECKS)
    profiles = []
    enabled: set[str] = set()
    for name in ("ember-studio", "northstar-library"):
        payload = _load(repo / "api/site_profiles" / f"{name}.json", f"profile:{name}")
        modules = sorted(item["id"] for item in payload.get("modules", []) if item.get("enabled") is True)
        routes = sorted(item["path"] for item in payload.get("navigation", []))
        if not modules or not routes:
            raise CloseoutError(f"profile:{name}:surface_empty")
        enabled.update(modules)
        profiles.append({"id": name, "modules": modules, "routes": routes})
    inventory = (repo / "specs/093-base2-foundation-hardening/experience-inventory.md").read_text(encoding="utf-8")
    if "zero unexplained public controls" not in inventory:
        raise CloseoutError("experience:unresolved_controls")
    return {
        "schemaVersion": 1,
        "status": "passed",
        "sourceCommit": gate["sourceCommit"],
        "gateEvidenceDigest": gate.get("evidenceDigest"),
        "fixtureBrands": profiles,
        "enabledPackInventory": sorted(enabled),
        "validatedGateChecks": sorted(checks[name]["id"] for name in EXPERIENCE_CHECKS),
        "routeControlA11yVisualPerformanceComplete": True,
        "unresolvedControls": 0,
    }


def recovery_ledger(gate_path: Path, live_path: Path, operations_path: Path) -> dict[str, Any]:
    gate, checks = _passed_gate(gate_path, RECOVERY_CHECKS)
    live = _load(live_path, "live")
    operations = _load(operations_path, "operations")
    trials = live.get("trials")
    if (
        live.get("status") != "passed"
        or live.get("sourceCommit") != gate.get("sourceCommit")
        or live.get("trialCount") != 3
        or not isinstance(trials, list)
        or len(trials) != 3
        or any(
            item.get("state") != "destroyed"
            or item.get("dnsRestored") is not True
            or item.get("zeroProviderResources") is not True
            for item in trials
        )
        or live.get("zeroProviderResources") is not True
        or live.get("dnsRestored") is not True
    ):
        raise CloseoutError("live:teardown_evidence_invalid")
    if (
        operations.get("status") != "passed"
        or operations.get("faultRestoreCycles") != 3
        or operations.get("ownedResourcesAfter") != 0
        or operations.get("temporaryStateRetained") is not False
        or operations.get("providerCalls") != 0
    ):
        raise CloseoutError("operations:evidence_invalid")
    return {
        "schemaVersion": 1,
        "status": "passed",
        "sourceCommit": gate["sourceCommit"],
        "gateEvidenceDigest": gate.get("evidenceDigest"),
        "planDigest": live.get("planDigest"),
        "canaryTeardownObservations": 3,
        "leaseStates": [item["state"] for item in trials],
        "dnsRestored": True,
        "zeroProviderResources": True,
        "estimatedCostMinorUnits": live.get("estimatedCostMinorUnits"),
        "certificateMode": live.get("certificateMode"),
        "backupRestoreRollbackCycles": operations["faultRestoreCycles"],
        "rpoSeconds": operations.get("rpoSeconds"),
        "rtoSecondsCeiling": operations.get("rtoSecondsCeiling"),
        "validatedGateChecks": sorted(checks[name]["id"] for name in RECOVERY_CHECKS),
        "secretValuesEmitted": 0,
    }


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "output": str(path)}, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=("experience", "recovery"))
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--gate", type=Path, required=True)
    parser.add_argument("--live", type=Path)
    parser.add_argument("--operations", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.kind == "experience":
        payload = experience_ledger(args.repo.resolve(), args.gate)
    else:
        if args.live is None or args.operations is None:
            raise CloseoutError("recovery:live_and_operations_required")
        payload = recovery_ledger(args.gate, args.live, args.operations)
    _write(args.output, payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
