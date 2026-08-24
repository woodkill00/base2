#!/usr/bin/env python3
"""Validate Base2 coverage policy and summarize machine-readable reports."""

from __future__ import annotations

from datetime import date
import json
from pathlib import Path
import re
import sys


SURFACE_ID = re.compile(r"^[a-z][a-z0-9-]+$")
METRICS = ("lines", "branches", "functions", "statements")


def percent(covered: int | float, total: int | float) -> float:
    return round(100.0 * covered / total, 2) if total else 100.0


def summarize_python_coverage(report: dict, excluded_substrings: list[str]) -> dict[str, float]:
    files = [
        item
        for name, item in report.get("files", {}).items()
        if not any(excluded in name.replace("\\", "/") for excluded in excluded_substrings)
    ]
    if not files:
        raise ValueError("coverage report has no in-scope files")
    summaries = [item["summary"] for item in files]
    covered_lines = sum(item.get("covered_lines", 0) for item in summaries)
    statements = sum(item.get("num_statements", 0) for item in summaries)
    covered_branches = sum(item.get("covered_branches", 0) for item in summaries)
    branches = sum(item.get("num_branches", 0) for item in summaries)
    return {
        "lines": percent(covered_lines, statements),
        "statements": percent(covered_lines, statements),
        "branches": percent(covered_branches, branches),
    }


def validate_policy(policy: dict, *, today: date | None = None) -> list[str]:
    findings: list[str] = []
    if policy.get("schemaVersion") != 1:
        findings.append("unsupported schemaVersion")
    surfaces = policy.get("surfaces")
    if not isinstance(surfaces, list) or not surfaces:
        return findings + ["surfaces must be a non-empty list"]
    ids = [surface.get("id") for surface in surfaces]
    if len(ids) != len(set(ids)):
        findings.append("surface IDs must be unique")
    for surface in surfaces:
        surface_id = surface.get("id")
        if not isinstance(surface_id, str) or not SURFACE_ID.fullmatch(surface_id):
            findings.append(f"invalid surface ID {surface_id!r}")
            continue
        if not surface.get("scope") or not surface.get("label"):
            findings.append(f"{surface_id} must have a label and scope")
        if surface.get("baselineStatus") != "measured":
            findings.append(f"{surface_id} baseline is not measured")
        floors = surface.get("floors", {})
        baseline = surface.get("baseline", {})
        if not floors:
            findings.append(f"{surface_id} has no floors")
        for metric, floor in floors.items():
            if metric not in METRICS or not isinstance(floor, (int, float)) or not 0 <= floor <= 100:
                findings.append(f"{surface_id} has invalid {metric} floor")
            elif metric not in baseline:
                findings.append(f"{surface_id} lacks {metric} baseline")
            elif floor > baseline[metric]:
                findings.append(f"{surface_id} {metric} floor exceeds measured baseline")
    changed = policy.get("changedLines", {})
    if not isinstance(changed.get("minimumPercent"), (int, float)) or not 0 <= changed.get("minimumPercent", -1) <= 100:
        findings.append("changed-line minimum is invalid")
    today = today or date.today()
    for exception in policy.get("exceptions", []):
        for field in ("id", "surface", "owner", "rationale", "mitigation", "approvedBy", "expiresOn"):
            if not exception.get(field):
                findings.append(f"coverage exception lacks {field}")
        try:
            if date.fromisoformat(exception.get("expiresOn", "")) < today:
                findings.append(f"coverage exception {exception.get('id', '<unknown>')} is expired")
        except ValueError:
            findings.append(f"coverage exception {exception.get('id', '<unknown>')} has invalid expiry")
    return sorted(set(findings))


def main() -> int:
    if len(sys.argv) >= 3 and sys.argv[1] == "--summarize-python":
        report = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
        print(json.dumps(summarize_python_coverage(report, sys.argv[3:]), sort_keys=True))
        return 0
    repo_root = Path(__file__).resolve().parents[2]
    path = repo_root / "scripts/config/coverage-policy.json"
    policy = json.loads(path.read_text(encoding="utf-8"))
    findings = validate_policy(policy)
    if findings:
        print(f"Coverage policy: FAILED ({len(findings)} finding(s))")
        for finding in findings:
            print(f"- {finding}")
        return 1
    print(f"Coverage policy: PASS ({len(policy['surfaces'])} measured surfaces)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
