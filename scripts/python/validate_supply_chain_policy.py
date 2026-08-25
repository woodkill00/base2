#!/usr/bin/env python3
"""Fail-closed license, package, provenance, and generated-artifact policy."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

SHA256 = re.compile(r"^[0-9a-f]{64}$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")
ECOSYSTEMS = {"npm", "python"}


def validate_policy(policy: dict) -> list[str]:
    findings: list[str] = []
    if (
        set(policy)
        != {
            "schemaVersion",
            "allowedLicenses",
            "forbiddenPackages",
            "generatedArtifact",
        }
        or policy.get("schemaVersion") != 1
    ):
        findings.append("invalid supply-chain policy fields")
    allowed = policy.get("allowedLicenses")
    if not isinstance(allowed, dict) or not allowed:
        findings.append("allowedLicenses must be a non-empty object")
    else:
        aliases: set[str] = set()
        for identifier, values in allowed.items():
            if (
                not isinstance(identifier, str)
                or not identifier
                or not isinstance(values, list)
                or not values
            ):
                findings.append("invalid allowed license entry")
                continue
            normalized = [str(value).strip().lower() for value in values]
            if any(not value for value in normalized) or aliases.intersection(normalized):
                findings.append("empty or duplicate license alias")
            aliases.update(normalized)

    forbidden = policy.get("forbiddenPackages")
    if not isinstance(forbidden, dict) or set(forbidden) != ECOSYSTEMS:
        findings.append("forbiddenPackages must define npm and python")
    else:
        for ecosystem, packages in forbidden.items():
            if not isinstance(packages, list) or any(
                not isinstance(name, str) or not name or name != name.lower() for name in packages
            ):
                findings.append(f"invalid {ecosystem} forbidden package list")

    generated = policy.get("generatedArtifact")
    required_fields = {
        "schemaVersion",
        "sourceCommit",
        "generator",
        "inputsDigest",
        "artifactDigest",
        "provenance",
        "verification",
    }
    if not isinstance(generated, dict) or set(generated) != {
        "requiredFields",
        "requiredPredicateType",
        "verificationStatus",
    }:
        findings.append("invalid generatedArtifact policy")
    elif set(generated.get("requiredFields", [])) != required_fields:
        findings.append("generatedArtifact requiredFields are incomplete")
    return sorted(set(findings))


def _allowed_aliases(policy: dict) -> set[str]:
    return {
        str(alias).strip().lower()
        for aliases in policy["allowedLicenses"].values()
        for alias in aliases
    }


def _license_allowed(value: object, policy: dict) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    aliases = _allowed_aliases(policy)
    normalized = value.strip().lower()
    if normalized in aliases:
        return True
    parts = [
        part.strip()
        for part in re.split(r"\s+(?:or|and)\s+|[;,/]", normalized.strip("()"))
        if part.strip()
    ]
    return bool(parts) and all(part.strip("() ") in aliases for part in parts)


def _npm_name(identity: str) -> str:
    if identity.startswith("@"):
        marker = identity.rfind("@")
        return identity[:marker].lower() if marker > 0 else identity.lower()
    return identity.rsplit("@", 1)[0].lower()


def validate_license_report(report: object, ecosystem: str, policy: dict) -> list[str]:
    if ecosystem not in ECOSYSTEMS:
        return ["unknown license ecosystem"]
    findings = validate_policy(policy)
    forbidden = set(policy["forbiddenPackages"][ecosystem])
    rows: list[tuple[str, object]] = []
    if ecosystem == "npm" and isinstance(report, dict):
        rows = [
            (_npm_name(identity), details.get("licenses") if isinstance(details, dict) else None)
            for identity, details in report.items()
        ]
    elif ecosystem == "python" and isinstance(report, list):
        rows = [
            (str(row.get("Name", "")).strip().lower(), row.get("License"))
            for row in report
            if isinstance(row, dict)
        ]
    else:
        return sorted(set([*findings, f"invalid {ecosystem} license report"]))
    if not rows:
        findings.append(f"empty {ecosystem} license report")
    for package, license_value in rows:
        if not package:
            findings.append(f"{ecosystem} package lacks name")
            continue
        if package in forbidden:
            findings.append(f"forbidden {ecosystem} package: {package}")
        if not _license_allowed(license_value, policy):
            findings.append(f"unapproved or unknown license: {ecosystem}:{package}")
    return sorted(set(findings))


def validate_generated_artifact(manifest: object, policy: dict) -> list[str]:
    findings = validate_policy(policy)
    if not isinstance(manifest, dict):
        return sorted(set([*findings, "generated artifact manifest must be an object"]))
    required = set(policy["generatedArtifact"]["requiredFields"])
    if set(manifest) != required:
        findings.append("generated artifact manifest fields do not match policy")
    if manifest.get("schemaVersion") != 1:
        findings.append("invalid generated artifact schemaVersion")
    if not COMMIT.fullmatch(str(manifest.get("sourceCommit", ""))):
        findings.append("invalid generated artifact sourceCommit")
    if not isinstance(manifest.get("generator"), str) or not manifest.get("generator"):
        findings.append("invalid generated artifact generator")
    for field in ("inputsDigest", "artifactDigest"):
        if not SHA256.fullmatch(str(manifest.get(field, ""))):
            findings.append(f"invalid generated artifact {field}")
    provenance = manifest.get("provenance")
    if (
        not isinstance(provenance, dict)
        or provenance.get("predicateType") != policy["generatedArtifact"]["requiredPredicateType"]
    ):
        findings.append("missing or invalid generated artifact provenance")
    else:
        subject = provenance.get("subject")
        digest = (
            (subject[0].get("digest") or {}).get("sha256")
            if isinstance(subject, list) and len(subject) == 1 and isinstance(subject[0], dict)
            else None
        )
        if digest != manifest.get("artifactDigest"):
            findings.append("provenance subject does not bind artifactDigest")
        predicate = provenance.get("predicate")
        if (
            not isinstance(predicate, dict)
            or not (predicate.get("builder") or {}).get("id")
            or not predicate.get("buildType")
        ):
            findings.append("provenance lacks builder or buildType")
    verification = manifest.get("verification")
    if (
        not isinstance(verification, dict)
        or verification.get("status") != policy["generatedArtifact"]["verificationStatus"]
    ):
        findings.append("generated artifact is unsigned or unverified")
    elif not verification.get("signerIdentity") or not SHA256.fullmatch(
        str(verification.get("signatureDigest", ""))
    ):
        findings.append("generated artifact verification is incomplete")
    return sorted(set(findings))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--kind", choices=["policy", "npm-license", "python-license", "generated"], default="policy"
    )
    parser.add_argument("--input")
    parser.add_argument("--output")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    policy = json.loads(
        (root / "scripts/config/supply-chain-policy.json").read_text(encoding="utf-8")
    )
    payload = json.loads(Path(args.input).read_text(encoding="utf-8")) if args.input else None
    if args.kind == "policy":
        findings = validate_policy(policy)
    elif args.kind == "generated":
        findings = validate_generated_artifact(payload, policy)
    else:
        findings = validate_license_report(payload, args.kind.removesuffix("-license"), policy)
    result = {
        "schemaVersion": 1,
        "kind": args.kind,
        "status": "failed" if findings else "passed",
        "findings": findings,
    }
    if args.output:
        Path(args.output).write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    print(f"Supply-chain policy: {result['status'].upper()} ({len(findings)} finding(s))")
    for finding in findings:
        print(f"- {finding}")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
