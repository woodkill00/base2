from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REACT = ROOT / "react-app"


class BrandInventoryTests(unittest.TestCase):
    def test_legacy_sample_identity_and_placeholder_links_are_absent(self):
        source = REACT / "src"
        files = [
            REACT / "index.html",
            *source.rglob("*.js"),
            *source.rglob("*.jsx"),
            *source.rglob("*.ts"),
            *source.rglob("*.tsx"),
        ]
        content = "\n".join(path.read_text(encoding="utf-8") for path in files)
        for forbidden in ("SpecKit", "Woodkill Dev", "Base2 React App", "woodkilldev.com"):
            self.assertNotIn(forbidden, content)
        self.assertIsNone(re.search(r'href=["\']#(?:github|twitter|linkedin|privacy|terms)["\']', content))

    def test_brand_navigation_legal_and_metadata_are_manifest_driven(self):
        expected = {
            "src/components/glass/GlassHeader.tsx": (
                "manifest = siteManifest",
                "manifest.name",
            ),
            "src/components/glass/GlassSidebar.tsx": ("siteManifest.navigation.map",),
            "src/components/home/HomeFooter.jsx": (
                "manifest.navigation.map",
                "manifest.legal.privacyPath",
                "manifest.legal.termsPath",
                "manifest.legal.accessibilityPath",
            ),
            "vite.config.mjs": ("profile.seo.description", "profile.seo.indexing", "canonicalUrl"),
        }
        for relative, markers in expected.items():
            content = (REACT / relative).read_text(encoding="utf-8")
            for marker in markers:
                self.assertIn(marker, content, relative)


if __name__ == "__main__":
    unittest.main()
