#!/usr/bin/env python3
"""Measure the legacy full local test path against a docs-only optimized run."""

from __future__ import annotations

import hashlib
import fcntl
import json
import os
import re
import statistics
import stat
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.python.assurance_orchestrator import (
    AssuranceError,
    Change,
    _prune_private_directories,
    _redact_output,
    _sha,
    benchmark_report,
    build_plan,
    load_graph,
)
from scripts.python.run_complete_gate import (
    open_private_directory,
    private_atomic_json,
    private_write,
    validate_gate_evidence,
    validate_manifest,
)

MAX_LOG_BYTES = 4 * 1024 * 1024
MUTATIONS = {
    "api/security/identity.py": "security-policy",
    "api/repositories/tenant_lifecycle.py": "security-policy",
    "api/migrations/sql/099_mutation.sql": "migration-contract",
    "react-app/src/index.css": "visual-full",
    ".github/workflows/security.yml": "ci-policy",
    "digital_ocean/scripts/python/orchestrate_deploy.py": "deployment-contract",
    "scripts/python/assurance_orchestrator.py": "assurance-tests",
}
ROUTINE_FIXTURES = (
    "docs/TESTING.md",
    "docs/ARCHITECTURE.md",
    "specs/107-efficient-assurance-orchestrator/quickstart.md",
)


def _git(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments], cwd=root, capture_output=True, text=True, check=False, timeout=30
    )
    if result.returncode:
        raise AssuranceError("benchmark_git_failed")
    return result.stdout.strip()


def _measure(command: list[str], root: Path, timeout: int) -> tuple[int, bytes, int]:
    started = time.monotonic_ns()
    try:
        result = subprocess.run(command, cwd=root, capture_output=True, check=False, timeout=timeout)
        output = (result.stdout or b"") + (result.stderr or b"")
        return result.returncode, _redact_output(output)[:MAX_LOG_BYTES], (time.monotonic_ns() - started) // 1_000_000
    except subprocess.TimeoutExpired as exc:
        output = (exc.stdout or b"") + (exc.stderr or b"")
        return 124, _redact_output(output)[:MAX_LOG_BYTES], (time.monotonic_ns() - started) // 1_000_000


