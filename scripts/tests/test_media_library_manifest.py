from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.python.module_registry import ModuleRegistry, validate_manifest
from scripts.python.site_manifest import load_manifest

ROOT = Path(__file__).resolve().parents[2]


class MediaLibraryManifestTests(unittest.TestCase):
    def test_media_module_is_closed_versioned_and_depends_on_workspace(self):
        payload = json.loads((ROOT / "modules/media/module.json").read_text())
        module = validate_manifest(payload).payload
        self.assertEqual("media", module["id"])
        self.assertEqual("2.1.0", module["version"])
        self.assertEqual(["content-workspace"], module["dependencies"])
        self.assertEqual(["/api/media/v1"], module["apiRoutes"])
        self.assertEqual(["/media"], module["uiRoutes"])
        self.assertEqual(["storage"], module["providerCapabilities"])
        self.assertIn("media.outbox-event", module["models"])
        self.assertIn("media.upload-part", module["models"])
        self.assertIn("media.inspection-result", module["models"])
        self.assertIn("media.derivative-recipe", module["models"])
        self.assertIn("media.purge-plan", module["models"])
        self.assertIn("media.encryption-envelope", module["models"])
        self.assertIn("media.abuse-case", module["models"])
        self.assertIn(
            "django/sitecontent/migrations/0013_media_governance.py", module["migrations"]
        )
        self.assertIn(
            "django/sitecontent/migrations/0014_media_processing_governance.py",
            module["migrations"],
        )
        self.assertIn(
            "django/sitecontent/migrations/0015_media_portability_and_abuse.py",
            module["migrations"],
        )

    def test_reference_profile_install_order_places_media_after_workspace(self):
        profile = load_manifest(ROOT / "site_profiles/base2-obsidian.json")
        enabled = {item["id"] for item in profile["modules"] if item["enabled"]}
        self.assertIn("media", enabled)
        manifests = [
            json.loads((ROOT / f"modules/{name}/module.json").read_text())
            for name in ("content", "content-workspace", "media")
        ]
        self.assertEqual(
            ["content", "content-workspace", "media"],
            [item["id"] for item in ModuleRegistry(manifests).install_plan()],
        )

    def test_other_profiles_remain_media_disabled_without_route_or_module(self):
        for name in ("ember-studio", "northstar-library"):
            profile = load_manifest(ROOT / f"site_profiles/{name}.json")
            enabled = {item["id"] for item in profile["modules"] if item["enabled"]}
            self.assertNotIn("media", enabled)
            self.assertFalse(any(item.get("module") == "media" for item in profile["navigation"]))

    def test_settings_schema_is_closed_and_defaults_disabled(self):
        schema = json.loads((ROOT / "modules/media/settings.schema.json").read_text())
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(set(schema["required"]), set(schema["properties"]))
        self.assertFalse(schema["properties"]["enabled"]["default"])
        self.assertEqual(["clamav"], schema["properties"]["scannerAdapter"]["enum"])


if __name__ == "__main__":
    unittest.main()
