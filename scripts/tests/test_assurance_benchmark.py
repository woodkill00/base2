import json
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
    assert "MAX_LOG_BYTES = 4 * 1024 * 1024" in source
    assert "requests" not in source and "urllib" not in source


def test_complete_gate_measurement_requires_exact_integrity_bound_pass(tmp_path):
    commit = "a" * 40
    evidence = tmp_path / ".artifacts" / "complete-gate" / "run" / "result.json"
    evidence.parent.mkdir(parents=True)
    payload = {
        "schemaVersion": 1,
        "sourceCommit": commit,
        "overallStatus": "passed",
        "startedAt": "2026-09-10T10:00:00Z",
        "finishedAt": "2026-09-10T10:00:01Z",
        "checks": [{"required": True, "status": "passed", "artifactSize": 100}],
    }
    payload["evidenceDigest"] = benchmark._sha(payload)
    evidence.write_text(json.dumps(payload), encoding="utf-8")
    measured, relative, elapsed = benchmark._complete_gate_measurement(
        tmp_path, f"Complete gate: PASSED\nEvidence: {evidence}\n".encode(), commit,
    )
    assert measured == 100 and elapsed == 1000 and relative.endswith("result.json")
    assert benchmark._existing_complete_gate(tmp_path, commit) == (measured, relative, elapsed)
    payload["checks"][0]["status"] = "failed"
    evidence.write_text(json.dumps(payload), encoding="utf-8")
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
