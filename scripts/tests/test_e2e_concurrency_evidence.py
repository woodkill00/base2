import json
import os

import pytest

from scripts.python import record_e2e_concurrency_evidence as evidence


def _logs():
    return {
        "owner.log": b"4 passed\n",
        "contender.log": b"fixed isolated E2E project is already in use\n",
    }


def test_e2e_concurrency_evidence_is_exact_private_and_tamper_evident(tmp_path):
    result = evidence._persist_verified(_logs(), "a" * 40, tmp_path)
    payload = json.loads(result.read_text(encoding="utf-8"))
    assert payload["sourceCommit"] == "a" * 40
    assert payload["ownerExitCode"] == 0
    assert payload["contenderExitCode"] == 3
    assert payload["finalInventory"] == "empty"
    assert evidence._persist_verified(_logs(), "a" * 40, tmp_path) == result
    (result.parent / "owner.log").write_text("changed", encoding="utf-8")
    with pytest.raises(evidence.EvidenceError, match="changed"):
        evidence._persist_verified(_logs(), "a" * 40, tmp_path)


def test_e2e_concurrency_evidence_rejects_false_or_oversized_results(tmp_path):
    with pytest.raises(evidence.EvidenceError, match="result_invalid"):
        evidence._persist_verified(
            {"owner.log": b"not passed", "contender.log": b"not busy"}, "b" * 40, tmp_path
        )
    logs = _logs()
    logs["owner.log"] = b"4 passed\n" + b"x" * evidence.MAX_LOG_BYTES
    with pytest.raises(evidence.EvidenceError, match="log_invalid"):
        evidence._persist_verified(logs, "b" * 40, tmp_path)


def test_evidence_root_link_is_rejected_without_external_write(tmp_path):
    artifacts = tmp_path / ".artifacts"
    artifacts.mkdir(mode=0o700)
    outside = tmp_path / "outside"
    outside.mkdir(mode=0o755)
    (artifacts / "feature-106-e2e-concurrency").symlink_to(outside, target_is_directory=True)
    with pytest.raises(evidence.EvidenceError, match="root_unsafe"):
        evidence._persist_verified(_logs(), "c" * 40, tmp_path)
    assert list(outside.iterdir()) == []
    assert outside.stat().st_mode & 0o777 == 0o755


def test_cli_rejects_caller_supplied_logs(capsys):
    assert evidence.main(["owner.log", "contender.log"]) == 2
    assert "arguments_invalid" in capsys.readouterr().out


def test_self_observed_proof_rejects_source_change(tmp_path, monkeypatch):
    commits = iter(["d" * 40, "e" * 40])
    monkeypatch.setattr(evidence, "_commit", lambda _root: next(commits))
    runner = tmp_path / "scripts" / "bash"
    runner.mkdir(parents=True)
    (runner / "e2e-isolated.sh").write_text("#!/bin/sh\n", encoding="utf-8")

    class Owner:
        def __init__(self, *_args, stdout=None, pass_fds=(), **_kwargs):
            stdout.write(b"4 passed\n")
            os.write(pass_fds[0], b"ready\n")

        def wait(self, timeout=None):
            return 0

        def poll(self):
            return 0

    calls = 0

    def run(*_args, stdout=None, **_kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            stdout.write(b"fixed isolated E2E project is already in use\n")
            return type("Result", (), {"returncode": 3, "stdout": ""})()
        return type("Result", (), {"returncode": 0, "stdout": ""})()

    monkeypatch.setattr(evidence.subprocess, "Popen", Owner)
    monkeypatch.setattr(evidence.subprocess, "run", run)
    with pytest.raises(evidence.EvidenceError, match="source_changed"):
        evidence.run_and_record(tmp_path)
    assert not (tmp_path / ".artifacts").exists()
