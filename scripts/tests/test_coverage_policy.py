import copy
from datetime import date
import importlib.util
from pathlib import Path
import unittest


MODULE_PATH = Path(__file__).parents[1] / "python" / "coverage_policy.py"
RUNNER_PATH = Path(__file__).parents[1] / "python" / "run_coverage_policy.py"


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
        spec = importlib.util.spec_from_file_location("run_coverage_policy", RUNNER_PATH)
        cls.runner = importlib.util.module_from_spec(spec)
        sys_path = __import__("sys").path
        sys_path.insert(0, str(RUNNER_PATH.parent))
        try:
            spec.loader.exec_module(cls.runner)
        finally:
            sys_path.pop(0)

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

    def test_summarizes_lcov_without_averaging_file_percentages(self):
        report = "LF:10\nLH:8\nBRF:4\nBRH:3\nFNF:2\nFNH:1\nend_of_record\nLF:10\nLH:10\nBRF:6\nBRH:6\nFNF:2\nFNH:2\n"
        self.assertEqual({"lines": 90.0, "branches": 90.0, "functions": 75.0}, self.runner.summarize_lcov(report))

    def test_evaluator_fails_missing_or_regressed_metric(self):
        candidate = policy()
        result = self.runner.evaluate(candidate, {"api-runtime": {"lines": 48}})
        self.assertEqual("failed", result["status"])
        self.assertTrue(any("49" in finding for finding in result["findings"]))

    def test_changed_line_parser_and_floor(self):
        diff = "+++ b/api/main.py\n@@ -4,0 +5,3 @@\n+one\n+two\n+three\n"
        changed = self.runner.parse_changed_lines(diff)
        self.assertEqual({"api/main.py": {5, 6, 7}}, changed)
        result = self.runner.changed_line_result(changed, [{"api/main.py": {5: True, 6: True, 7: False}}], 90)
        self.assertEqual("failed", result["status"])
        self.assertEqual(66.67, result["percent"])

    def test_changed_line_floor_is_not_applicable_without_executable_lines(self):
        result = self.runner.changed_line_result({"docs/readme.md": {1}}, [{}], 90)
        self.assertEqual("not_applicable", result["status"])


if __name__ == "__main__":
    unittest.main()
