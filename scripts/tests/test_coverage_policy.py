import copy
from datetime import date
import importlib.util
from pathlib import Path
import unittest


MODULE_PATH = Path(__file__).parents[1] / "python" / "coverage_policy.py"


def load_module():
    spec = importlib.util.spec_from_file_location("coverage_policy", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def policy():
    return {
        "schemaVersion": 1,
        "changedLines": {"minimumPercent": 90},
        "surfaces": [{
            "id": "api-runtime", "label": "API runtime", "scope": "api excluding tests",
            "baselineStatus": "measured", "baseline": {"lines": 50}, "floors": {"lines": 49},
        }],
        "exceptions": [],
    }


class CoveragePolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.coverage = load_module()

    def test_accepts_measured_floor_at_or_below_baseline(self):
        self.assertEqual([], self.coverage.validate_policy(policy()))

    def test_rejects_duplicate_unmeasured_and_inflated_surfaces(self):
        candidate = policy()
        duplicate = copy.deepcopy(candidate["surfaces"][0])
        duplicate["baselineStatus"] = "unmeasured"
        duplicate["floors"]["lines"] = 51
        candidate["surfaces"].append(duplicate)
        findings = self.coverage.validate_policy(candidate)
        self.assertTrue(any("unique" in finding for finding in findings))
        self.assertTrue(any("not measured" in finding for finding in findings))
        self.assertTrue(any("exceeds" in finding for finding in findings))

    def test_rejects_expired_or_ownerless_exception(self):
        candidate = policy()
        candidate["exceptions"] = [{"id": "COV-001", "surface": "api-runtime", "expiresOn": "2025-01-01"}]
        findings = self.coverage.validate_policy(candidate, today=date(2026, 8, 24))
        self.assertTrue(any("lacks owner" in finding for finding in findings))
        self.assertTrue(any("expired" in finding for finding in findings))

    def test_summarizes_python_runtime_and_excludes_tests(self):
        report = {"files": {
            "api/main.py": {"summary": {"covered_lines": 8, "num_statements": 10, "covered_branches": 3, "num_branches": 4}},
            "api/tests/test_main.py": {"summary": {"covered_lines": 100, "num_statements": 100, "covered_branches": 10, "num_branches": 10}},
        }}
        summary = self.coverage.summarize_python_coverage(report, ["/tests/"])
        self.assertEqual({"lines": 80.0, "statements": 80.0, "branches": 75.0}, summary)


if __name__ == "__main__":
    unittest.main()
