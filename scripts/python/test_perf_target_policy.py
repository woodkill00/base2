#!/usr/bin/env python3
from __future__ import annotations

import unittest

from perf_target_policy import evaluate


class PerfTargetPolicyTests(unittest.TestCase):
    def test_pull_requests_are_always_hermetic(self):
        result = evaluate("pull_request", "true", "https://example.com")
        self.assertFalse(result["enabled"])
        self.assertEqual(result["reason"], "pull-request-hermetic")

    def test_unconfigured_main_and_schedule_skip_cleanly(self):
        for event in ("push", "schedule", "workflow_dispatch"):
            with self.subTest(event=event):
                self.assertEqual(
                    evaluate(event, "", ""),
                    {"enabled": False, "reason": "live-target-not-enabled", "base_url": ""},
                )

    def test_explicit_https_root_target_is_enabled(self):
        self.assertEqual(
            evaluate("push", "true", " https://preview.example.com/ "),
            {"enabled": True, "reason": "approved-live-target", "base_url": "https://preview.example.com"},
        )

    def test_unsafe_or_ambiguous_targets_fail_closed(self):
        targets = (
            "", "http://example.com", "https://user@example.com", "https://example.com/path",
            "https://example.com?x=1", "https://example.com#fragment", "not-a-url",
        )
        for target in targets:
            with self.subTest(target=target):
                result = evaluate("schedule", "true", target)
                self.assertFalse(result["enabled"])
                self.assertEqual(result["reason"], "live-target-invalid")


if __name__ == "__main__":
    unittest.main()
