from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VISUAL_TIP = "0132131292d584172a9b2fa173e439b540abed99"


class VisualPortTests(unittest.TestCase):
    def test_stale_visual_history_was_not_merged(self):
        result = subprocess.run(
            ["git", "merge-base", "--is-ancestor", VISUAL_TIP, "HEAD"],
            cwd=ROOT,
            check=False,
        )
        self.assertNotEqual(0, result.returncode)

    def test_reviewed_current_components_own_the_port(self):
        expected = {
            "components/home/HomeHero.jsx": ("home-obsidian-panel", "siteManifest"),
            "components/home/HomeVisual.jsx": ("home-runtime-frame", "siteManifest.modules"),
            "components/home/HomeFooter.jsx": ("home-integrated-footer",),
            "pages/Home.js": ("home-page-root",),
        }
        source = ROOT / "react-app/src"
        for relative, markers in expected.items():
            text = (source / relative).read_text(encoding="utf-8")
            for marker in markers:
                self.assertIn(marker, text, relative)

    def test_port_uses_semantic_tokens_and_has_responsive_reduced_motion_rules(self):
        css = (ROOT / "react-app/src/styles/home.css").read_text(encoding="utf-8")
        for token in ("--color-canvas", "--color-surface", "--color-text", "--color-accent"):
            self.assertIn(f"var({token})", css)
        self.assertIn("@media (max-width: 768px)", css)
        self.assertIn("prefers-reduced-motion: reduce", css)
        self.assertNotIn("images.unsplash.com", css)

    def test_external_decorative_image_and_unreviewed_operational_claims_are_absent(self):
        sources = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (ROOT / "react-app/src/components/home").glob("*.jsx")
        )
        self.assertNotIn("images.unsplash.com", sources)
        self.assertNotIn("Vault refs only", sources)
        self.assertNotIn("Live staging", sources)


if __name__ == "__main__":
    unittest.main()
