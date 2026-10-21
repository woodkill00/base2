from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class AccessibilityMatrixContractTests(unittest.TestCase):
    def test_matrix_covers_required_dimensions_and_negative_control(self):
        source = (ROOT / "react-app/e2e/visual/accessibility-matrix.spec.ts").read_text(encoding="utf-8")
        for marker in (
            "desktop-dark-reduced",
            "tablet-light-reduced",
            "mobile-dark-motion",
            "window.axe.run",
            "scrollWidth",
            "keyboard.press('Tab')",
            "document.getAnimations()",
            "negative control",
            "image-alt",
            "route.abort('blockedbyclient')",
            "getByTestId('home-page')",
            "getByRole('main')",
            "getByRole('heading', { level: 1 })",
            "document.fonts.ready",
            "expect(waitForHome(page, 200)).rejects.toThrow()",
        ):
            self.assertIn(marker, source)

    def test_both_home_scans_require_ready_content_first(self):
        source = (ROOT / "react-app/e2e/visual/accessibility-matrix.spec.ts").read_text(encoding="utf-8")
        self.assertEqual(2, source.count("await page.goto('/');"))
        self.assertEqual(2, source.count("await page.goto('/');\n"))
        for scan in source.split("await page.goto('/');")[1:]:
            self.assertLess(scan.index("await waitForHome(page);"), scan.index("await page.addScriptTag"))


if __name__ == "__main__":
    unittest.main()
