import json
import unittest
from pathlib import Path

from scripts.python.site_manifest import load_manifest

ROOT = Path(__file__).resolve().parents[2]


class JourneyProfileTests(unittest.TestCase):
    def test_enabled_profile_uses_registered_module_versions(self):
        profile = load_manifest(ROOT / "site_profiles/journey-reference.json")
        for module in profile["modules"]:
            if module["id"] in {"blog", "portfolio", "documentation", "events", "booking"}:
                manifest = json.loads((ROOT / f"modules/{module['id']}/module.json").read_text())
                self.assertEqual(module["version"], manifest["version"])
                self.assertTrue(module["enabled"])
        self.assertEqual("deny", profile["seo"]["indexing"])
        self.assertEqual("destroy", profile["previewPolicy"]["idleAction"])
        self.assertTrue(all(domain["host"].endswith(".example") for domain in profile["domains"]))

    def test_real_base2_capabilities_are_not_enabled_by_fixture(self):
        profile = load_manifest(ROOT / "site_profiles/base2-obsidian.json")
        enabled = {item["id"] for item in profile["modules"] if item["enabled"]}
        self.assertFalse(enabled & {"blog", "portfolio", "documentation", "events", "booking"})


if __name__ == "__main__":
    unittest.main()
