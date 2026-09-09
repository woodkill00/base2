#!/usr/bin/env python3
"""Run and integrity-bind Feature 106 exact-head stability repetitions."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

REPETITIONS = 10
SUITES = {
    "privacy-runtime": (
        ".venv-api/bin/python",
        "-m",
        "pytest",
        "-q",
        "-o",
        "addopts=",
        "api/tests/test_operations_runtime.py",
        "api/tests/test_runtime_governance_repository.py",
        "api/tests/test_settings_validation.py",
    ),
    "backup-release-deployment": (
        ".venv/bin/python",
        "-m",
        "pytest",
        "-q",
        "-o",
        "addopts=",
        "scripts/tests/test_production_backup.py",
        "scripts/tests/test_production_release.py",
        "scripts/tests/test_production_release_cli.py",
        "digital_ocean/tests/test_deploy_config.py",
        "digital_ocean/tests/test_deployment_evidence.py",
        "digital_ocean/tests/test_deployment_mode.py",
        "digital_ocean/tests/test_provider_lease.py",
        "digital_ocean/tests/test_provider_ready.py",
        "digital_ocean/tests/test_release_orchestrator.py",
        "digital_ocean/tests/test_validate_deployment_evidence.py",
    ),
}


class RepetitionError(RuntimeError):
    """Exact-head repetition evidence could not be produced safely."""


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_commit(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    commit = result.stdout.strip()
    if result.returncode or re.fullmatch(r"[0-9a-f]{40}", commit) is None:
        raise RepetitionError("repetition_source_unavailable")
    return commit


def _require_clean(root: Path) -> None:
    result = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode or result.stdout.strip():
        raise RepetitionError("repetition_source_not_clean")


def _test_environment() -> dict[str, str]:
    blocked = re.compile(r"(?:TOKEN|SECRET|PASSWORD|CREDENTIAL|PRIVATE_KEY)", re.I)
    return {key: value for key, value in os.environ.items() if blocked.search(key) is None}


def _validate_existing(path: Path, commit: str) -> Path:
    try:
        payload = json.loads((path / "result.json").read_text(encoding="utf-8"))
        files = payload["files"]
    except (OSError, KeyError, json.JSONDecodeError, TypeError) as exc:
        raise RepetitionError("repetition_evidence_invalid") from exc
    if (
        payload.get("schemaVersion") != 1
        or payload.get("status") != "passed"
        or payload.get("sourceCommit") != commit
        or payload.get("repetitionsPerSuite") != REPETITIONS
        or not isinstance(files, list)
        or len(files) != len(SUITES) * REPETITIONS
    ):
        raise RepetitionError("repetition_evidence_invalid")
    supplied_digest = payload.get("evidenceDigest")
    digest_payload = {key: value for key, value in payload.items() if key != "evidenceDigest"}
    expected_digest = hashlib.sha256(
        json.dumps(digest_payload, separators=(",", ":"), sort_keys=True).encode()
    ).hexdigest()
    expected_names = {
        f"{suite}-{repetition}.log"
        for suite in SUITES
        for repetition in range(1, REPETITIONS + 1)
    }
    if supplied_digest != expected_digest or {entry.get("name") for entry in files} != expected_names:
        raise RepetitionError("repetition_evidence_invalid")
    for entry in files:
        member = path / str(entry.get("name", ""))
        if (
            not member.is_file()
            or member.name != entry.get("name")
            or member.stat().st_size != entry.get("bytes")
            or _digest(member) != entry.get("sha256")
        ):
            raise RepetitionError("repetition_evidence_changed")
    return path / "result.json"


def run(root: Path | None = None) -> Path:
    project_root = (root or Path(__file__).resolve().parents[3]).resolve()
    _require_clean(project_root)
    commit = _source_commit(project_root)
    evidence_root = project_root / ".artifacts" / "feature-106-repetitions"
    destination = evidence_root / commit
    if destination.exists():
        return _validate_existing(destination, commit)
    evidence_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    with tempfile.TemporaryDirectory(prefix=f".{commit}.", dir=evidence_root) as raw_stage:
        stage = Path(raw_stage)
        environment = _test_environment()
        files: list[dict[str, object]] = []
        for suite, command in SUITES.items():
            for repetition in range(1, REPETITIONS + 1):
                result = subprocess.run(
                    command,
                    cwd=project_root,
                    env=environment,
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
                member = stage / f"{suite}-{repetition}.log"
                member.write_text(result.stdout + result.stderr, encoding="utf-8")
                member.chmod(0o600)
                if result.returncode:
                    raise RepetitionError(f"repetition_failed:{suite}:{repetition}")
                files.append(
                    {
                        "bytes": member.stat().st_size,
                        "name": member.name,
                        "sha256": _digest(member),
                    }
                )
        payload = {
            "files": sorted(files, key=lambda entry: str(entry["name"])),
            "repetitionsPerSuite": REPETITIONS,
            "schemaVersion": 1,
            "sourceCommit": commit,
            "status": "passed",
            "suiteCommands": {name: list(command) for name, command in sorted(SUITES.items())},
        }
        canonical = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
        payload["evidenceDigest"] = hashlib.sha256(canonical).hexdigest()
        result_path = stage / "result.json"
        result_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        result_path.chmod(0o600)
        stage.rename(destination)
    return destination / "result.json"


def main() -> int:
    try:
        print(run())
    except (OSError, RepetitionError, subprocess.SubprocessError) as exc:
        print(f"ERROR:{type(exc).__name__}:{exc}")
        return 2
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised through the installed entrypoint
    raise SystemExit(main())
