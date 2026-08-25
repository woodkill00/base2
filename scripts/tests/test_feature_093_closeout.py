import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import subprocess

from scripts.python.feature_093_closeout import (
    CloseoutError,
    EXPERIENCE_CHECKS,
    RECOVERY_CHECKS,
    _verified_closeout_delta,
    experience_ledger,
    recovery_ledger,
)

ROOT = Path(__file__).resolve().parents[2]


class Feature093CloseoutTests(unittest.TestCase):
    def _json(self, root: Path, name: str, payload: dict) -> Path:
        path = root / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def _gate(self, root: Path) -> Path:
        checks = [{"id": name, "status": "passed"} for name in sorted(EXPERIENCE_CHECKS | RECOVERY_CHECKS)]
        return self._json(root, "gate.json", {"overallStatus": "passed", "sourceCommit": "a" * 40, "evidenceDigest": "b" * 64, "checks": checks})

    def _live(self, root: Path) -> Path:
        trial = {"state": "destroyed", "dnsRestored": True, "zeroProviderResources": True}
        return self._json(root, "live.json", {"status": "passed", "sourceCommit": "a" * 40, "trialCount": 3, "trials": [dict(trial) for _ in range(3)], "zeroProviderResources": True, "dnsRestored": True, "certificateMode": "letsencrypt-staging-only", "estimatedCostMinorUnits": 3})

    def _operations(self, root: Path) -> Path:
        return self._json(root, "operations.json", {"status": "passed", "faultRestoreCycles": 3, "ownedResourcesAfter": 0, "temporaryStateRetained": False, "providerCalls": 0, "rpoSeconds": 0, "rtoSecondsCeiling": 60})

    def test_three_teardowns_and_recovery_cycles_are_required(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = recovery_ledger(ROOT, self._gate(root), self._live(root), self._operations(root))
            self.assertEqual(3, result["canaryTeardownObservations"])
            self.assertTrue(result["zeroProviderResources"])
            self.assertEqual("letsencrypt-staging-only", result["certificateMode"])

    def test_experience_ledger_binds_two_brands_and_all_required_checks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = experience_ledger(ROOT, self._gate(root))
            self.assertEqual("passed", result["status"])
            self.assertEqual(2, len(result["fixtureBrands"]))
            self.assertEqual(0, result["unresolvedControls"])
            self.assertTrue(result["routeControlA11yVisualPerformanceComplete"])

    def test_missing_or_failed_gate_check_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            gate = json.loads(self._gate(root).read_text())
            gate["checks"] = [item for item in gate["checks"] if item["id"] != "operations-checkpoint"]
            path = self._json(root, "bad-gate.json", gate)
            with self.assertRaisesRegex(CloseoutError, "gate:missing"):
                recovery_ledger(ROOT, path, self._live(root), self._operations(root))

    def test_non_destroyed_trial_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            live = json.loads(self._live(root).read_text())
            live["trials"][1]["state"] = "healthy"
            path = self._json(root, "bad-live.json", live)
            with self.assertRaisesRegex(CloseoutError, "live:teardown"):
                recovery_ledger(ROOT, self._gate(root), path, self._operations(root))

    def test_runtime_change_between_live_and_closeout_fails_closed(self):
        responses = [
            subprocess.CompletedProcess([], 0, "", ""),
            subprocess.CompletedProcess([], 0, "api/main.py\n", ""),
        ]
        with patch("scripts.python.feature_093_closeout.subprocess.run", side_effect=responses):
            with self.assertRaisesRegex(CloseoutError, "live:runtime_delta:api/main.py"):
                _verified_closeout_delta(ROOT, "a" * 40, "b" * 40)

    def test_gate_and_independent_ci_recovery_delta_is_explicitly_allowed(self):
        expected = [
            ".github/workflows/ci-backend.yml",
            ".github/workflows/ci-frontend.yml",
            "api/db.py",
            "api/repositories/scheduling.py",
            "api/repositories/site_content.py",
            "api/security/request_auth.py",
            "api/tests/security/test_engagement_policy.py",
            "api/tests/test_engagement_service.py",
            "api/tests/test_scheduling_repository.py",
            "django/tests/live_scheduling_race.py",
            "docs/wsl-gate-recovery.md",
            "react-app/.storybook/main.js",
            "scripts/python/classify_gate_runtime_failure.py",
            "scripts/tests/test_ci_policy.py",
            "scripts/tests/test_gate_runtime_recovery.py",
        ]
        responses = [
            subprocess.CompletedProcess([], 0, "", ""),
            subprocess.CompletedProcess([], 0, "\n".join(expected) + "\n", ""),
        ]
        with patch("scripts.python.feature_093_closeout.subprocess.run", side_effect=responses):
            self.assertEqual(expected, _verified_closeout_delta(ROOT, "a" * 40, "b" * 40))

    def test_unrelated_live_commit_fails_closed(self):
        response = subprocess.CompletedProcess([], 1, "", "")
        with patch("scripts.python.feature_093_closeout.subprocess.run", return_value=response):
            with self.assertRaisesRegex(CloseoutError, "live:source_not_ancestor"):
                _verified_closeout_delta(ROOT, "a" * 40, "b" * 40)


if __name__ == "__main__":
    unittest.main()
