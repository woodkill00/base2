from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.python.module_registry import ModuleRegistry, validate_manifest
from scripts.python.site_manifest import load_manifest

ROOT = Path(__file__).resolve().parents[2]


class ContentWorkspaceManifestTests(unittest.TestCase):
    def test_workspace_manifest_is_closed_provider_free_and_depends_on_content(self):
        payload = json.loads((ROOT / "modules/content-workspace/module.json").read_text())
        validated = validate_manifest(payload).payload
        self.assertEqual(["content"], validated["dependencies"])
        self.assertEqual([], validated["providerCapabilities"])
        self.assertEqual(["/api/content/v1"], validated["apiRoutes"])
        self.assertEqual(["/workspace"], validated["uiRoutes"])

    def test_base2_profile_enables_workspace_and_catalog_dependency(self):
        profile = load_manifest(ROOT / "site_profiles/base2-obsidian.json")
        enabled = {item["id"] for item in profile["modules"] if item["enabled"]}
        self.assertIn("content-workspace", enabled)
        manifests = [
            json.loads((ROOT / f"modules/{name}/module.json").read_text())
            for name in ("content", "content-workspace")
        ]
        self.assertEqual(
            ["content", "content-workspace"],
            [item["id"] for item in ModuleRegistry(manifests).install_plan()],
        )

    def test_preset_registry_is_versioned_closed_and_deterministic(self):
        path = ROOT / "modules/content-workspace/presets.json"
        first = json.loads(path.read_text())
        second = json.loads(path.read_text())
        self.assertEqual(first, second)
        self.assertEqual(1, first["schemaVersion"])
        self.assertEqual(
            {
                "article",
                "catalog",
                "rental",
                "portfolio",
                "documentation",
                "listing",
                "event",
                "community",
            },
            set(first["presets"]),
        )
        self.assertTrue(all(item["version"] == 1 for item in first["presets"].values()))


if __name__ == "__main__":
    unittest.main()
