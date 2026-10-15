import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from scripts.python.renew_media_visual_review import REVIEW, SNAPSHOTS, clean_source, renew, validate_results


class MediaReviewRenewalTests(unittest.TestCase):
    def test_complete_matrix_only(self):
        stats = {"expected": 24, "skipped": 12, "unexpected": 0, "flaky": 0}
        validate_results({"stats": stats, "errors": []})
        for key in stats:
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_results({"stats": {**stats, key: stats[key] + 1}})
        for report in [{}, {"stats": stats, "errors": [{"message": "failure"}]}]:
            with self.assertRaises(ValueError):
                validate_results(report)

    @patch("scripts.python.renew_media_visual_review.git")
    def test_dirty_source_rejected(self, git):
        git.return_value = " M tracked.py"
        with self.assertRaisesRegex(ValueError, "clean_committed"):
            clean_source()

    @patch("scripts.python.renew_media_visual_review.git")
    def test_clean_source_bound(self, git):
        git.side_effect = ["", "a" * 40]
        self.assertEqual(clean_source(), "a" * 40)

    def test_failed_partial_or_drifted_runs_cannot_renew(self):
        for failure in ["process", "partial", "drift", "baseline"]:
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                snapshots = root / SNAPSHOTS
                snapshots.mkdir(parents=True)
                names = [f"capture-{n:02d}.png" for n in range(24)]
                for name in names:
                    (snapshots / name).touch()
                original = json.dumps({"sourceCommit": "b" * 40, "screenshots": names})
                review = root / REVIEW
                review.parent.mkdir(parents=True)
                review.write_text(original)
                report = {"stats": {"expected": 24, "skipped": 12, "unexpected": 0, "flaky": 0}}
                if failure == "partial":
                    report["stats"]["expected"] = 23
                with (
                    patch("scripts.python.renew_media_visual_review.ROOT", root),
                    patch("scripts.python.renew_media_visual_review.clean_source", side_effect=["a" * 40, "c" * 40]),
                    patch("scripts.python.renew_media_visual_review.git", return_value="changed.png" if failure == "baseline" else ""),
                    patch("scripts.python.renew_media_visual_review.subprocess.run", return_value=Mock(returncode=1 if failure == "process" else 0, stdout=json.dumps(report), stderr="")) as run,
                    self.assertRaises(ValueError),
                ):
                    renew()
                self.assertEqual(review.read_text(), original)
                if failure == "baseline":
                    run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
