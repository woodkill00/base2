import json
import hashlib
import os
from pathlib import Path

import pytest

from scripts.python import run_assurance_benchmark as benchmark


def test_benchmark_is_fixed_bounded_offline_and_uses_real_measurements():
    source = Path(benchmark.__file__).read_text(encoding="utf-8")
    assert "scripts/python/run_complete_gate.py" in source
    assert '["/usr/bin/python3", str(root / "scripts/python/run_complete_gate.py")]' in source
    assert '"scripts/bash/assure.sh"' in source
    assert "legacy_measured_ms=legacy_ms" in source
    assert "optimized_measured_ms=optimized_ms" in source
    assert "same-exact-gate-full-logs-vs-compact-receipt" in source
    assert "MAX_LOG_BYTES = 4 * 1024 * 1024" in source
    assert "requests" not in source and "urllib" not in source


def test_complete_gate_measurement_requires_exact_integrity_bound_pass(tmp_path):
    commit = "a" * 40
    config = tmp_path / "scripts" / "config"
    config.mkdir(parents=True)
    config.joinpath("complete-gate-v1.json").write_text(json.dumps({"schemaVersion": 1, "checks": [{
        "id": "sample", "command": ["true"], "required": True, "timeoutSeconds": 1,
        "dependsOn": [], "requiredTools": [],
    }]}), encoding="utf-8")
    evidence = tmp_path / ".artifacts" / "complete-gate" / "run" / "result.json"
    evidence.parent.mkdir(parents=True, mode=0o700)
    (tmp_path / ".artifacts").chmod(0o700)
    (tmp_path / ".artifacts" / "complete-gate").chmod(0o700)
    artifact = evidence.parent / "sample.log"
    artifact.write_bytes(b"x" * 100)
    artifact.chmod(0o600)
    payload = {
        "schemaVersion": 1,
        "sourceCommit": commit,
        "overallStatus": "passed",
        "startedAt": "2026-09-10T10:00:00Z",
        "finishedAt": "2026-09-10T10:00:01Z",
        "checks": [{
            "id": "sample", "required": True, "status": "passed", "artifact": "sample.log",
            "artifactSize": 100, "artifactSha256": hashlib.sha256(b"x" * 100).hexdigest(),
            "attempts": 1, "diagnostic": None, "exitCode": 0,
        }],
    }
    payload["evidenceDigest"] = benchmark._sha(payload)
    evidence.write_text(json.dumps(payload), encoding="utf-8")
    evidence.chmod(0o600)
    measured, relative, elapsed = benchmark._complete_gate_measurement(
        tmp_path, f"Complete gate: PASSED\nEvidence: {evidence}\n".encode(), commit,
    )
    assert measured == 100 and elapsed == 1000 and relative.endswith("result.json")
    assert benchmark._existing_complete_gate(tmp_path, commit) == (measured, relative, elapsed)
    payload["checks"][0]["status"] = "failed"
    payload["evidenceDigest"] = benchmark._sha({key: value for key, value in payload.items() if key != "evidenceDigest"})
    evidence.write_text(json.dumps(payload), encoding="utf-8")
    evidence.chmod(0o600)
    with pytest.raises(benchmark.AssuranceError, match="legacy_evidence_invalid"):
        benchmark._complete_gate_measurement(
            tmp_path, f"Complete gate: PASSED\nEvidence: {evidence}\n".encode(), commit,
        )


def test_mutation_fixture_covers_seven_safety_families():
    assert len(benchmark.MUTATIONS) == 7
    joined = "\n".join(benchmark.MUTATIONS)
    for marker in ("security", "tenant", "migrations", "index.css", ".github", "digital_ocean", "assurance"):
        assert marker in joined


def test_benchmark_uses_three_real_routine_samples_and_their_median():
    assert len(benchmark.ROUTINE_FIXTURES) == 3
    assert len(set(benchmark.ROUTINE_FIXTURES)) == 3
    source = Path(benchmark.__file__).read_text(encoding="utf-8")
    assert "statistics.median(optimized_samples)" in source
    assert '"optimizedRoutineSamplesMilliseconds": optimized_samples' in source


def test_benchmark_cli_rejects_all_arguments(capsys):
    assert benchmark.main(["--legacy-command", "anything"]) == 2
    assert "benchmark_arguments_invalid" in capsys.readouterr().out


def test_existing_benchmark_replay_binds_all_logs_and_gate(tmp_path, monkeypatch):
    directory = tmp_path / "benchmark"
    directory.mkdir(mode=0o700)
    metadata = {}
    for name in ("legacy.log", "optimized.log", "routine.log"):
        content = name.encode()
        member = directory / name
        member.write_bytes(content)
        member.chmod(0o600)
        metadata[name] = {"name": name, "sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content)}
    report = benchmark.benchmark_report(
        legacy_measured_ms=1000, optimized_measured_ms=2,
        legacy_output_bytes=1000, optimized_output_bytes=metadata["optimized.log"]["bytes"],
        estimated_avoided_ms=998, mutations_detected=7, mutations_total=7,
    )
    payload = {
        **report, "sourceCommit": "a" * 40,
        "legacyLog": metadata["legacy.log"], "optimizedLog": metadata["optimized.log"],
        "routineLog": metadata["routine.log"], "legacyCompleteGateEvidence": ".artifacts/gate.json",
        "legacyFullLogBytes": 1000,
        "legacyReceiptMilliseconds": 1000,
        "outputComparison": "same-exact-gate-full-logs-vs-compact-receipt",
        "mutationPathsDigest": hashlib.sha256("\n".join(sorted(benchmark.MUTATIONS)).encode()).hexdigest(),
        "previousFeatureCommitHostedJobsMultiplier": 2,
        "optimizedFeatureCommitHostedJobsMultiplier": 1,
        "routineFixtures": list(benchmark.ROUTINE_FIXTURES),
        "optimizedRoutineSamplesMilliseconds": [1, 2, 3],
    }
    payload["integrity"] = benchmark._sha(payload)
    result = directory / "result.json"
    result.write_text(json.dumps(payload), encoding="utf-8")
    result.chmod(0o600)
    monkeypatch.setattr(
        benchmark, "_validate_complete_gate_path",
        lambda *_args: (1000, ".artifacts/gate.json", 1000),
    )
    descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        assert benchmark._validate_existing(descriptor, "a" * 40, tmp_path)["status"] == "passed"
        payload["optimizedMeasuredMilliseconds"] = 400
        payload["integrity"] = benchmark._sha({key: value for key, value in payload.items() if key != "integrity"})
        result.write_text(json.dumps(payload), encoding="utf-8")
        result.chmod(0o600)
        with pytest.raises(benchmark.AssuranceError, match="benchmark_evidence_invalid"):
            benchmark._validate_existing(descriptor, "a" * 40, tmp_path)
        payload["optimizedMeasuredMilliseconds"] = 2
        payload["integrity"] = benchmark._sha({key: value for key, value in payload.items() if key != "integrity"})
        result.write_text(json.dumps(payload), encoding="utf-8")
        result.chmod(0o600)
        (directory / "routine.log").write_text("tampered", encoding="utf-8")
        (directory / "routine.log").chmod(0o600)
        with pytest.raises(benchmark.AssuranceError, match="benchmark_evidence_invalid"):
            benchmark._validate_existing(descriptor, "a" * 40, tmp_path)
    finally:
        os.close(descriptor)
