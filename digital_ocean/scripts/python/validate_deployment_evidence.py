#!/usr/bin/env python3
"""Create and verify a complete exact-source local deployment evidence manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
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
        if relative.is_absolute() or ".." in relative.parts:
            raise EvidenceError("invalid_evidence_path")
        path = root / relative
        if path.is_symlink() or not path.is_file():
            raise EvidenceError(f"evidence_member_missing:{entry['name']}")
        if path.stat().st_size != entry["bytes"] or digest(path) != entry["sha256"]:
            raise EvidenceError(f"evidence_member_changed:{entry['name']}")
    deployed_head = next(entry for entry in files if entry["name"] == "post-deploy-head.txt")
    if (root / deployed_head["path"]).read_text(encoding="utf-8").strip() != source_commit:
        raise EvidenceError("deployed_source_mismatch")


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
