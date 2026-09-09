from __future__ import annotations

import json
from pathlib import Path

import pytest

from digital_ocean.scripts.python import feature_106_repetitions as repetitions


def test_exact_head_evidence_is_hash_bound_and_replay_safe(tmp_path, monkeypatch):
    commit = "a" * 40
    monkeypatch.setattr(repetitions, "REPETITIONS", 2)
    monkeypatch.setattr(repetitions, "SUITES", {"suite": ("fixture",)})
    monkeypatch.setattr(repetitions, "_require_clean", lambda _root: None)
    monkeypatch.setattr(repetitions, "_source_commit", lambda _root: commit)

    class Result:
        returncode = 0
        stdout = "passed\n"
        stderr = ""

    monkeypatch.setattr(repetitions.subprocess, "run", lambda *_args, **_kwargs: Result())
    result = repetitions.run(tmp_path)
    payload = json.loads(result.read_text(encoding="utf-8"))
    assert payload["sourceCommit"] == commit
    assert payload["repetitionsPerSuite"] == 2
    assert len(payload["files"]) == 2
    assert len(payload["evidenceDigest"]) == 64
    assert repetitions.run(tmp_path) == result


def test_existing_evidence_rejects_changed_member(tmp_path, monkeypatch):
    commit = "b" * 40
    monkeypatch.setattr(repetitions, "REPETITIONS", 1)
    monkeypatch.setattr(repetitions, "SUITES", {"suite": ("fixture",)})
    monkeypatch.setattr(repetitions, "_require_clean", lambda _root: None)
    monkeypatch.setattr(repetitions, "_source_commit", lambda _root: commit)

    class Result:
        returncode = 0
        stdout = "passed\n"
        stderr = ""

    monkeypatch.setattr(repetitions.subprocess, "run", lambda *_args, **_kwargs: Result())
    result = repetitions.run(tmp_path)
    (result.parent / "suite-1.log").write_text("changed\n", encoding="utf-8")
    with pytest.raises(repetitions.RepetitionError, match="changed"):
        repetitions.run(tmp_path)


def test_existing_evidence_rejects_manifest_tamper(tmp_path, monkeypatch):
    commit = "d" * 40
    monkeypatch.setattr(repetitions, "REPETITIONS", 1)
    monkeypatch.setattr(repetitions, "SUITES", {"suite": ("fixture",)})
    monkeypatch.setattr(repetitions, "_require_clean", lambda _root: None)
    monkeypatch.setattr(repetitions, "_source_commit", lambda _root: commit)

    class Result:
        returncode = 0
        stdout = "passed\n"
        stderr = ""

    monkeypatch.setattr(repetitions.subprocess, "run", lambda *_args, **_kwargs: Result())
    result = repetitions.run(tmp_path)
    payload = json.loads(result.read_text(encoding="utf-8"))
    payload["suiteCommands"] = {"suite": ["changed"]}
    result.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(repetitions.RepetitionError, match="invalid"):
        repetitions.run(tmp_path)


def test_source_commit_is_exact_and_fail_closed(tmp_path, monkeypatch):
    class Result:
        returncode = 0
        stdout = "e" * 40 + "\n"

    monkeypatch.setattr(repetitions.subprocess, "run", lambda *_args, **_kwargs: Result())
    assert repetitions._source_commit(tmp_path) == "e" * 40
    Result.stdout = "not-a-commit\n"
    with pytest.raises(repetitions.RepetitionError, match="source_unavailable"):
        repetitions._source_commit(tmp_path)


def test_structurally_invalid_existing_manifest_is_rejected(tmp_path, monkeypatch):
    commit = "f" * 40
    monkeypatch.setattr(repetitions, "REPETITIONS", 1)
    monkeypatch.setattr(repetitions, "SUITES", {"suite": ("fixture",)})
    monkeypatch.setattr(repetitions, "_require_clean", lambda _root: None)
    monkeypatch.setattr(repetitions, "_source_commit", lambda _root: commit)

    class Result:
        returncode = 0
        stdout = "passed\n"
        stderr = ""

    monkeypatch.setattr(repetitions.subprocess, "run", lambda *_args, **_kwargs: Result())
    result = repetitions.run(tmp_path)
    payload = json.loads(result.read_text(encoding="utf-8"))
    payload["status"] = "failed"
    result.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(repetitions.RepetitionError, match="invalid"):
        repetitions.run(tmp_path)


def test_missing_existing_manifest_is_rejected(tmp_path):
    with pytest.raises(repetitions.RepetitionError, match="invalid"):
        repetitions._validate_existing(tmp_path, "f" * 40)


def test_main_reports_success_and_sanitized_failure(monkeypatch, capsys, tmp_path):
    result = tmp_path / "result.json"
    monkeypatch.setattr(repetitions, "run", lambda: result)
    assert repetitions.main() == 0
    assert str(result) in capsys.readouterr().out

    def fail():
        raise repetitions.RepetitionError("bounded_failure")

    monkeypatch.setattr(repetitions, "run", fail)
    assert repetitions.main() == 2
    assert "ERROR:RepetitionError:bounded_failure" in capsys.readouterr().out


def test_dirty_source_and_failed_repetition_are_terminal(tmp_path, monkeypatch):
    with pytest.raises(repetitions.RepetitionError, match="not_clean"):
        monkeypatch.setattr(repetitions.subprocess, "run", lambda *_args, **_kwargs: type(
            "Result", (), {"returncode": 0, "stdout": "dirty\n"}
        )())
        repetitions._require_clean(tmp_path)

    monkeypatch.setattr(repetitions, "REPETITIONS", 1)
    monkeypatch.setattr(repetitions, "SUITES", {"suite": ("fixture",)})
    monkeypatch.setattr(repetitions, "_require_clean", lambda _root: None)
    monkeypatch.setattr(repetitions, "_source_commit", lambda _root: "c" * 40)
    monkeypatch.setattr(repetitions.subprocess, "run", lambda *_args, **_kwargs: type(
        "Result", (), {"returncode": 1, "stdout": "", "stderr": "failed\n"}
    )())
    with pytest.raises(repetitions.RepetitionError, match="repetition_failed"):
        repetitions.run(tmp_path)