def _validate_complete_gate_path(root: Path, path: Path, commit: str) -> tuple[int, str, int]:
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to((root / ".artifacts" / "complete-gate").resolve(strict=True))
        if path.is_symlink() or not path.is_file():
            raise ValueError
        payload = validate_gate_evidence(path, root)
        manifest = json.loads((root / "scripts/config/complete-gate-v1.json").read_text(encoding="utf-8"))
        validate_manifest(manifest)
    except (OSError, ValueError, UnicodeError, json.JSONDecodeError) as exc:
        raise AssuranceError("benchmark_legacy_evidence_invalid") from exc
    checks = payload.get("checks")
    expected = [(item["id"], item["required"]) for item in manifest["checks"]]
    actual = [(item.get("id"), item.get("required")) for item in checks] if isinstance(checks, list) else []
    required_shape = {
        "artifact", "artifactSha256", "artifactSize", "attempts", "diagnostic",
        "exitCode", "id", "required", "status",
    }
    if (
        payload.get("schemaVersion") != 1 or payload.get("sourceCommit") != commit
        or payload.get("overallStatus") != "passed" or actual != expected
        or any(
            set(item) != required_shape or item.get("status") != "passed"
            or item.get("exitCode") != 0
            or not isinstance(item.get("attempts"), int) or not 1 <= item["attempts"] <= 3
            or not isinstance(item.get("artifact"), str)
            or not isinstance(item.get("artifactSize"), int) or item["artifactSize"] < 0
            or not isinstance(item.get("artifactSha256"), str)
            or re.fullmatch(r"[0-9a-f]{64}", item["artifactSha256"]) is None
            for item in checks if item.get("required")
        )
    ):
        raise AssuranceError("benchmark_legacy_evidence_invalid")
    measured_bytes = sum(item.get("artifactSize", 0) for item in checks)
    try:
        elapsed_ms = int(
            (datetime.fromisoformat(payload["finishedAt"].replace("Z", "+00:00"))
             - datetime.fromisoformat(payload["startedAt"].replace("Z", "+00:00"))).total_seconds()
            * 1000
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise AssuranceError("benchmark_legacy_evidence_invalid") from exc
    if not isinstance(measured_bytes, int) or measured_bytes <= 0 or elapsed_ms <= 0:
        raise AssuranceError("benchmark_legacy_evidence_invalid")
    return measured_bytes, str(resolved.relative_to(root)), elapsed_ms


def _complete_gate_measurement(root: Path, output: bytes, commit: str) -> tuple[int, str, int]:
    text = output.decode("utf-8", errors="strict")
    matches = re.findall(r"^Evidence: (.+/result\.json)$", text, re.M)
    if len(matches) != 1:
        raise AssuranceError("benchmark_legacy_evidence_missing")
    return _validate_complete_gate_path(root, Path(matches[0]), commit)


def _existing_complete_gate(root: Path, commit: str) -> tuple[int, str, int] | None:
    directory = root / ".artifacts" / "complete-gate"
    if not directory.is_dir() or directory.is_symlink():
        return None
    for path in sorted(directory.glob("*/result.json"), key=lambda item: item.stat().st_mtime_ns, reverse=True):
        try:
            return _validate_complete_gate_path(root, path, commit)
        except AssuranceError:
            continue
    return None


def _validate_existing(directory_fd: int, commit: str, root: Path) -> dict:
    descriptor = os.open("result.json", os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW, dir_fd=directory_fd)
    try:
        details = os.fstat(descriptor)
        if details.st_uid != os.geteuid() or details.st_nlink != 1 or details.st_mode & 0o077:
            raise AssuranceError("benchmark_evidence_unsafe")
        with os.fdopen(os.dup(descriptor), "rb") as stream:
            payload = json.loads(stream.read(65537).decode("utf-8"))
    finally:
        os.close(descriptor)
    supplied = payload.get("integrity")
    unsigned = {key: value for key, value in payload.items() if key != "integrity"}
    expected_keys = {
        "schemaVersion", "status", "timeReductionPercent", "outputReductionPercent",
        "legacyMeasuredMilliseconds", "optimizedMeasuredMilliseconds", "estimatedAvoidedMilliseconds",
        "mutationsDetected", "mutationsTotal", "sourceCommit", "legacyLog",
        "legacyCompleteGateEvidence", "legacyFullLogBytes", "optimizedLog", "routineLog",
        "outputComparison", "mutationPathsDigest", "previousFeatureCommitHostedJobsMultiplier",
        "optimizedFeatureCommitHostedJobsMultiplier", "routineFixtures",
        "optimizedRoutineSamplesMilliseconds", "integrity",
    }
    if (
        set(payload) != expected_keys or payload.get("schemaVersion") != 1
        or payload.get("sourceCommit") != commit or payload.get("status") != "passed"
        or supplied != _sha(unsigned)
    ):
        raise AssuranceError("benchmark_evidence_invalid")
    for key, expected_name in (
        ("legacyLog", "legacy.log"), ("optimizedLog", "optimized.log"), ("routineLog", "routine.log"),
    ):
        metadata = payload.get(key)
        if not isinstance(metadata, dict) or set(metadata) != {"name", "sha256", "bytes"} or metadata["name"] != expected_name:
            raise AssuranceError("benchmark_evidence_invalid")
        member = os.open(expected_name, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW, dir_fd=directory_fd)
        try:
            details = os.fstat(member)
            chunks: list[bytes] = []
            remaining = MAX_LOG_BYTES + 1
            while remaining:
                block = os.read(member, min(1024 * 1024, remaining))
                if not block:
                    break
                chunks.append(block)
                remaining -= len(block)
            content = b"".join(chunks)
        finally:
            os.close(member)
        if (
            not stat.S_ISREG(details.st_mode) or details.st_uid != os.geteuid()
            or details.st_nlink != 1 or details.st_mode & 0o077
            or len(content) > MAX_LOG_BYTES or len(content) != metadata["bytes"]
            or hashlib.sha256(content).hexdigest() != metadata["sha256"]
        ):
            raise AssuranceError("benchmark_evidence_invalid")
    legacy = payload.get("legacyCompleteGateEvidence")
    if not isinstance(legacy, str):
        raise AssuranceError("benchmark_evidence_invalid")
    measured, relative, _ = _validate_complete_gate_path(root, root / legacy, commit)
    if relative != legacy or payload.get("legacyFullLogBytes") != measured:
        raise AssuranceError("benchmark_evidence_invalid")
    try:
        expected_report = benchmark_report(
            legacy_measured_ms=payload["legacyMeasuredMilliseconds"],
            optimized_measured_ms=payload["optimizedMeasuredMilliseconds"],
            legacy_output_bytes=payload["legacyFullLogBytes"],
            optimized_output_bytes=payload["optimizedLog"]["bytes"],
            estimated_avoided_ms=payload["estimatedAvoidedMilliseconds"],
            mutations_detected=payload["mutationsDetected"],
            mutations_total=payload["mutationsTotal"],
        )
    except (KeyError, TypeError, AssuranceError) as exc:
        raise AssuranceError("benchmark_evidence_invalid") from exc
    if (
        any(payload.get(key) != value for key, value in expected_report.items())
        or payload.get("outputComparison") != "same-exact-gate-full-logs-vs-compact-receipt"
        or payload.get("mutationPathsDigest") != hashlib.sha256("\n".join(sorted(MUTATIONS)).encode()).hexdigest()
        or payload.get("previousFeatureCommitHostedJobsMultiplier") != 2
        or payload.get("optimizedFeatureCommitHostedJobsMultiplier") != 1
        or payload.get("routineFixtures") != list(ROUTINE_FIXTURES)
        or not isinstance(payload.get("optimizedRoutineSamplesMilliseconds"), list)
        or len(payload["optimizedRoutineSamplesMilliseconds"]) != len(ROUTINE_FIXTURES)
        or any(not isinstance(value, int) or value <= 0 for value in payload["optimizedRoutineSamplesMilliseconds"])
    ):
        raise AssuranceError("benchmark_evidence_invalid")
    return payload


def _mutation_detection(root: Path, commit: str) -> int:
    graph = load_graph(root)
    detected = 0
    for path, required_check in MUTATIONS.items():
        change = Change("M", path, None, hashlib.sha256(path.encode()).hexdigest())
        plan = build_plan(graph, [change], "auto", commit, commit, False)
        if required_check not in plan["selected"]:
            raise AssuranceError(f"benchmark_mutation_escaped:{path}")
        detected += 1
    return detected


def _run_under_lease(root: Path) -> Path:
    commit = _git(root, "rev-parse", "HEAD")
    if not re.fullmatch(r"[0-9a-f]{40}", commit) or _git(root, "status", "--porcelain", "--untracked-files=all"):
        raise AssuranceError("benchmark_source_not_clean")
    benchmark_root_fd = open_private_directory(
        root / ".artifacts" / "assurance-orchestrator" / "benchmarks", root
    )
    evidence_fd: int | None = None
    try:
        try:
            fcntl.flock(benchmark_root_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise AssuranceError("benchmark_busy") from exc
        maximum = load_graph(root)["evidencePolicy"]["maxBenchmarkDirectories"]
        present = commit in os.listdir(benchmark_root_fd)
        _prune_private_directories(
            benchmark_root_fd, re.compile(r"[0-9a-f]{40}"),
            maximum if present else maximum - 1, {commit} if present else None,
        )
        evidence_fd = open_private_directory(
            root / ".artifacts" / "assurance-orchestrator" / "benchmarks" / commit, root
        )
        if "result.json" in os.listdir(evidence_fd):
            _validate_existing(evidence_fd, commit, root)
            return root / ".artifacts" / "assurance-orchestrator" / "benchmarks" / commit / "result.json"
        existing_gate = _existing_complete_gate(root, commit)
        if existing_gate is None:
            legacy_rc, legacy_log, measured_legacy_ms = _measure(
                ["/usr/bin/python3", str(root / "scripts/python/run_complete_gate.py")], root, 1800,
            )
            if legacy_rc:
                private_write(evidence_fd, "legacy-failure.log", legacy_log)
                raise AssuranceError(f"benchmark_legacy_failed:{legacy_rc}")
            legacy_output_bytes, legacy_evidence_path, receipt_legacy_ms = _complete_gate_measurement(
                root, legacy_log, commit,
            )
            legacy_ms = max(measured_legacy_ms, receipt_legacy_ms)
        else:
            legacy_output_bytes, legacy_evidence_path, legacy_ms = existing_gate
            legacy_log = f"Complete gate evidence reused: {legacy_evidence_path}\n".encode()
        with tempfile.TemporaryDirectory(prefix="base2-assurance-benchmark.") as raw:
            worktree = Path(raw) / "source"
            added = subprocess.run(
                ["git", "worktree", "add", "--detach", str(worktree), commit], cwd=root,
                capture_output=True, check=False, timeout=30,
            )
            if added.returncode:
                raise AssuranceError("benchmark_worktree_failed")
            try:
                optimized_samples: list[int] = []
                routine_logs: list[bytes] = []
                for relative in ROUTINE_FIXTURES:
                    document = worktree / relative
                    original = document.read_bytes()
                    document.write_bytes(original + b"\n")
                    try:
                        optimized_rc, optimized_log, optimized_ms = _measure(
                            [str(worktree / "scripts/bash/assure.sh"), "run", "--tier", "auto", "--base", commit, "--json"],
                            worktree, 120,
                        )
                    finally:
                        document.write_bytes(original)
                    if optimized_rc:
                        private_write(evidence_fd, f"optimized-{len(optimized_samples) + 1}-failure.log", optimized_log)
                        raise AssuranceError(f"benchmark_optimized_failed:{optimized_rc}")
                    try:
                        optimized_payload = json.loads(optimized_log.decode("utf-8"))
                    except (UnicodeError, json.JSONDecodeError) as exc:
                        raise AssuranceError("benchmark_optimized_output_invalid") from exc
                    if optimized_payload.get("status") != "passed" or optimized_payload.get("resolvedTier") != "focused":
                        raise AssuranceError("benchmark_optimized_output_invalid")
                    optimized_samples.append(optimized_ms)
                    routine_logs.append(optimized_log)
                optimized_ms = int(statistics.median(optimized_samples))
                routine_log = b"\n".join(routine_logs)[:MAX_LOG_BYTES]
            finally:
                removed = subprocess.run(
                    ["git", "worktree", "remove", "--force", str(worktree)], cwd=root,
                    capture_output=True, check=False, timeout=30,
                )
                if removed.returncode:
                    raise AssuranceError("benchmark_worktree_cleanup_failed")
        compact_rc, compact_log, _ = _measure(
            [str(root / "scripts/bash/assure.sh"), "run", "--tier", "auto", "--json"],
            root, 120,
        )
        if compact_rc:
            private_write(evidence_fd, "compact-release-failure.log", compact_log)
            raise AssuranceError(f"benchmark_compact_release_failed:{compact_rc}")
        try:
            compact_payload = json.loads(compact_log.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise AssuranceError("benchmark_compact_release_output_invalid") from exc
        if (
            compact_payload.get("status") != "passed"
            or compact_payload.get("satisfiedBy") != "exact-complete-gate"
            or compact_payload.get("executed") != []
        ):
            raise AssuranceError("benchmark_compact_release_output_invalid")
        optimized_output_bytes = len(compact_log)
        mutations_detected = _mutation_detection(root, commit)
        report = benchmark_report(
            legacy_measured_ms=legacy_ms,
            optimized_measured_ms=optimized_ms,
            legacy_output_bytes=legacy_output_bytes,
            optimized_output_bytes=optimized_output_bytes,
            estimated_avoided_ms=max(0, legacy_ms - optimized_ms),
            mutations_detected=mutations_detected,
            mutations_total=len(MUTATIONS),
        )
        if report["status"] != "passed":
            raise AssuranceError("benchmark_targets_not_met")
        legacy_sha, legacy_bytes = private_write(evidence_fd, "legacy.log", legacy_log)
        optimized_sha, optimized_bytes = private_write(evidence_fd, "optimized.log", compact_log)
        routine_sha, routine_bytes = private_write(evidence_fd, "routine.log", routine_log)
        payload = {
            **report,
            "sourceCommit": commit,
            "legacyLog": {"name": "legacy.log", "sha256": legacy_sha, "bytes": legacy_bytes},
            "legacyCompleteGateEvidence": legacy_evidence_path,
            "legacyFullLogBytes": legacy_output_bytes,
            "optimizedLog": {"name": "optimized.log", "sha256": optimized_sha, "bytes": optimized_bytes},
            "routineLog": {"name": "routine.log", "sha256": routine_sha, "bytes": routine_bytes},
            "outputComparison": "same-exact-gate-full-logs-vs-compact-receipt",
            "mutationPathsDigest": hashlib.sha256("\n".join(sorted(MUTATIONS)).encode()).hexdigest(),
            "previousFeatureCommitHostedJobsMultiplier": 2,
            "optimizedFeatureCommitHostedJobsMultiplier": 1,
            "routineFixtures": list(ROUTINE_FIXTURES),
            "optimizedRoutineSamplesMilliseconds": optimized_samples,
        }
        payload["integrity"] = _sha(payload)
        private_atomic_json(evidence_fd, "result.json", payload)
        return root / ".artifacts" / "assurance-orchestrator" / "benchmarks" / commit / "result.json"
    finally:
        if evidence_fd is not None:
            os.close(evidence_fd)
        os.close(benchmark_root_fd)


def run(root: Path = ROOT) -> Path:
    return _run_under_lease(root)


def main(argv: list[str]) -> int:
    if argv:
        print('{"status":"error","error":"benchmark_arguments_invalid"}')
        return 2
    try:
        print(run())
        return 0
    except (AssuranceError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, separators=(",", ":")))
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
