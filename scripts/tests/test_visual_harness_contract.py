from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class VisualHarnessContractTests(unittest.TestCase):
    def test_harness_freezes_every_declared_input(self):
        config = (ROOT / "react-app/playwright.visual.config.mjs").read_text(encoding="utf-8")
        spec = (ROOT / "react-app/e2e/visual/hermetic-visual.spec.ts").read_text(encoding="utf-8")
        for marker in (
            "browserName: 'chromium'",
            "locale: 'en-US'",
            "timezoneId: 'UTC'",
            "colorScheme: 'dark'",
            "reducedMotion: 'reduce'",
            "viewport: { width: 1280, height: 900 }",
            "deviceScaleFactor: 1",
            "serviceWorkers: 'block'",
        ):
            self.assertIn(marker, config)
        for marker in (
            "FrozenDate",
            "document.fonts.ready",
            "animation: none",
            "previous.equals(current)",
        ):
            self.assertIn(marker, spec)

    def test_harness_is_local_only_and_does_not_reuse_a_server(self):
        config = (ROOT / "react-app/playwright.visual.config.mjs").read_text(encoding="utf-8")
        spec = (ROOT / "react-app/e2e/visual/hermetic-visual.spec.ts").read_text(encoding="utf-8")
        self.assertIn("127.0.0.1:4174", config)
        self.assertIn("reuseExistingServer: false", config)
        self.assertIn("route.abort('blockedbyclient')", spec)
        self.assertNotIn("ignoreHTTPSErrors: true", config)


if __name__ == "__main__":
    unittest.main()
