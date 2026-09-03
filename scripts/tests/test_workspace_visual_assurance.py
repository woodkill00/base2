from __future__ import annotations

import copy
import importlib.util
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "workspace_visual_assurance", ROOT / "scripts/python/workspace_visual_assurance.py"
)
assert SPEC and SPEC.loader
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


def test_workspace_visual_matrix_is_complete_deterministic_and_integrity_bound():
    first = M.build(ROOT, commit="a" * 40)
    second = M.build(ROOT, commit="a" * 40)
    assert first == second
    M.validate(first)
    assert first["memberCount"] == 48
    assert set(first["surfaces"]) == {"records", "schema", "imports", "exports"}
    assert {row["project"] for row in first["members"]} == set(M.PROJECTS)
    assert all(row["width"] > 0 and row["height"] > 0 for row in first["members"])
    assert first["fixtureCoverage"]["fieldKinds"] == 18
    assert "failed" in first["fixtureCoverage"]["jobStates"]
    assert "rejected" in first["fixtureCoverage"]["mediaOutcomes"]
    assert "rtl" in first["fixtureCoverage"]["content"]


def test_workspace_visual_tamper_missing_matrix_and_false_review_fail_closed():
    payload = M.build(ROOT, commit="a" * 40)
    changed = copy.deepcopy(payload)
    changed["members"][0]["size"] += 1
    with pytest.raises(ValueError, match="digest"):
        M.validate(changed)
    incomplete = copy.deepcopy(payload)
    incomplete["members"].pop()
    unsigned = {key: value for key, value in incomplete.items() if key != "inventoryDigest"}
    incomplete["inventoryDigest"] = M.digest(
        M.json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode()
    )
    with pytest.raises(ValueError, match="matrix"):
        M.validate(incomplete)
    with pytest.raises(ValueError, match="review_status"):
        M.build(ROOT, commit="a" * 40, review_status="approved-by-default")


def test_workspace_visual_export_is_private_and_includes_real_contact_sheet():
    payload = M.build(ROOT, commit="a" * 40, review_status="reviewed-no-findings")
    with tempfile.TemporaryDirectory() as temporary:
        destination = Path(temporary) / "evidence"
        result = M.export(payload, destination, ROOT)
        assert result == {"ok": True, "memberCount": 48, "reviewStatus": "reviewed-no-findings"}
        assert destination.stat().st_mode & 0o077 == 0
        assert (destination / "workspace-contact-sheet.png").read_bytes().startswith(b"\x89PNG")
        assert (destination / "manifest.json").is_file()


def test_ordinary_visual_command_has_no_baseline_mutation_authority():
    package = (ROOT / "react-app/package.json").read_text()
    updater = (ROOT / "scripts/bash/update-workspace-visual-baselines.sh").read_text()
    assert "test:workspace-release" in package
    assert "--update-snapshots" not in package
    assert "WORKSPACE_VISUAL_BASELINE_UPDATE_APPROVAL" in updater
    assert "git diff --quiet" in updater
