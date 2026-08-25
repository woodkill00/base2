import json
from pathlib import Path
import tempfile
import unittest

from scripts.python.feature_093_closeout import (
    CloseoutError,
    EXPERIENCE_CHECKS,
    RECOVERY_CHECKS,
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
            result = recovery_ledger(self._gate(root), self._live(root), self._operations(root))
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
                recovery_ledger(path, self._live(root), self._operations(root))

    def test_non_destroyed_trial_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            live = json.loads(self._live(root).read_text())
            live["trials"][1]["state"] = "healthy"
            path = self._json(root, "bad-live.json", live)
            with self.assertRaisesRegex(CloseoutError, "live:teardown"):
                recovery_ledger(self._gate(root), path, self._operations(root))


if __name__ == "__main__":
    unittest.main()
