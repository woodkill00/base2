import unittest
from unittest.mock import patch

from scripts.python.renew_media_visual_review import clean_source, validate_results


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


if __name__ == "__main__":
    unittest.main()
