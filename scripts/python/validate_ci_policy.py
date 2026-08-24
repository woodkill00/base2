#!/usr/bin/env python3
"""Detect nonblocking and mutable GitHub Actions policy defects."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys


ACTION = re.compile(r"^\s*-?\s*uses:\s*([^\s#]+)", re.MULTILINE)
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
JOB = re.compile(r"^  ([a-zA-Z0-9_-]+):\s*$", re.MULTILINE)


def scan_workflow(name: str, text: str, required_jobs: list[str], marker: str) -> list[str]:
    findings = []
    if not re.search(r"^\s{2}pull_request:\s*$", text, re.MULTILINE):
        findings.append(f"{name}: required workflow lacks pull_request trigger")
    jobs_text = text.split("\njobs:\n", 1)[1] if "\njobs:\n" in text else ""
    jobs = set(JOB.findall(jobs_text))
    for job in required_jobs:
        if job not in jobs:
            findings.append(f"{name}: missing required job {job}")
    for line_number, line in enumerate(text.splitlines(), 1):
        if re.search(r"\bcontinue-on-error:\s*true\b", line):
            findings.append(f"{name}:{line_number}: continue-on-error true is forbidden")
        if "|| true" in line and marker not in line:
            findings.append(f"{name}:{line_number}: failure suppression is forbidden")
    for action in ACTION.findall(text):
        if action.startswith("./") or action.startswith("docker://") or "@" not in action:
            continue
        owner_repo, ref = action.rsplit("@", 1)
        if not FULL_SHA.fullmatch(ref):
            findings.append(f"{name}: mutable action ref {owner_repo}@{ref}")
    return findings


def validate(repo_root: Path, policy: dict) -> list[str]:
    findings = []
    workflow_root = repo_root / ".github" / "workflows"
    marker = policy["diagnosticCleanupMarker"]
    for name, jobs in policy["requiredPullRequestWorkflows"].items():
        path = workflow_root / name
        if not path.is_file():
            findings.append(f"{name}: required workflow missing")
            continue
        findings.extend(scan_workflow(name, path.read_text(encoding="utf-8"), jobs, marker))
    return sorted(set(findings))


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    policy = json.loads((repo_root / "scripts/config/ci-policy.json").read_text(encoding="utf-8"))
    findings = validate(repo_root, policy)
    if findings:
        print(f"CI policy: FAILED ({len(findings)} finding(s))")
        for finding in findings:
            print(f"- {finding}")
        return 1
    print("CI policy: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
