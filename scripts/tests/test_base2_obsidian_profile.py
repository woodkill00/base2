from __future__ import annotations

import json
from pathlib import Path

from scripts.python.generate_site_profiles import TARGETS, generate
from scripts.python.site_manifest import load_manifest, manifest_digest


ROOT = Path(__file__).resolve().parents[2]


def test_canonical_base2_obsidian_profile_is_complete_and_generated():
    source = ROOT / "site_profiles/base2-obsidian.json"
    profile = load_manifest(source)
    assert profile["siteId"] == "base2-obsidian"
    assert profile["brand"]["theme"] == "obsidian"
    assert profile["seo"]["indexing"] == "deny"
    assert profile["search"]["enabled"] is True
    assert {row["id"] for row in profile["modules"] if row["enabled"]} == {
        "accounts",
        "commerce",
        "content",
        "content-workspace",
        "forms",
        "search",
    }
    digests = generate(check=True)
    assert digests["base2-obsidian"] == manifest_digest(profile)
    for target in TARGETS:
        assert json.loads((target / "base2-obsidian.json").read_text()) == profile
        index = json.loads((target / "index.json").read_text())
        assert "base2-obsidian" in index["profiles"]


def test_react_registry_is_generated_and_contains_every_profile():
    registry = (ROOT / "react-app/src/config/generated/siteRegistry.ts").read_text()
    index = json.loads((ROOT / "react-app/src/config/generated/index.json").read_text())
    for profile_id in index["profiles"]:
        assert f"'{profile_id}'" in registry
        assert f"./{profile_id}.json" in registry


def test_fixture_profiles_remain_distinct_from_base2():
    base2 = load_manifest(ROOT / "site_profiles/base2-obsidian.json")
    for fixture in ("ember-studio", "northstar-library"):
        item = load_manifest(ROOT / f"site_profiles/{fixture}.json")
        assert item["siteId"] != base2["siteId"]
        assert item["name"] != base2["name"]
        assert manifest_digest(item) != manifest_digest(base2)
