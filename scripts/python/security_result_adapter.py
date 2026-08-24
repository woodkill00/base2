#!/usr/bin/env python3
"""Normalize scanner output into one integrity-bound, fail-closed result."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re


FAMILIES = {"secret", "sast", "dependency", "sbom", "provenance", "image", "dast", "iac"}
SEVERITIES = ("critical", "high", "moderate", "low", "unknown")
COMMIT = re.compile(r"^[0-9a-f]{40}$")


def empty_counts() -> dict[str, int]:
    return {**{severity: 0 for severity in SEVERITIES}, "total": 0}


def add(counts: dict[str, int], severity: str, amount: int = 1) -> None:
    normalized = severity.lower() if isinstance(severity, str) else "unknown"
    if normalized == "medium":
        normalized = "moderate"
    if normalized not in SEVERITIES:
        normalized = "unknown"
    counts[normalized] += amount
    counts["total"] += amount


def sarif_counts(payload: dict, default_severity: str, forced_severity: str | None = None) -> dict[str, int]:
    if payload.get("version") != "2.1.0" or not isinstance(payload.get("runs"), list):
        raise ValueError("invalid SARIF payload")
    counts = empty_counts()
    for run in payload["runs"]:
        if not isinstance(run, dict) or not isinstance(run.get("results", []), list):
            raise ValueError("invalid SARIF run")
        for result in run.get("results", []):
            if forced_severity:
                add(counts, forced_severity)
                continue
            properties = result.get("properties") or {}
            score = properties.get("security-severity")
            if score is not None:
                try:
                    value = float(score)
                except (TypeError, ValueError) as exc:
                    raise ValueError("invalid SARIF security severity") from exc
                severity = "critical" if value >= 9 else "high" if value >= 7 else "moderate" if value >= 4 else "low"
            else:
                severity = {"error": "high", "warning": "moderate", "note": "low", "none": "low"}.get(result.get("level"), default_severity)
            add(counts, severity)
    return counts


def npm_counts(payload: dict) -> dict[str, int]:
    vulnerabilities = (payload.get("metadata") or {}).get("vulnerabilities")
    if not isinstance(vulnerabilities, dict):
        raise ValueError("invalid npm audit payload")
    counts = empty_counts()
    for severity in SEVERITIES:
        value = vulnerabilities.get(severity if severity != "moderate" else "moderate", 0)
        if not isinstance(value, int) or value < 0:
            raise ValueError("invalid npm audit count")
        add(counts, severity, value)
    return counts


def pip_counts(payload: dict) -> dict[str, int]:
    dependencies = payload.get("dependencies")
    if not isinstance(dependencies, list):
        raise ValueError("invalid pip-audit payload")
    counts = empty_counts()
    for dependency in dependencies:
        vulnerabilities = dependency.get("vulns", []) if isinstance(dependency, dict) else None
        if not isinstance(vulnerabilities, list):
            raise ValueError("invalid pip-audit dependency")
        for vulnerability in vulnerabilities:
            aliases = vulnerability.get("aliases", []) if isinstance(vulnerability, dict) else []
            severity = vulnerability.get("severity", "unknown") if isinstance(vulnerability, dict) else "unknown"
            # pip-audit commonly omits severity; an unresolved advisory is never silently green.
            add(counts, severity if severity != "unknown" or aliases else "unknown")
    return counts


def integrity_counts(family: str, payload: dict) -> dict[str, int]:
    if family == "sbom":
        if payload.get("bomFormat") != "CycloneDX" or not isinstance(payload.get("components"), list):
            raise ValueError("invalid CycloneDX payload")
    else:
        subjects = payload.get("subject")
        if not isinstance(subjects, list) or not subjects or not isinstance(payload.get("predicateType"), str):
            raise ValueError("invalid SLSA provenance payload")
        for subject in subjects:
            digest = (subject.get("digest") or {}).get("sha256") if isinstance(subject, dict) else None
            if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
                raise ValueError("invalid provenance subject digest")
    return empty_counts()


def zap_counts(payload: dict) -> dict[str, int]:
    sites = payload.get("site")
    if not isinstance(sites, list):
        raise ValueError("invalid ZAP payload")
    counts = empty_counts()
    mapping = {"4": "critical", "3": "high", "2": "moderate", "1": "low", "0": "low"}
    for site in sites:
        alerts = site.get("alerts", []) if isinstance(site, dict) else None
        if not isinstance(alerts, list):
            raise ValueError("invalid ZAP site")
        for alert in alerts:
            add(counts, mapping.get(str(alert.get("riskcode")), "unknown"))
    return counts


def checkov_counts(payload: dict) -> dict[str, int]:
    failed = (payload.get("results") or {}).get("failed_checks")
    if not isinstance(failed, list):
        raise ValueError("invalid Checkov payload")
    counts = empty_counts()
    for finding in failed:
        add(counts, (finding.get("severity") or "high") if isinstance(finding, dict) else "high")
    return counts


def validate_result(result: dict) -> None:
    expected = {"schemaVersion", "family", "tool", "sourceCommit", "rawArtifactSha256", "status", "counts"}
    if set(result) != expected or result.get("schemaVersion") != 1:
        raise ValueError("invalid normalized result fields")
    if result.get("family") not in FAMILIES or result.get("status") not in {"passed", "failed"}:
        raise ValueError("invalid normalized result identity")
    if not COMMIT.fullmatch(result.get("sourceCommit", "")) or not re.fullmatch(r"[0-9a-f]{64}", result.get("rawArtifactSha256", "")):
        raise ValueError("invalid normalized result digest")
    counts = result.get("counts")
    if not isinstance(counts, dict) or set(counts) != {*SEVERITIES, "total"}:
        raise ValueError("invalid normalized result counts")
    if any(not isinstance(value, int) or value < 0 for value in counts.values()) or counts["total"] != sum(counts[item] for item in SEVERITIES):
        raise ValueError("inconsistent normalized result counts")


def normalize(family: str, format_name: str, payload: dict, raw: bytes, tool: str, source_commit: str) -> dict:
    if family not in FAMILIES or not COMMIT.fullmatch(source_commit):
        raise ValueError("invalid family or source commit")
    if not isinstance(tool, str) or not tool or len(tool) > 80:
        raise ValueError("invalid tool name")
    if format_name == "sarif":
        defaults = {"secret": "critical", "sast": "high", "dependency": "high", "image": "high", "iac": "high"}
        counts = sarif_counts(payload, defaults.get(family, "unknown"), {"secret": "critical", "sast": "high"}.get(family))
    elif format_name == "npm-audit":
        counts = npm_counts(payload)
    elif format_name == "pip-audit":
        counts = pip_counts(payload)
    elif format_name in {"cyclonedx", "slsa"}:
        counts = integrity_counts(family, payload)
    elif format_name == "zap":
        counts = zap_counts(payload)
    elif format_name == "checkov":
        counts = checkov_counts(payload)
    else:
        raise ValueError("unsupported scanner format")
    result = {
        "schemaVersion": 1,
        "family": family,
        "tool": tool,
        "sourceCommit": source_commit,
        "rawArtifactSha256": hashlib.sha256(raw).hexdigest(),
        "status": "failed" if counts["critical"] or counts["high"] or counts["unknown"] else "passed",
        "counts": counts,
    }
    validate_result(result)
    return result


def validate_policy(policy: dict) -> None:
    if policy.get("schemaVersion") != 1 or policy.get("blockingSeverities") != ["critical", "high"]:
        raise ValueError("invalid security adapter policy")
    families = policy.get("families")
    if not isinstance(families, dict) or set(families) != FAMILIES:
        raise ValueError("security adapter policy must define every family exactly once")
    for family, entry in families.items():
        if set(entry) != {"format", "activation"} or not all(isinstance(value, str) and value for value in entry.values()):
            raise ValueError(f"invalid adapter policy for {family}")
    required = {"secret", "sast", "dependency", "sbom"}
    if {family for family, entry in families.items() if entry["activation"] == "required-ci"} != required:
        raise ValueError("invalid required CI adapter family set")


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy-check", action="store_true")
    parser.add_argument("--family", choices=sorted(FAMILIES))
    parser.add_argument("--format")
    parser.add_argument("--tool")
    parser.add_argument("--source-commit")
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[2]
    if args.policy_check:
        validate_policy(json.loads((repo / "scripts/config/security-adapter-policy.json").read_text(encoding="utf-8")))
        print("Security adapter policy: PASS")
        return 0
    if not all((args.family, args.format, args.tool, args.source_commit, args.input, args.output)):
        parser.error("normalization requires family, format, tool, source commit, input, and output")
    raw = args.input.read_bytes()
    payload = json.loads(raw)
    result = normalize(args.family, args.format, payload, raw, args.tool, args.source_commit)
    atomic_json(args.output, result)
    print(f"{args.family}: {result['status'].upper()}")
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
