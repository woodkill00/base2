import hashlib
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "python" / "run_complete_gate.py"
COMPOSE_MODULE_PATH = Path(__file__).parents[1] / "python" / "validate_compose_config.py"


def load_module():
    spec = importlib.util.spec_from_file_location("run_complete_gate", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check(
    check_id,
    command,
    *,
    required=True,
    depends=None,
    tools=None,
    timeout=10,
    max_attempts=None,
    retry_on=None,
):
    result = {
        "id": check_id,
        "command": command,
        "required": required,
        "timeoutSeconds": timeout,
        "dependsOn": depends or [],
        "requiredTools": tools or [],
    }
    if max_attempts is not None:
        result["maxAttempts"] = max_attempts
    if retry_on is not None:
        result["retryOn"] = retry_on
    return result


class CompleteGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gate = load_module()

    def run_gate(self, checks, env=None):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        (root / ".git").mkdir()
        output = root / "evidence"
        result = self.gate.run_gate(
            {"schemaVersion": 1, "checks": checks},
            root,
            output,
            source_commit="0" * 40,
            environment=env,
        )
        return result, output

    def test_records_failure_and_blocks_dependent_check(self):
        result, _ = self.run_gate(
            [
                check("bad", ["/bin/sh", "-c", "exit 7"], tools=["/bin/sh"]),
                check("later", ["/bin/true"], depends=["bad"], tools=["/bin/true"]),
            ]
        )
        self.assertEqual("failed", result["overallStatus"])
        self.assertEqual(["failed", "not_run"], [item["status"] for item in result["checks"]])

    def test_missing_required_tool_is_incomplete(self):
        result, _ = self.run_gate(
            [check("missing", ["never"], tools=["base2-tool-that-does-not-exist"])]
        )
        self.assertEqual("incomplete", result["overallStatus"])
        self.assertEqual("unavailable", result["checks"][0]["status"])

    def test_timeout_is_failure(self):
        result, _ = self.run_gate(
            [check("slow", ["/bin/sh", "-c", "sleep 2"], tools=["/bin/sh"], timeout=1)]
        )
        self.assertEqual("failed", result["overallStatus"])
        self.assertIn("timed out", result["checks"][0]["diagnostic"])

    def test_does_not_retry_ordinary_failure(self):
        result, _ = self.run_gate([check("bad", ["/bin/sh", "-c", "exit 7"], tools=["/bin/sh"])])
        self.assertEqual(1, result["checks"][0]["attempts"])
        self.assertNotIn("retry", result["checks"][0]["diagnostic"])

    def test_retries_one_explicit_timeout_and_records_recovery(self):
        command = [
            "/bin/sh",
            "-c",
            "if test -f marker; then echo passed; else touch marker; sleep 2; fi",
        ]
        result, _ = self.run_gate(
            [
                check(
                    "slow",
                    command,
                    tools=["/bin/sh"],
                    timeout=1,
                    max_attempts=2,
                    retry_on=["timeout"],
                )
            ]
        )
        self.assertEqual("passed", result["overallStatus"])
        self.assertEqual(2, result["checks"][0]["attempts"])
        self.assertIn("bounded infrastructure retry", result["checks"][0]["diagnostic"])

    def test_retries_incomplete_output_but_not_assertion_failure(self):
        command = [
            "/bin/sh",
            "-c",
            "if test -f marker; then echo 'Test Files 1 passed'; exit 0; else touch marker; echo banner; exit 1; fi",
        ]
        result, _ = self.run_gate(
            [
                check(
                    "early",
                    command,
                    tools=["/bin/sh"],
                    max_attempts=2,
                    retry_on=["incomplete-test-output"],
                )
            ]
        )
        self.assertEqual("passed", result["overallStatus"])
        self.assertEqual(2, result["checks"][0]["attempts"])

        failed, _ = self.run_gate(
            [
                check(
                    "assertion",
                    ["/bin/sh", "-c", "echo '1 failed'; exit 1"],
                    tools=["/bin/sh"],
                    max_attempts=2,
                    retry_on=["incomplete-test-output"],
                )
            ]
        )
        self.assertEqual(1, failed["checks"][0]["attempts"])

    def test_redacts_secret_environment_values_and_binds_digest(self):
        secret = "fixture-super-secret-value"
        result, output = self.run_gate(
            [check("echo", ["/bin/sh", "-c", "printf '%s' \"$API_TOKEN\""], tools=["/bin/sh"])],
            env={**os.environ, "API_TOKEN": secret},
        )
        self.assertEqual("passed", result["overallStatus"])
        log = (output / "echo.log").read_text(encoding="utf-8")
        self.assertNotIn(secret, log)
        self.assertIn("[REDACTED]", log)
        stored = json.loads((output / "result.json").read_text(encoding="utf-8"))
        digest = stored.pop("evidenceDigest")
        canonical = json.dumps(stored, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(hashlib.sha256(canonical).hexdigest(), digest)

    def test_rejects_unknown_dependency_and_cycle(self):
        with self.assertRaisesRegex(ValueError, "unknown dependency"):
            self.gate.validate_manifest(
                {"schemaVersion": 1, "checks": [check("aa", ["true"], depends=["xx"])]}
            )
        with self.assertRaisesRegex(ValueError, "cycle"):
            self.gate.validate_manifest(
                {
                    "schemaVersion": 1,
                    "checks": [
                        check("aa", ["true"], depends=["bb"]),
                        check("bb", ["true"], depends=["aa"]),
                    ],
                }
            )

    def test_resolves_service_python_without_platform_specific_manifest(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        expected = root / (
            ".venv-api/Scripts/python.exe" if os.name == "nt" else ".venv-api/bin/python"
        )
        self.assertEqual(str(expected), self.gate.resolve_tool("{python-api}", root))
        self.assertEqual("node", self.gate.resolve_tool("node", root))

    def test_repo_manifest_uses_isolated_portable_service_interpreters(self):
        repo_root = MODULE_PATH.parents[2]
        manifest = json.loads(
            (repo_root / "scripts/config/complete-gate-v1.json").read_text(encoding="utf-8")
        )
        commands = {item["id"]: item["command"] for item in manifest["checks"]}
        self.assertEqual("{python-api}", commands["api-tests"][0])
        self.assertEqual("{python-django}", commands["django-tests"][0])
        self.assertEqual("{python-orchestrator}", commands["digitalocean-tests"][0])
        self.assertEqual(
            [
                "{python-orchestrator}",
                "digital_ocean/scripts/python/providerless_canary.py",
            ],
            commands["providerless-deployment-canary"],
        )
        self.assertIn("django/pytest.ini", commands["django-tests"])
        self.assertEqual(
            ["python3", "scripts/python/validate_compose_config.py"], commands["compose-config"]
        )
        powershell = (repo_root / "scripts/powershell/install-python-deps.ps1").read_text(
            encoding="utf-8"
        )
        for name in (".venv-api", ".venv-django", ".venv"):
            self.assertIn(name, powershell)

    def test_compose_fixture_replaces_only_documentation_placeholders(self):
        spec = importlib.util.spec_from_file_location(
            "validate_compose_config", COMPOSE_MODULE_PATH
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        rendered = module.render_validation_env(
            "PROJECT_NAME=YOUR_PROJECT_NAME\nKEEP=${PROJECT_NAME}\n"
        )
        self.assertEqual("PROJECT_NAME=fixture\nKEEP=${PROJECT_NAME}\n", rendered)


if __name__ == "__main__":
    unittest.main()
