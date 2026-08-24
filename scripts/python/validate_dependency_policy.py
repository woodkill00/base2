#!/usr/bin/env python3
"""Validate dependency severity, SLA, and exception policy."""

from __future__ import annotations

from datetime import date
import json
from pathlib import Path
import sys


SEVERITIES = ("critical", "high", "moderate", "low")
EXCEPTION_FIELDS = ("id", "ecosystem", "package", "advisory", "severity", "owner", "rationale", "mitigation", "approvedBy", "reviewOn", "expiresOn")


def validate(policy: dict, *, today: date | None = None) -> list[str]:
    findings = []
    if policy.get("schemaVersion") != 1:
        findings.append("unsupported schemaVersion")
    severity_policy = policy.get("severityPolicy", {})
    if set(severity_policy) != set(SEVERITIES):
        findings.append("severity policy must define exactly critical/high/moderate/low")
    for severity in SEVERITIES:
        rule = severity_policy.get(severity, {})
        if not isinstance(rule.get("remediationHours"), int) or rule.get("remediationHours", -1) < 0:
            findings.append(f"{severity} remediation SLA is invalid")
        if severity in ("critical", "high") and (rule.get("blocks") is not True or rule.get("exceptionsAllowed") is not False):
            findings.append(f"{severity} must block without exceptions")
    maximum = policy.get("exceptionMaximumDays")
    if not isinstance(maximum, int) or not 1 <= maximum <= 90:
        findings.append("exceptionMaximumDays must be 1-90")
        maximum = 30
    today = today or date.today()
    seen = set()
    for exception in policy.get("exceptions", []):
        for field in EXCEPTION_FIELDS:
            if not exception.get(field):
                findings.append(f"dependency exception lacks {field}")
        exception_id = exception.get("id", "<unknown>")
        if exception_id in seen:
            findings.append(f"duplicate dependency exception {exception_id}")
        seen.add(exception_id)
        severity = exception.get("severity")
        if severity_policy.get(severity, {}).get("exceptionsAllowed") is not True:
            findings.append(f"dependency exception {exception_id} uses forbidden severity {severity}")
        try:
            review = date.fromisoformat(exception.get("reviewOn", ""))
            expiry = date.fromisoformat(exception.get("expiresOn", ""))
            if review < today:
                findings.append(f"dependency exception {exception_id} review is overdue")
            if expiry < today:
                findings.append(f"dependency exception {exception_id} is expired")
            if (expiry - today).days > maximum:
                findings.append(f"dependency exception {exception_id} exceeds maximum duration")
        except ValueError:
            findings.append(f"dependency exception {exception_id} has invalid dates")
    return sorted(set(findings))


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    policy = json.loads((repo_root / "scripts/config/dependency-policy.json").read_text(encoding="utf-8"))
    findings = validate(policy)
    if findings:
        print(f"Dependency policy: FAILED ({len(findings)} finding(s))")
        for finding in findings:
            print(f"- {finding}")
        return 1
    print(f"Dependency policy: PASS ({len(policy['exceptions'])} active exceptions)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
