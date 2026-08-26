from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "react-app/e2e/visual/hermetic-visual.spec.ts"
UPDATE = ROOT / "scripts/bash/update-visual-baselines.sh"


class VisualBaselineContractTests(unittest.TestCase):
    def test_reviewed_baseline_is_required_by_browser_test(self):
        source = SPEC.read_text(encoding="utf-8")
        self.assertIn("toHaveScreenshot('base2-obsidian-home-hero.png'", source)
        self.assertIn("toHaveScreenshot('base2-obsidian-full-page.png'", source)
        snapshots = list((SPEC.parent / "hermetic-visual.spec.ts-snapshots").glob("base2-obsidian-home-hero-*.png"))
        full_pages = list((SPEC.parent / "hermetic-visual.spec.ts-snapshots").glob("base2-obsidian-full-page-*.png"))
        self.assertEqual(3, len(snapshots), snapshots)
        self.assertEqual(3, len(full_pages), full_pages)
        self.assertTrue(all(path.stat().st_size > 10_000 for path in snapshots + full_pages))

    def test_update_workflow_is_explicit_local_and_review_only(self):
        source = UPDATE.read_text(encoding="utf-8")
        for marker in (
            "VISUAL_BASELINE_UPDATE_APPROVAL",
            "reviewed-local-only",
            "git diff --quiet",
            "--update-snapshots",
            "does not commit, publish, or deploy",
        ):
            self.assertIn(marker, source)

        env = os.environ.copy()
        env.pop("VISUAL_BASELINE_UPDATE_APPROVAL", None)
        result = subprocess.run(["bash", str(UPDATE)], cwd=ROOT, env=env, capture_output=True, text=True)
        self.assertEqual(64, result.returncode)
        self.assertIn("Refusing baseline update", result.stderr)

    def test_intentional_baseline_mutation_is_detectable(self):
        snapshots = list((SPEC.parent / "hermetic-visual.spec.ts-snapshots").glob("base2-obsidian-home-hero-*.png"))
        self.assertEqual(3, len(snapshots), snapshots)
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / snapshots[0].name
            shutil.copy2(snapshots[0], candidate)
            original = candidate.read_bytes()
            candidate.write_bytes(original[:-1] + bytes([original[-1] ^ 1]))
            self.assertNotEqual(snapshots[0].read_bytes(), candidate.read_bytes())


if __name__ == "__main__":
    unittest.main()
