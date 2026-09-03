from __future__ import annotations

import json
from pathlib import Path

from scripts.python.generate_site_profiles import TARGETS, generate

ROOT = Path(__file__).resolve().parents[2]


def test_generated_workspace_contract_matrix_is_complete_and_deterministic():
    first = generate()
    second = generate(check=True)
    assert first == second
    expected_presets = {
        "article",
        "catalog",
        "rental",
        "portfolio",
        "documentation",
        "listing",
        "event",
        "community",
    }
    copies = []
    for target in TARGETS:
        payload = json.loads((target / "content-workspace-contracts.json").read_text())
        copies.append(payload)
        assert set(payload["profiles"]) == {
            "base2-obsidian",
            "ember-studio",
            "northstar-library",
        }
        enabled = payload["profiles"]["base2-obsidian"]
        assert enabled["enabled"] is True
        assert set(enabled["presets"]) == expected_presets
        assert len(enabled["fixtures"]) == len(expected_presets)
        assert enabled["models"] and enabled["migrations"]
        assert enabled["apiRoutes"] == ["/api/content/v1"]
        assert enabled["uiRoutes"] == ["/workspace"]
        assert enabled["navigation"] == ["workspace.index"]
        assert enabled["permissions"] and enabled["jobs"] and enabled["contractTests"]
        assert enabled["migrationNotes"] == "versioned-forward-and-rollback-required"
    assert copies[0] == copies[1] == copies[2]


def test_disabled_profiles_generate_no_workspace_authority_or_fixture_surface():
    generate(check=True)
    payload = json.loads((ROOT / "api/site_profiles/content-workspace-contracts.json").read_text())
    for profile_id in ("ember-studio", "northstar-library"):
        disabled = payload["profiles"][profile_id]
        assert disabled == {
            "enabled": False,
            "models": [],
            "migrations": [],
            "apiRoutes": [],
            "uiRoutes": [],
            "navigation": [],
            "permissions": [],
            "jobs": [],
            "presets": [],
            "fixtures": [],
            "contractTests": [],
            "migrationNotes": "disabled-no-op",
        }
