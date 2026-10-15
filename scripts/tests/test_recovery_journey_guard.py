import os
import unittest
from unittest.mock import patch

from scripts.python.run_recovery_journey_postgres_checks import JourneyFailure, main


class RecoveryJourneyGuardTests(unittest.TestCase):
    def test_refuses_non_disposable_database_before_importing_application(self):
        for env in (
            {},
            {"DB_HOST": "remote", "DB_NAME": "base2"},
            {"DB_HOST": "127.0.0.1", "DB_NAME": "owner"},
        ):
            with (
                self.subTest(env=env),
                patch.dict(os.environ, env, clear=True),
                self.assertRaisesRegex(JourneyFailure, "disposable_database_required"),
            ):
                main()

    def test_requires_disposable_runner_marker(self):
        with (
            patch.dict(os.environ, {"DB_HOST": "127.0.0.1", "DB_NAME": "base2"}, clear=True),
            self.assertRaisesRegex(JourneyFailure, "disposable_runner_required"),
        ):
            main()


if __name__ == "__main__":
    unittest.main()
