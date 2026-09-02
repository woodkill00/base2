from __future__ import annotations

import copy
import importlib.util
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "visual_assurance_manifest", ROOT / "scripts/python/visual_assurance_manifest.py"
)
assert SPEC and SPEC.loader
M = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(M)


def test_inventory_is_deterministic_complete_and_integrity_bound():
    first = M.build(ROOT, commit="a" * 40)
    second = M.build(ROOT, commit="a" * 40)
    assert first == second
    M.validate(first)
    assert first["baselineCount"] >= 50
    assert {"desktop", "tablet", "mobile"}.issubset(first["projects"])
    assert {row["id"] for row in first["routes"]} == {
        "public", "admin", "api", "swagger", "pgadmin", "traefik", "settings", "workspace"
    }
    assert all(row["size"] > 8 and len(row["sha256"]) == 64 for row in first["members"])


def test_tampering_and_duplicate_members_fail_closed():
    payload = M.build(ROOT, commit="a" * 40)
    changed = copy.deepcopy(payload); changed["members"][0]["size"] += 1
    with pytest.raises(ValueError, match="digest"):
        M.validate(changed)
    duplicate = copy.deepcopy(payload)
    duplicate["members"].append(copy.deepcopy(duplicate["members"][0]))
    duplicate["baselineCount"] = len(duplicate["members"])
    unsigned = {key: value for key, value in duplicate.items() if key != "inventoryDigest"}
    duplicate["inventoryDigest"] = M.sha256(M.json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode())
    with pytest.raises(ValueError, match="duplicate"):
        M.validate(duplicate)


def test_export_is_private_and_manifest_members_are_exact():
    payload = M.build(ROOT, commit="a" * 40)
    with tempfile.TemporaryDirectory() as temporary:
        destination = Path(temporary) / "evidence"
        result = M.export(payload, destination)
        assert result["ok"]
        assert destination.stat().st_mode & 0o077 == 0
        assert "default-src 'none'" in (destination / "visual-assurance.html").read_text()
        assert (destination / "manifest.json").is_file()


def test_markdown_states_honest_live_boundary():
    rendered = M.render_markdown(M.build(ROOT, commit="a" * 40))
    assert "live approval required" in rendered
    assert "not claims of live availability" in rendered
