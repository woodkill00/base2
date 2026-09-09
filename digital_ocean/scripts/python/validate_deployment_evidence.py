#!/usr/bin/env python3
"""Create and verify a complete exact-source local deployment evidence manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path

BASE_REQUIRED = (
    "remote_verify.done",
    "compose-ps.txt",
    "deployment-kind.txt",
    "pre-deploy-head.txt",
    "post-deploy-head.txt",
    "api-migrate.txt",
    "django-migrate.txt",
    "schema-compat-check.json",
    "curl-root.txt",
    "curl-api-health.txt",
    "traefik-env.txt",
    "traefik-dynamic.yml",
    "bootstrap-packages.txt",
    "DO_userdata.json",
    "deploy-mode.json",
)
TEST_REQUIRED = (
    "api-pytest.txt",
    "api-pytest-integration.txt",
    "api-ruff.txt",
    "api-mypy.txt",
    "django-pytest.txt",
)


class EvidenceError(RuntimeError):
    pass


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def create_manifest(root: Path, source_commit: str, *, tests_required: bool) -> Path:
    if (
        root.is_symlink()
        or not root.is_dir()
        or len(source_commit) != 40
        or any(char not in "0123456789abcdef" for char in source_commit)
    ):
        raise EvidenceError("invalid_evidence_boundary")
    required = BASE_REQUIRED + (TEST_REQUIRED if tests_required else ())
    entries = []
    for name in required:
        candidates = list(root.rglob(name))
        if any(path.is_symlink() for path in candidates):
            raise EvidenceError(f"required_evidence_symlink:{name}")
        matches = [path for path in candidates if path.is_file()]
        if not matches:
            raise EvidenceError(f"required_evidence_count:{name}:0")
        identities = {(path.stat().st_size, digest(path)) for path in matches}
        if len(identities) != 1:
            raise EvidenceError(f"required_evidence_divergent:{name}")
        path = min(matches, key=lambda candidate: len(candidate.relative_to(root).parts))
        size = path.stat().st_size
        if size < 1:
            raise EvidenceError(f"required_evidence_empty:{name}")
        entries.append(
            {
                "name": name,
                "path": path.relative_to(root).as_posix(),
                "bytes": size,
                "sha256": digest(path),
            }
        )
    deployed_head = next(entry for entry in entries if entry["name"] == "post-deploy-head.txt")
    if (root / deployed_head["path"]).read_text(encoding="utf-8").strip() != source_commit:
        raise EvidenceError("deployed_source_mismatch")
    _validate_provider_evidence(root, entries)
    payload = {
        "schemaVersion": 1,
        "sourceCommit": source_commit,
        "complete": True,
        "testsRequired": tests_required,
        "files": entries,
    }
    target = root / "remote-evidence-manifest.json"
    temporary = target.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, target)
    verify_manifest(root, target)
    return target


def verify_manifest(root: Path, manifest_path: Path) -> None:
    resolved_root = root.resolve(strict=True)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    source_commit = payload.get("sourceCommit")
    tests_required = payload.get("testsRequired")
    files = payload.get("files")
    if (
        payload.get("schemaVersion") != 1
        or payload.get("complete") is not True
        or not isinstance(tests_required, bool)
        or not isinstance(source_commit, str)
        or len(source_commit) != 40
        or any(char not in "0123456789abcdef" for char in source_commit)
        or not isinstance(files, list)
    ):
        raise EvidenceError("invalid_evidence_manifest")
    required = BASE_REQUIRED + (TEST_REQUIRED if tests_required else ())
    if any(not isinstance(entry, dict) for entry in files):
        raise EvidenceError("invalid_evidence_member")
    if len(files) != len(required) or {entry.get("name") for entry in files} != set(required):
        raise EvidenceError("invalid_evidence_members")
    for entry in files:
        if not isinstance(entry.get("path"), str):
            raise EvidenceError("invalid_evidence_member")
        relative = Path(entry["path"])
        if (
            relative.is_absolute()
            or ".." in relative.parts
            or relative.name != entry["name"]
        ):
            raise EvidenceError("invalid_evidence_path")
        path = root / relative
        component = root
        for part in relative.parts:
            component /= part
            if component.is_symlink():
                raise EvidenceError(f"evidence_member_symlink:{entry['name']}")
        try:
            path.resolve(strict=True).relative_to(resolved_root)
        except (OSError, ValueError) as exc:
            raise EvidenceError(f"evidence_member_outside:{entry['name']}") from exc
        if path.is_symlink() or not path.is_file():
            raise EvidenceError(f"evidence_member_missing:{entry['name']}")
        if path.stat().st_size != entry["bytes"] or digest(path) != entry["sha256"]:
            raise EvidenceError(f"evidence_member_changed:{entry['name']}")
    deployed_head = next(entry for entry in files if entry["name"] == "post-deploy-head.txt")
    if (root / deployed_head["path"]).read_text(encoding="utf-8").strip() != source_commit:
        raise EvidenceError("deployed_source_mismatch")
    _validate_provider_evidence(root, files)


def _validate_provider_evidence(root: Path, entries: list[dict]) -> None:
    by_name = {entry["name"]: root / entry["path"] for entry in entries}
    try:
        provider = json.loads(by_name["DO_userdata.json"].read_text(encoding="utf-8"))
        mode = json.loads(by_name["deploy-mode.json"].read_text(encoding="utf-8"))
    except (KeyError, json.JSONDecodeError, OSError) as exc:
        raise EvidenceError("provider_evidence_invalid") from exc
    digest_value = provider.get("user_data_sha256") if isinstance(provider, dict) else None
    provider_id = provider.get("droplet_id") if isinstance(provider, dict) else None
    provider_ip = provider.get("ip_address") if isinstance(provider, dict) else None
    if (
        not isinstance(provider, dict)
        or "user_data" in provider
        or not isinstance(digest_value, str)
        or len(digest_value) != 64
        or any(char not in "0123456789abcdef" for char in digest_value)
        or not str(provider_id or "").isdigit()
        or not isinstance(provider_ip, str)
        or not provider_ip.strip()
        or not isinstance(mode, dict)
    ):
        raise EvidenceError("provider_evidence_invalid")
    detected = mode.get("detectedExistingProviderId")
    if detected not in (None, "") and str(detected) != str(provider_id):
        raise EvidenceError("provider_identity_mismatch")
    packages = by_name["bootstrap-packages.txt"].read_text(encoding="utf-8").splitlines()
    if not packages or any(
        "=" not in line
        or re.fullmatch(r"[a-z0-9][a-z0-9+.-]*", line.split("=", 1)[0]) is None
        or not line.split("=", 1)[1]
        or any(char.isspace() for char in line)
        for line in packages
    ):
        raise EvidenceError("bootstrap_package_evidence_invalid")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--tests-required", action="store_true")
    args = parser.parse_args(argv)
    try:
        path = create_manifest(args.root, args.source_commit, tests_required=args.tests_required)
    except (EvidenceError, OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"ERROR: {type(error).__name__}")
        return 2
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
