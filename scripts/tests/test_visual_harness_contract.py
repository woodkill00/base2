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
        preview = (ROOT / "scripts/bash/visual-preview.sh").read_text(encoding="utf-8")
        spec = (ROOT / "react-app/e2e/visual/hermetic-visual.spec.ts").read_text(encoding="utf-8")
        self.assertIn("process.env.BASE2_VISUAL_PORT || '4174'", config)
        self.assertIn("visualPort < 1024 || visualPort > 65535", config)
        self.assertIn("http://127.0.0.1:${visualPort}", config)
        self.assertIn("bash ../scripts/bash/visual-preview.sh ${visualPort}", config)
        self.assertIn("reuseExistingServer: false", config)
        self.assertIn("gracefulShutdown: { signal: 'SIGTERM', timeout: 5_000 }", config)
        self.assertIn("route.abort('blockedbyclient')", spec)
        self.assertNotIn("ignoreHTTPSErrors: true", config)
        self.assertIn('build_dir="$build_root/$port"', preview)
        self.assertIn('trap cleanup EXIT INT TERM', preview)
        self.assertIn('--host 127.0.0.1 --port "$port" --strictPort', preview)
        self.assertIn('rm -rf -- "$build_dir"', preview)

    def test_localized_visual_evidence_is_hermetic_and_covers_reflow_and_rtl(self):
        config = (ROOT / "react-app/playwright.visual.config.mjs").read_text(encoding="utf-8")
        spec = (ROOT / "react-app/e2e/visual/obsidian-localization.spec.ts").read_text(
            encoding="utf-8"
        )
        for marker in ("german-reflow", "arabic-rtl-touch", "locale: 'de-DE'", "locale: 'ar-SA'"):
            self.assertIn(marker, config)
        for marker in (
            "FrozenDate",
            "document.fonts.ready",
            "route.abort('blockedbyclient')",
            "toHaveAttribute('dir', scenario.direction)",
            "toHaveScreenshot",
            "toBeDisabled",
        ):
            self.assertIn(marker, spec)


if __name__ == "__main__":
    unittest.main()
