"""The mail acceptance runner must preserve failure and clean up on every exit."""

import importlib.util
import json
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

SOURCE = Path(__file__).parents[1] / "python/run_email_container_checks.py"
spec = importlib.util.spec_from_file_location("email_container_checks", SOURCE)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class ContainerRunnerTests(unittest.TestCase):
    def test_acceptance_is_required_and_guarded_in_release_gate(self):
        manifest = json.loads((SOURCE.parents[1] / "config/complete-gate-v1.json").read_text())
        check = next(
            item
            for item in manifest["checks"]
            if item["id"] == "feature-115-email-container-acceptance"
        )
        self.assertTrue(check["required"])
        self.assertEqual(check.get("maxAttempts", 1), 1)
        self.assertIn("feature-115-email-container-contract", check["dependsOn"])
        self.assertIn("workspace-postgres-acceptance", check["dependsOn"])
        self.assertEqual(
            check["command"],
            [
                "python3",
                "scripts/python/run_email_container_checks.py",
                "--image",
                "base2-local-api:latest",
            ],
        )

    def invoke(self, first, cleanup=None):
        with patch.object(
            runner.subprocess,
            "run",
            side_effect=[first, cleanup or subprocess.CompletedProcess([], 0, "", "")],
        ) as run:
            try:
                runner.run_phase(["docker", "run", "fixture"], "owned-test", "first")
            finally:
                self.assertEqual(
                    run.call_args_list[-1].args[0], ["docker", "rm", "--force", "owned-test"]
                )
                self.assertEqual(run.call_args_list[-1].kwargs["timeout"], 15)

    def test_valid_receipt(self):
        self.invoke(
            subprocess.CompletedProcess(
                [], 0, json.dumps({"ok": True, "phase": "first", "externalRequests": 0}), ""
            )
        )

    def test_timeout_is_sanitized_and_cleaned(self):
        with self.assertRaisesRegex(RuntimeError, "^email_container_check_timeout_first$"):
            self.invoke(subprocess.TimeoutExpired("sensitive-command", 45, output="secret"))

    def test_failure_is_preserved_over_cleanup_failure(self):
        with self.assertRaisesRegex(RuntimeError, "^email_container_check_failed_first$"):
            self.invoke(
                subprocess.CompletedProcess([], 1, "secret", "secret"),
                subprocess.CompletedProcess([], 1, "secret", "secret"),
            )

    def test_invalid_receipts(self):
        for payload in ("not-json", "{}", '{"ok":true,"phase":"first","externalRequests":1}'):
            with (
                self.subTest(payload=payload),
                self.assertRaisesRegex(RuntimeError, "^email_container_receipt_invalid$"),
            ):
                self.invoke(subprocess.CompletedProcess([], 0, payload, ""))

    def test_cleanup_failure_cannot_pass(self):
        with self.assertRaisesRegex(RuntimeError, "^email_container_cleanup_failed$"):
            self.invoke(
                subprocess.CompletedProcess(
                    [], 0, json.dumps({"ok": True, "phase": "first", "externalRequests": 0}), ""
                ),
                subprocess.CompletedProcess([], 1, "", ""),
            )


if __name__ == "__main__":
    unittest.main()
