import contextlib
import io
import subprocess
import unittest
from unittest.mock import Mock, patch

from scripts.python.run_workspace_postgres_acceptance import cleanup_containers


class JourneyCleanupTests(unittest.TestCase):
    @patch("scripts.python.run_workspace_postgres_acceptance.subprocess.run")
    def test_removes_all_owned_containers(self, run):
        run.return_value = Mock(returncode=0)
        cleanup_containers(["owned-redis", "owned-postgres"])
        self.assertEqual(2, run.call_count)
        self.assertEqual(["docker", "rm", "--force", "owned-postgres"], run.call_args.args[0])
        self.assertEqual(30, run.call_args.kwargs["timeout"])

    @patch("scripts.python.run_workspace_postgres_acceptance.subprocess.run")
    def test_cleanup_error_fails_successful_run_and_still_attempts_remaining(self, run):
        run.side_effect = [Mock(returncode=1), Mock(returncode=0)]
        with contextlib.redirect_stderr(io.StringIO()) as stderr:
            with self.assertRaisesRegex(RuntimeError, "disposable_container_cleanup_failed"):
                cleanup_containers(["owned-redis", "owned-postgres"])
        self.assertEqual(2, run.call_count)
        self.assertIn("disposable_container_cleanup_failed", stderr.getvalue())

    @patch("scripts.python.run_workspace_postgres_acceptance.subprocess.run")
    def test_preserves_primary_failure_while_reporting_cleanup(self, run):
        for failure in [
            OSError("private details"),
            subprocess.TimeoutExpired("private command", 30),
        ]:
            run.side_effect = [failure, Mock(returncode=0)]
            run.reset_mock()
            with contextlib.redirect_stderr(io.StringIO()) as stderr:
                with self.assertRaisesRegex(ValueError, "original_failure"):
                    try:
                        raise ValueError("original_failure")
                    finally:
                        cleanup_containers(["owned-redis", "owned-postgres"], primary_failure=True)
            self.assertEqual(2, run.call_count)
            self.assertEqual("disposable_container_cleanup_failed\n", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
