import json
import subprocess
import sys
from pathlib import Path

from digital_ocean.scripts.python import feature_106_repetitions as repetitions
from scripts.python import assurance_orchestrator as assurance


def test_preflight_admits_valid_existing_evidence_without_release_acceptance(tmp_path, monkeypatch):
    monkeypatch.setattr(
        repetitions, "validate_current", lambda root: root / ".artifacts/current/result.json"
    )
    result = assurance.release_prerequisites(tmp_path)
    assert result["status"] == "passed" and result["releaseAccepted"] is False
    assert result["executed"] == [] and result["scope"] == "prerequisites-only"


def test_missing_stale_tampered_and_dirty_evidence_block(tmp_path, monkeypatch):
    for issue in ("missing", "source_changed", "integrity_invalid", "source_not_clean"):

        def invalid(root, issue=issue):
            raise repetitions.RepetitionError(issue)

        monkeypatch.setattr(repetitions, "validate_current", invalid)
        result = assurance.release_prerequisites(tmp_path)
        assert result["status"] == "blocked" and result["executed"] == []
        assert result["releaseAccepted"] is False


def test_preflight_cli_never_runs_a_test_plan(monkeypatch):
    monkeypatch.setattr(assurance, "release_prerequisites", lambda root: {"status": "blocked"})
    monkeypatch.setattr(
        assurance, "execute_plan", lambda *a: (_ for _ in ()).throw(AssertionError())
    )
    assert assurance.main(["preflight", "--json"]) == 1


def test_real_script_entrypoint_returns_json_not_import_traceback():
    root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, "scripts/python/assurance_orchestrator.py", "preflight", "--json"],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode in {0, 1}
    assert json.loads(result.stdout)["scope"] == "prerequisites-only"
    assert "Traceback" not in result.stderr
