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
        ):
            self.assertIn(marker, source)


if __name__ == "__main__":
    unittest.main()
