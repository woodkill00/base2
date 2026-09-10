import json

import pytest

from scripts.python import record_e2e_concurrency_evidence as evidence


def _prepare(monkeypatch, commit="a" * 40):
    monkeypatch.setattr(evidence, "_commit", lambda _root: commit)


def test_e2e_concurrency_evidence_is_exact_private_and_tamper_evident(tmp_path, monkeypatch):
    _prepare(monkeypatch)
    owner = tmp_path / "owner-source.log"
    contender = tmp_path / "contender-source.log"
    owner.write_text("4 passed\n", encoding="utf-8")
    contender.write_text("fixed isolated E2E project is already in use\n", encoding="utf-8")
    result = evidence.record(owner, contender, tmp_path)
    payload = json.loads(result.read_text(encoding="utf-8"))
    assert payload["sourceCommit"] == "a" * 40
    assert payload["ownerExitCode"] == 0
    assert payload["contenderExitCode"] == 3
    assert payload["finalInventory"] == "empty"
    assert evidence.record(owner, contender, tmp_path) == result
    (result.parent / "owner.log").write_text("changed", encoding="utf-8")
    with pytest.raises(evidence.EvidenceError, match="changed"):
        evidence.record(owner, contender, tmp_path)


def test_e2e_concurrency_evidence_rejects_false_or_oversized_results(tmp_path, monkeypatch):
    _prepare(monkeypatch, "b" * 40)
    owner = tmp_path / "owner-source.log"
    contender = tmp_path / "contender-source.log"
    owner.write_text("not passed\n", encoding="utf-8")
    contender.write_text("not busy\n", encoding="utf-8")
    with pytest.raises(evidence.EvidenceError, match="result_invalid"):
        evidence.record(owner, contender, tmp_path)
    owner.write_bytes(b"4 passed\n" + b"x" * evidence.MAX_LOG_BYTES)
    with pytest.raises(evidence.EvidenceError, match="too_large"):
        evidence.record(owner, contender, tmp_path)
