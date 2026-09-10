#!/usr/bin/env python3
"""Retain private integrity-bound evidence for the real isolated-E2E lease proof."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

MAX_LOG_BYTES = 1024 * 1024


class EvidenceError(RuntimeError):
    pass


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _commit(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=False
    )
    value = result.stdout.strip()
    if result.returncode or not re.fullmatch(r"[0-9a-f]{40}", value):
        raise EvidenceError("e2e_concurrency_source_invalid")
    status = subprocess.run(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if status.returncode or status.stdout:
        raise EvidenceError("e2e_concurrency_source_not_clean")
    return value


def _validate(destination: Path, commit: str) -> Path:
    manifest = destination / "result.json"
    if destination.is_symlink() or manifest.is_symlink() or not manifest.is_file():
        raise EvidenceError("e2e_concurrency_evidence_invalid")
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    files = payload.get("files")
    supplied = payload.get("evidenceDigest")
    unsigned = {key: value for key, value in payload.items() if key != "evidenceDigest"}
    expected = hashlib.sha256(
        json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    if (
        payload.get("schemaVersion") != 1
        or payload.get("status") != "passed"
        or payload.get("sourceCommit") != commit
        or payload.get("ownerExitCode") != 0
        or payload.get("contenderExitCode") != 3
        or payload.get("finalInventory") != "empty"
        or supplied != expected
        or not isinstance(files, list)
        or {item.get("name") for item in files} != {"owner.log", "contender.log"}
        or {item.name for item in destination.iterdir()} != {
            "owner.log",
            "contender.log",
            "result.json",
        }
    ):
        raise EvidenceError("e2e_concurrency_evidence_invalid")
    if os.name != "nt" and (
        destination.stat().st_uid != os.getuid() or destination.stat().st_mode & 0o077
    ):
        raise EvidenceError("e2e_concurrency_evidence_permissions_invalid")
    for item in files:
        member = destination / item["name"]
        if (
            member.is_symlink()
            or not member.is_file()
            or member.stat().st_size != item.get("bytes")
            or _digest(member) != item.get("sha256")
            or member.stat().st_size > MAX_LOG_BYTES
            or (os.name != "nt" and (member.stat().st_uid != os.getuid() or member.stat().st_mode & 0o077))
        ):
            raise EvidenceError("e2e_concurrency_evidence_changed")
    return manifest


def record(owner_log: Path, contender_log: Path, root: Path | None = None) -> Path:
    project_root = (root or Path(__file__).resolve().parents[2]).resolve()
    commit = _commit(project_root)
    evidence_root = project_root / ".artifacts" / "feature-106-e2e-concurrency"
    evidence_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    evidence_root.chmod(0o700)
    destination = evidence_root / commit
    if destination.exists():
        return _validate(destination, commit)
    logs = {"owner.log": owner_log.read_bytes(), "contender.log": contender_log.read_bytes()}
    if any(len(value) > MAX_LOG_BYTES for value in logs.values()):
        raise EvidenceError("e2e_concurrency_log_too_large")
    if b"4 passed" not in logs["owner.log"] or b"fixed isolated E2E project is already in use" not in logs["contender.log"]:
        raise EvidenceError("e2e_concurrency_result_invalid")
    with tempfile.TemporaryDirectory(prefix=f".{commit}.", dir=evidence_root) as raw_stage:
        stage = Path(raw_stage)
        files = []
        for name, value in logs.items():
            member = stage / name
            member.write_bytes(value)
            member.chmod(0o600)
            files.append({"name": name, "bytes": len(value), "sha256": _digest(member)})
        payload = {
            "schemaVersion": 1,
            "status": "passed",
            "sourceCommit": commit,
            "ownerExitCode": 0,
            "contenderExitCode": 3,
            "finalInventory": "empty",
            "files": sorted(files, key=lambda item: item["name"]),
        }
        payload["evidenceDigest"] = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        manifest = stage / "result.json"
        manifest.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        manifest.chmod(0o600)
        stage.rename(destination)
        destination.chmod(0o700)
    return _validate(destination, commit)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("ERROR:e2e_concurrency_arguments_invalid")
        return 2
    try:
        print(record(Path(argv[0]), Path(argv[1])))
    except (EvidenceError, OSError, json.JSONDecodeError) as exc:
        print(f"ERROR:{type(exc).__name__}:{exc}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
