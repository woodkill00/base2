import importlib.util
from pathlib import Path
import tempfile
import unittest


MODULE_PATH = Path(__file__).parents[1] / "python" / "validate_ci_policy.py"


def load_module():
    spec = importlib.util.spec_from_file_location("validate_ci_policy", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CiPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = load_module()

    def scan(self, body):
        return self.policy.scan_workflow("fixture.yml", body, ["gate"], "ci-policy: diagnostic-cleanup")

    def test_accepts_pinned_blocking_required_job(self):
        body = "on:\n  pull_request:\njobs:\n  gate:\n    steps:\n      - uses: actions/checkout@" + "a" * 40 + "\n"
        self.assertEqual([], self.scan(body))

    def test_rejects_continue_on_error_and_shell_suppression(self):
        body = "on:\n  pull_request:\njobs:\n  gate:\n    continue-on-error: true\n    steps:\n      - run: scanner || true\n"
        findings = self.scan(body)
        self.assertTrue(any("continue-on-error" in item for item in findings))
        self.assertTrue(any("suppression" in item for item in findings))

    def test_allows_only_marked_diagnostic_cleanup_suppression(self):
        body = "on:\n  pull_request:\njobs:\n  gate:\n    steps:\n      - run: cleanup || true # ci-policy: diagnostic-cleanup\n"
        self.assertEqual([], self.scan(body))

    def test_rejects_mutable_action_and_missing_job(self):
        body = "on:\n  pull_request:\njobs:\n  other:\n    steps:\n      - uses: actions/checkout@v4\n"
        findings = self.scan(body)
        self.assertTrue(any("missing required job" in item for item in findings))
        self.assertTrue(any("mutable action" in item for item in findings))

    def test_current_repository_has_known_pre_t019_findings(self):
        repo_root = MODULE_PATH.parents[2]
        policy = __import__("json").loads((repo_root / "scripts/config/ci-policy.json").read_text(encoding="utf-8"))
        findings = self.policy.validate(repo_root, policy)
        self.assertTrue(any("continue-on-error" in item for item in findings))
        self.assertTrue(any("mutable action" in item for item in findings))


if __name__ == "__main__":
    unittest.main()
