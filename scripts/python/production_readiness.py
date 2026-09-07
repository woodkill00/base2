#!/usr/bin/env python3
"""Fail-closed Base2 production-readiness inventory and policy validator."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "shared/config/production-readiness-v1.json"
SCHEMA_PATH = ROOT / "shared/schemas/production-readiness-v1.schema.json"
RELEASE_SCHEMA_PATH = ROOT / "shared/schemas/release-bundle-v2.schema.json"

COMMIT = re.compile(r"^[0-9a-f]{40}$")
ENVIRONMENTS = {"development", "test", "preview", "staging", "production"}
ENVIRONMENT_FIELDS = {
    "dataClass",
    "certificateMode",
    "providerAccess",
    "productionAuthority",
}
PROTECTED_ACTIONS = {
    "publish",
    "merge",
    "deploy-live",
    "spend",
    "read-credential",
    "mutate-dns",
    "issue-production-certificate",
    "destructive-migration",
    "destroy-provider-resource",
}
ABSENCE_SURFACES = {
    "routes",
    "navigation",
    "workers",
    "schedules",
    "storageAllocation",
    "credentialResolution",
    "providerActions",
}
TOP_LEVEL = {
    "schemaVersion",
    "planningBaseline",
    "environments",
    "services",
    "modules",
    "siteProfiles",
    "workflows",
    "routeSurfaces",
    "dataStores",
    "trustBoundaries",
    "protectedActions",
    "resourceDefaults",
    "releaseRequiredFields",
    "capabilityAbsence",
}
RESOURCE_FIELDS = {
    "requestTimeoutSeconds",
    "jobLeaseSeconds",
    "maxAttempts",
    "maxConcurrentPerTenant",
    "telemetryRetentionDays",
    "incidentRetentionDays",
    "ephemeralLifetimeMinutes",
    "ephemeralCostCeilingUsd",
}


class ReadinessError(ValueError):
    """The readiness contract is missing, unsafe, or inconsistent."""


def _load_json(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ReadinessError(f"unsafe or missing JSON file: {path.relative_to(ROOT)}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReadinessError(f"invalid JSON file: {path.relative_to(ROOT)}") from exc
    if not isinstance(payload, dict):
        raise ReadinessError(f"JSON root must be an object: {path.relative_to(ROOT)}")
    return payload


def _unique_strings(value: Any, label: str, minimum: int) -> set[str]:
    if (
        not isinstance(value, list)
        or len(value) < minimum
        or any(not isinstance(item, str) or not item for item in value)
        or len(value) != len(set(value))
    ):
        raise ReadinessError(f"{label} must contain unique non-empty strings")
    return set(value)


def repository_inventory(root: Path = ROOT) -> dict[str, set[str]]:
    return {
        "modules": {
            path.parent.name for path in (root / "modules").glob("*/module.json")
        },
        "siteProfiles": {path.stem for path in (root / "site_profiles").glob("*.json")},
        "workflows": {path.name for path in (root / ".github/workflows").glob("*.yml")},
    }


def validate_policy(policy: dict[str, Any], root: Path = ROOT) -> list[str]:
    findings: list[str] = []
    if set(policy) != TOP_LEVEL or policy.get("schemaVersion") != 1:
        findings.append("policy fields or schemaVersion differ from the closed contract")

    baseline = policy.get("planningBaseline")
    if not isinstance(baseline, str) or not COMMIT.fullmatch(baseline):
        findings.append("planningBaseline must be an exact commit")

    environments = policy.get("environments")
    if not isinstance(environments, dict) or set(environments) != ENVIRONMENTS:
        findings.append("environment inventory differs from the closed contract")
    else:
        for name, profile in environments.items():
            if not isinstance(profile, dict) or set(profile) != ENVIRONMENT_FIELDS:
                findings.append(f"environment fields differ: {name}")
                continue
            if name in {"development", "test"}:
                if profile["certificateMode"] != "disabled" or profile["providerAccess"] is not False:
                    findings.append(f"local environment has provider or certificate access: {name}")
            if name in {"preview", "staging"} and profile["certificateMode"] != "staging-only":
                findings.append(f"non-production certificate mode is unsafe: {name}")
            if name != "production" and profile["productionAuthority"] is not False:
                findings.append(f"non-production profile has production authority: {name}")
        production = environments.get("production", {})
        if production.get("productionAuthority") != "separate-activation-only":
            findings.append("production activation is not separately gated")
        if production.get("certificateMode") != "external-approved-only":
            findings.append("production certificate mode is not externally gated")

    minimums = {
        "services": 10,
        "modules": 15,
        "siteProfiles": 3,
        "workflows": 10,
        "routeSurfaces": 9,
        "dataStores": 5,
        "trustBoundaries": 8,
    }
    values: dict[str, set[str]] = {}
    for field, minimum in minimums.items():
        try:
            values[field] = _unique_strings(policy.get(field), field, minimum)
        except ReadinessError as exc:
            findings.append(str(exc))

    inventory = repository_inventory(root)
    for field in ("modules", "siteProfiles", "workflows"):
        if field in values and values[field] != inventory[field]:
            missing = sorted(inventory[field] - values[field])
            stale = sorted(values[field] - inventory[field])
            findings.append(f"{field} inventory drift: missing={missing} stale={stale}")

    try:
        protected = _unique_strings(policy.get("protectedActions"), "protectedActions", 1)
        if protected != PROTECTED_ACTIONS:
            findings.append("protected action inventory differs from the closed contract")
    except ReadinessError as exc:
        findings.append(str(exc))

    try:
        absence = _unique_strings(policy.get("capabilityAbsence"), "capabilityAbsence", 1)
        if absence != ABSENCE_SURFACES:
            findings.append("capability absence surfaces differ from the closed contract")
    except ReadinessError as exc:
        findings.append(str(exc))

    resources = policy.get("resourceDefaults")
    if not isinstance(resources, dict) or set(resources) != RESOURCE_FIELDS:
        findings.append("resource default fields differ from the closed contract")
    else:
        integer_bounds = {
            "requestTimeoutSeconds": (1, 120),
            "jobLeaseSeconds": (30, 3600),
            "maxAttempts": (1, 10),
            "maxConcurrentPerTenant": (1, 64),
            "telemetryRetentionDays": (1, 90),
            "incidentRetentionDays": (30, 2555),
            "ephemeralLifetimeMinutes": (15, 1440),
        }
        for field, (minimum, maximum) in integer_bounds.items():
            value = resources.get(field)
            if not isinstance(value, int) or isinstance(value, bool) or not minimum <= value <= maximum:
                findings.append(f"resource default outside bounds: {field}")
        ceiling = resources.get("ephemeralCostCeilingUsd")
        if not isinstance(ceiling, (int, float)) or isinstance(ceiling, bool) or not 0 < ceiling <= 25:
            findings.append("resource default outside bounds: ephemeralCostCeilingUsd")

    release_fields = policy.get("releaseRequiredFields")
    try:
        release_set = _unique_strings(release_fields, "releaseRequiredFields", 12)
    except ReadinessError as exc:
        findings.append(str(exc))
        release_set = set()
    try:
        release_schema = _load_json(root / "shared/schemas/release-bundle-v2.schema.json")
        schema_required = set(release_schema.get("required", []))
        if release_set != schema_required:
            findings.append("release fields differ from the v2 schema")
        if release_schema.get("additionalProperties") is not False:
            findings.append("release schema must reject unknown fields")
    except ReadinessError as exc:
        findings.append(str(exc))

    try:
        schema = _load_json(root / "shared/schemas/production-readiness-v1.schema.json")
        if set(schema.get("required", [])) != TOP_LEVEL:
            findings.append("readiness schema required fields differ from policy")
        if schema.get("additionalProperties") is not False:
            findings.append("readiness schema must reject unknown fields")
    except ReadinessError as exc:
        findings.append(str(exc))
    return sorted(set(findings))


def baseline_is_ancestor(baseline: str, root: Path = ROOT) -> bool:
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", baseline, "HEAD"],
        cwd=root,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        policy = _load_json(POLICY_PATH)
        findings = validate_policy(policy)
        if not baseline_is_ancestor(str(policy.get("planningBaseline", ""))):
            findings.append("planningBaseline is not an ancestor of HEAD")
    except ReadinessError as exc:
        findings = [str(exc)]
    result = {
        "schemaVersion": 1,
        "status": "failed" if findings else "passed",
        "findings": sorted(set(findings)),
    }
    if args.json:
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    else:
        print(
            f"Production readiness contract: {result['status'].upper()} "
            f"({len(result['findings'])} finding(s))"
        )
        for finding in result["findings"]:
            print(f"- {finding}")
    return 1 if result["findings"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
