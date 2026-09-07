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

    def test_rejects_nonblocking_scanner_and_mutable_service_image(self):
        body = "on:\n  pull_request:\njobs:\n  gate:\n    services:\n      db:\n        image: postgres:16\n    steps:\n      - run: scan\n        fail-build: false\n"
        findings = self.scan(body)
        self.assertTrue(any("nonblocking scanner" in item for item in findings))
        self.assertTrue(any("mutable image" in item for item in findings))

    def test_current_repository_satisfies_t019_policy(self):
        repo_root = MODULE_PATH.parents[2]
        policy = __import__("json").loads((repo_root / "scripts/config/ci-policy.json").read_text(encoding="utf-8"))
        findings = self.policy.validate(repo_root, policy)
        self.assertEqual([], findings)

    def test_storybook_excludes_only_the_application_bundle_budget(self):
        repo_root = MODULE_PATH.parents[2]
        main = (repo_root / "react-app/.storybook/main.js").read_text(encoding="utf-8")
        self.assertIn("viteFinal(config)", main)
        self.assertIn("plugin.name !== 'base2-performance-budget'", main)

    def test_frontend_security_job_audits_the_complete_graph_at_moderate(self):
        repo_root = MODULE_PATH.parents[2]
        workflow = (repo_root / ".github/workflows/security.yml").read_text(encoding="utf-8")
        self.assertIn("npm ci --legacy-peer-deps", workflow)
        self.assertIn("npm audit --audit-level=moderate --json", workflow)
        self.assertNotIn("npm audit --omit=dev", workflow)

    def test_e2e_stack_uses_the_documented_docker_hub_mirror(self):
        repo_root = MODULE_PATH.parents[2]
        compose = (repo_root / "e2e/docker-compose.e2e.yml").read_text(encoding="utf-8")
        self.assertNotIn("public.ecr.aws/docker/library", compose)
        self.assertNotIn("image: postgres:", compose)
        self.assertNotIn("image: redis:", compose)
        self.assertEqual(7, compose.count("mirror.gcr.io/library"))
        self.assertEqual(2, compose.count("mirror.gcr.io/library/postgres@sha256:"))
        self.assertEqual(1, compose.count("mirror.gcr.io/library/redis@sha256:"))

    def test_workflows_pin_node24_checkout_and_artifact_actions(self):
        repo_root = MODULE_PATH.parents[2]
        workflows = "\n".join(
            path.read_text(encoding="utf-8")
            for path in sorted((repo_root / ".github/workflows").glob("*.yml"))
        )
        self.assertNotIn("actions/checkout@11d5960a326750d5838078e36cf38b85af677262", workflows)
        self.assertNotIn("actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02", workflows)
        self.assertIn("actions/checkout@fbc6f3992d24b796d5a048ff273f7fcc4a7b6c09", workflows)
        self.assertIn("actions/upload-artifact@b7c566a772e6b6bfb58ed0dc250532a479d7789f", workflows)


if __name__ == "__main__":
    unittest.main()
