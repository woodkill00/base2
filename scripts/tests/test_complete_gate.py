import hashlib
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from stat import S_IMODE
from unittest.mock import patch

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

    def test_exact_source_admission_rejects_dirty_or_invalid_identity(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(root))
        clean = unittest.mock.Mock(returncode=0, stdout="")
        with patch.object(self.gate.subprocess, "run", return_value=clean), patch.object(
            self.gate, "git_commit", return_value="a" * 40
        ):
            self.assertEqual("a" * 40, self.gate.require_clean_source(root))
        for result in (
            unittest.mock.Mock(returncode=0, stdout=" M tracked.py\n"),
            unittest.mock.Mock(returncode=0, stdout="?? injected.py\n"),
            unittest.mock.Mock(returncode=1, stdout=""),
        ):
            with patch.object(self.gate.subprocess, "run", return_value=result), self.assertRaisesRegex(
                ValueError, "complete_gate_source_not_clean"
            ):
                self.gate.require_clean_source(root)

    def test_gate_revalidates_source_before_and_after_each_command(self):
        calls = []
        result, _ = self.run_gate_with_source_guard(
            [check("source-guard", ["python3", "-c", "print('ok')"])],
            lambda: calls.append("checked"),
        )
        self.assertEqual("passed", result["overallStatus"])
        self.assertGreaterEqual(len(calls), 3)

    def run_gate_with_source_guard(self, checks, source_guard):
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
            source_guard=source_guard,
        )
        return result, output

    def test_complete_gate_lock_rejects_contender_and_releases(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        with self.gate.complete_gate_lock(root) as lock_path:
            self.assertEqual(0o600, S_IMODE(lock_path.stat().st_mode))
            with self.assertRaisesRegex(
                self.gate.CompleteGateBusy, "complete_gate_already_running"
            ), self.gate.complete_gate_lock(root):
                self.fail("contender acquired the gate lock")
        with self.gate.complete_gate_lock(root):
            pass
        with self.assertRaisesRegex(
            RuntimeError, "owner failure"
        ), self.gate.complete_gate_lock(root):
            raise RuntimeError("owner failure")
        with self.gate.complete_gate_lock(root):
            pass

    def test_complete_gate_lock_rejects_symlink_and_preserves_target(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        artifacts = root / ".artifacts"
        artifacts.mkdir()
        target = root / "target.txt"
        target.write_text("preserve", encoding="utf-8")
        (artifacts / "complete-gate.lock").symlink_to(target)
        with self.assertRaises(OSError), self.gate.complete_gate_lock(root):
            self.fail("symlink lock was followed")
        self.assertEqual("preserve", target.read_text(encoding="utf-8"))
        self.assertEqual(0o644, S_IMODE(target.stat().st_mode))

    def test_complete_gate_lock_rejects_symlinked_artifacts_directory(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        outside = root / "outside"
        outside.mkdir()
        (root / ".artifacts").symlink_to(outside, target_is_directory=True)
        with self.assertRaises(OSError), self.gate.complete_gate_lock(root):
            self.fail("symlinked lock parent was followed")
        self.assertEqual([], list(outside.iterdir()))

    def test_complete_gate_lock_rejects_hardlink_and_preserves_target(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        artifacts = root / ".artifacts"
        artifacts.mkdir()
        target = root / "target.txt"
        target.write_text("preserve", encoding="utf-8")
        os.link(target, artifacts / "complete-gate.lock")
        with self.assertRaisesRegex(
            ValueError, "unsafe_complete_gate_lock"
        ), self.gate.complete_gate_lock(root):
            self.fail("hardlink lock was accepted")
        self.assertEqual("preserve", target.read_text(encoding="utf-8"))
        self.assertEqual(0o644, S_IMODE(target.stat().st_mode))

    def test_complete_gate_lock_closes_descriptors_when_lock_chmod_fails(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        original = self.gate.os.fchmod
        calls = 0

        def fail_second(descriptor, mode):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("fixture chmod failure")
            return original(descriptor, mode)

        before = len(os.listdir("/proc/self/fd"))
        with (
            patch.object(self.gate.os, "fchmod", side_effect=fail_second),
            self.assertRaisesRegex(OSError, "fixture chmod failure"),
            self.gate.complete_gate_lock(root),
        ):
            self.fail("lock admission unexpectedly succeeded")
        self.assertEqual(before, len(os.listdir("/proc/self/fd")))
        with self.gate.complete_gate_lock(root):
            pass

    def test_busy_receipt_is_distinct_and_integrity_bound(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        path = self.gate.write_busy_receipt(root)
        self.assertIn("complete-gate-busy", path.parts)
        payload = json.loads(path.read_text(encoding="utf-8"))
        digest = payload.pop("evidenceDigest")
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(hashlib.sha256(canonical).hexdigest(), digest)
        self.assertEqual("busy", payload["overallStatus"])
        self.assertEqual("complete_gate_already_running", payload["diagnostic"])
        self.assertIsNone(payload["sourceCommit"])
        self.assertEqual([], payload["checks"])

    def test_records_failure_and_blocks_dependent_check(self):
        result, _ = self.run_gate(
            [
                check("bad", ["/bin/sh", "-c", "exit 7"], tools=["/bin/sh"]),
                check("later", ["/bin/true"], depends=["bad"], tools=["/bin/true"]),
            ]
        )
        self.assertEqual("failed", result["overallStatus"])
        self.assertEqual(["failed", "not_run"], [item["status"] for item in result["checks"]])

    def test_executes_later_declared_dependency_before_consumer(self):
        result, _ = self.run_gate(
            [
                check("consumer", ["/bin/true"], depends=["provider"], tools=["/bin/true"]),
                check("provider", ["/bin/true"], tools=["/bin/true"]),
            ]
        )
        self.assertEqual("passed", result["overallStatus"])
        self.assertEqual(["provider", "consumer"], [item["id"] for item in result["checks"]])

    def test_missing_required_tool_is_incomplete(self):
        result, _ = self.run_gate(
            [check("missing", ["never"], tools=["base2-tool-that-does-not-exist"])]
        )
        self.assertEqual("incomplete", result["overallStatus"])
        self.assertEqual("unavailable", result["checks"][0]["status"])

    def test_wsl_single_processor_runtime_fails_early_with_remedy(self):
        with (
            patch.object(self.gate.platform, "release", return_value="microsoft-standard-WSL2"),
            patch.object(self.gate.os, "cpu_count", return_value=1),
            self.assertRaisesRegex(RuntimeError, r"processors=2.*wsl --shutdown"),
        ):
            self.gate.validate_runtime_capacity()
        with (
            patch.object(self.gate.platform, "release", return_value="microsoft-standard-WSL2"),
            patch.object(self.gate.os, "cpu_count", return_value=2),
        ):
            self.gate.validate_runtime_capacity()

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

    def test_retries_shell_wrapped_sigsegv_once_and_records_recovery(self):
        command = [
            "/bin/sh",
            "-c",
            "if test -f marker; then echo passed; else touch marker; exit 139; fi",
        ]
        result, _ = self.run_gate([check("segfault", command, tools=["/bin/sh"], max_attempts=2)])
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

    def test_intentional_error_text_is_not_a_terminal_test_summary(self):
        command = [
            "/bin/sh",
            "-c",
            "if test -f marker; then echo 'Test Files 1 passed'; exit 0; "
            "else touch marker; echo 'Error: boom'; exit 1; fi",
        ]
        result, _ = self.run_gate(
            [
                check(
                    "abrupt",
                    command,
                    tools=["/bin/sh"],
                    max_attempts=2,
                    retry_on=["incomplete-test-output"],
                )
            ]
        )
        self.assertEqual("passed", result["overallStatus"])
        self.assertEqual(2, result["checks"][0]["attempts"])

    def test_retries_explicit_worker_crash_signature_once(self):
        command = [
            "/bin/sh",
            "-c",
            "if test -f marker; then echo passed; exit 0; "
            "else touch marker; echo 'Worker exited unexpectedly'; exit 1; fi",
        ]
        result, _ = self.run_gate([check("worker", command, tools=["/bin/sh"], max_attempts=2)])
        self.assertEqual("passed", result["overallStatus"])
        self.assertEqual(2, result["checks"][0]["attempts"])

        exhausted, _ = self.run_gate(
            [
                check(
                    "worker",
                    ["/bin/sh", "-c", "echo 'Worker exited unexpectedly'; exit 1"],
                    tools=["/bin/sh"],
                )
            ]
        )
        self.assertEqual("failed", exhausted["overallStatus"])
        self.assertEqual(2, exhausted["checks"][0]["attempts"])

    def test_retries_exact_json_encoder_corruption_but_not_application_type_error(self):
        corruption = (
            "/usr/lib/python3.12/json/encoder.py\n"
            "yield '\\n' + _indent * _current_indent_level\n"
            "TypeError: unsupported operand type(s) for *: 'NoneType' and 'int'"
        )
        command = [
            "/bin/sh",
            "-c",
            f"if test -f marker; then echo passed; exit 0; "
            f"else touch marker; printf '%s\\n' \"{corruption}\"; exit 1; fi",
        ]
        result, _ = self.run_gate(
            [check("json-corruption", command, tools=["/bin/sh"], max_attempts=2)]
        )
        self.assertEqual("passed", result["overallStatus"])
        self.assertEqual(2, result["checks"][0]["attempts"])

        exhausted, _ = self.run_gate(
            [
                check(
                    "json-corruption",
                    ["/bin/sh", "-c", f"printf '%s\\n' \"{corruption}\"; exit 1"],
                    tools=["/bin/sh"],
                )
            ]
        )
        self.assertEqual("failed", exhausted["overallStatus"])
        self.assertEqual(2, exhausted["checks"][0]["attempts"])

        self.assertFalse(
            self.gate.retryable_interpreter_corruption(
                "api/routes/settings.py TypeError: unsupported operand type(s) for *: "
                "'NoneType' and 'int'"
            )
        )
        self.assertFalse(
            self.gate.retryable_interpreter_corruption(
                "/usr/lib/python3.12/json/encoder.py AssertionError: expected 200"
            )
        )

    def test_retries_exact_django_field_counter_corruption_only(self):
        corruption = (
            "/site-packages/django/db/models/fields/__init__.py\n"
            "Field.creation_counter += 1\n"
            "TypeError: unsupported operand type(s) for +=: 'type' and 'int'"
        )
        command = [
            "/bin/sh",
            "-c",
            f"if test -f marker; then echo '6 passed'; exit 0; "
            f"else touch marker; printf '%s\\n' \"{corruption}\"; exit 1; fi",
        ]
        result, _ = self.run_gate(
            [check("django-counter", command, tools=["/bin/sh"], max_attempts=2)]
        )
        self.assertEqual("passed", result["overallStatus"])
        self.assertEqual(2, result["checks"][0]["attempts"])
        self.assertFalse(
            self.gate.retryable_interpreter_corruption(
                "app/models.py Field.creation_counter += 1 "
                "TypeError: unsupported operand type(s) for +=: 'type' and 'int'"
            )
        )
        self.assertFalse(
            self.gate.retryable_interpreter_corruption(
                "/django/db/models/fields/__init__.py Field.creation_counter += 1 "
                "AssertionError: migration mismatch"
            )
        )
        exhausted, _ = self.run_gate(
            [
                check(
                    "django-counter",
                    ["/bin/sh", "-c", f"printf '%s\\n' \"{corruption}\"; exit 1"],
                    tools=["/bin/sh"],
                )
            ]
        )
        self.assertEqual("failed", exhausted["overallStatus"])
        self.assertEqual(2, exhausted["checks"][0]["attempts"])

    def test_retries_two_exact_native_heap_corruptions_then_passes(self):
        corruption = (
            "Emalloc(): smallbin double linked list corrupted\n"
            "Fatal Python error: Aborted"
        )
        command = [
            "/bin/sh",
            "-c",
            "count=0; test ! -f attempts || count=$(cat attempts); count=$((count + 1)); "
            "printf '%s' \"$count\" > attempts; "
            f"if test \"$count\" -lt 3; then printf '%s\\n' \"{corruption}\"; exit 134; "
            "else echo '6 passed'; fi",
        ]
        result, _ = self.run_gate(
            [check("native-abort", command, tools=["/bin/sh"])]
        )
        self.assertEqual("passed", result["overallStatus"])
        self.assertEqual(3, result["checks"][0]["attempts"])
        self.assertIn("2 bounded infrastructure retries", result["checks"][0]["diagnostic"])

    def test_native_abort_requires_exact_heap_corruption_conjunction(self):
        self.assertFalse(self.gate.retryable_native_crash(134, "Fatal Python error: Aborted"))
        self.assertFalse(
            self.gate.retryable_native_crash(
                1, "Fatal Python error: Aborted smallbin double linked list corrupted"
            )
        )
        self.assertFalse(self.gate.retryable_native_crash(134, "AssertionError: expected"))
        self.assertTrue(
            self.gate.retryable_native_crash(
                -6, "smallbin double linked list corrupted\nFatal Python error: Aborted"
            )
        )

    def test_gate_children_receive_deterministic_python_runtime(self):
        result, output = self.run_gate(
            [
                check(
                    "runtime",
                    ["/bin/sh", "-c", "printf '%s %s' \"$PYTHONHASHSEED\" \"$PYTHONMALLOC\""],
                    tools=["/bin/sh"],
                )
            ],
            env={**os.environ, "PYTHONHASHSEED": "random", "PYTHONMALLOC": "pymalloc"},
        )
        self.assertEqual("passed", result["overallStatus"])
        self.assertIn("0 malloc", (output / "runtime.log").read_text(encoding="utf-8"))

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
        check_result = stored["checks"][0]
        self.assertEqual(hashlib.sha256(log.encode()).hexdigest(), check_result["artifactSha256"])
        self.assertEqual(len(log.encode()), check_result["artifactSize"])
        self.assertEqual(0o700, S_IMODE(output.stat().st_mode))
        self.assertEqual(0o600, S_IMODE((output / "echo.log").stat().st_mode))
        self.assertEqual(0o600, S_IMODE((output / "result.json").stat().st_mode))
        validated = self.gate.validate_gate_evidence(output / "result.json", output.parent)
        validated.pop("evidenceDigest")
        self.assertEqual(stored, validated)

    def test_gate_evidence_replay_rejects_log_tamper(self):
        result, output = self.run_gate(
            [check("echo", ["/bin/sh", "-c", "printf stable"], tools=["/bin/sh"])]
        )
        self.assertEqual("passed", result["overallStatus"])
        (output / "echo.log").write_text("tampered", encoding="utf-8")
        os.chmod(output / "echo.log", 0o600)
        with self.assertRaisesRegex(ValueError, "artifact_integrity_invalid"):
            self.gate.validate_gate_evidence(output / "result.json", output.parent)

    def test_gate_evidence_replay_rejects_public_result_mode(self):
        result, output = self.run_gate(
            [check("echo", ["/bin/sh", "-c", "printf stable"], tools=["/bin/sh"])]
        )
        self.assertEqual("passed", result["overallStatus"])
        os.chmod(output / "result.json", 0o644)
        with self.assertRaisesRegex(ValueError, "result_unsafe"):
            self.gate.validate_gate_evidence(output / "result.json", output.parent)

    def test_gate_evidence_replay_rejects_public_directory_without_repair(self):
        result, output = self.run_gate(
            [check("echo", ["/bin/sh", "-c", "printf stable"], tools=["/bin/sh"])]
        )
        self.assertEqual("passed", result["overallStatus"])
        os.chmod(output, 0o755)
        with self.assertRaisesRegex(ValueError, "unsafe_private_directory"):
            self.gate.validate_gate_evidence(output / "result.json", output.parent)
        self.assertEqual(0o755, S_IMODE(output.stat().st_mode))

    def test_gate_evidence_replay_does_not_create_missing_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            missing = root / "missing" / "result.json"
            with self.assertRaises(FileNotFoundError):
                self.gate.validate_gate_evidence(missing, root)
            self.assertFalse(missing.parent.exists())

    def test_gate_evidence_replay_rejects_hardlinked_log(self):
        result, output = self.run_gate(
            [check("echo", ["/bin/sh", "-c", "printf stable"], tools=["/bin/sh"])]
        )
        self.assertEqual("passed", result["overallStatus"])
        external = output.parent / "external-log-link"
        os.link(output / "echo.log", external)
        with self.assertRaisesRegex(ValueError, "artifact_unsafe"):
            self.gate.validate_gate_evidence(output / "result.json", output.parent)

    def test_gate_evidence_rejects_symlinked_output_parent_and_preserves_target(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        (root / ".git").mkdir()
        outside = root / "outside"
        outside.mkdir()
        marker = outside / "marker"
        marker.write_text("preserve", encoding="utf-8")
        (root / "evidence").symlink_to(outside, target_is_directory=True)
        with self.assertRaises(OSError):
            self.gate.run_gate(
                {"schemaVersion": 1, "checks": [check("ok", ["/bin/true"], tools=["/bin/true"])]},
                root,
                root / "evidence",
                source_commit="0" * 40,
            )
        self.assertEqual("preserve", marker.read_text(encoding="utf-8"))

    def test_gate_closes_evidence_descriptor_when_member_write_fails(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        (root / ".git").mkdir()
        before = len(os.listdir("/proc/self/fd"))
        with patch.object(
            self.gate, "private_write", side_effect=OSError("fixture write failure")
        ), self.assertRaisesRegex(OSError, "fixture write failure"):
            self.gate.run_gate(
                {"schemaVersion": 1, "checks": [check("ok", ["/bin/true"], tools=["/bin/true"])]},
                root,
                root / "evidence",
                source_commit="0" * 40,
            )
        self.assertEqual(before, len(os.listdir("/proc/self/fd")))

    def test_gate_evidence_rejects_symlinked_log_and_preserves_target(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        (root / ".git").mkdir()
        output = root / "evidence"
        output.mkdir()
        target = root / "target"
        target.write_text("preserve", encoding="utf-8")
        (output / "ok.log").symlink_to(target)
        with self.assertRaises(OSError):
            self.gate.run_gate(
                {"schemaVersion": 1, "checks": [check("ok", ["/bin/true"], tools=["/bin/true"])]},
                root,
                output,
                source_commit="0" * 40,
            )
        self.assertEqual("preserve", target.read_text(encoding="utf-8"))

    def test_gate_evidence_rejects_symlinked_result_and_preserves_target(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        (root / ".git").mkdir()
        output = root / "evidence"
        output.mkdir()
        target = root / "target"
        target.write_text("preserve", encoding="utf-8")
        (output / "result.json").symlink_to(target)
        with self.assertRaisesRegex(ValueError, "unsafe_private_result_member"):
            self.gate.run_gate(
                {"schemaVersion": 1, "checks": [check("ok", ["/bin/true"], tools=["/bin/true"])]},
                root,
                output,
                source_commit="0" * 40,
            )
        self.assertEqual("preserve", target.read_text(encoding="utf-8"))

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
        self.assertEqual(
            ["python3", "-m", "unittest", "scripts.tests.test_module_registry"],
            commands["module-registry-contract"],
        )
        self.assertEqual(
            ["python3", "-m", "unittest", "scripts.tests.test_module_lifecycle"],
            commands["module-lifecycle-contract"],
        )
        self.assertEqual(
            ["python3", "-m", "unittest", "scripts.tests.test_content_pack_manifests"],
            commands["content-pack-contract"],
        )
        self.assertEqual(
            ["python3", "-m", "unittest", "scripts.tests.test_interaction_pack_manifests"],
            commands["interaction-pack-contract"],
        )
        self.assertEqual(
            [
                "{python-orchestrator}",
                "-m",
                "unittest",
                "scripts.tests.test_site_manifest",
            ],
            commands["site-manifest-contract"],
        )
        self.assertEqual(
            ["{python-api}", "scripts/python/run_api_coverage.py"],
            commands["api-tests"],
        )
        self.assertEqual(
            ["{python-api}", "-m", "mypy", "api"],
            commands["api-typecheck"],
        )
        self.assertEqual(
            [
                "{python-django}",
                "-m",
                "mypy",
                "--exclude",
                ".*/migrations/.*",
                "django",
            ],
            commands["django-typecheck"],
        )
        self.assertEqual(
            ["npm", "--prefix", "react-app", "audit", "--audit-level=moderate"],
            commands["frontend-production-audit"],
        )
        self.assertEqual(
            [
                "npm",
                "--prefix",
                "react-app",
                "ci",
                "--dry-run",
                "--ignore-scripts",
                "--legacy-peer-deps",
            ],
            commands["frontend-lockfile-sync"],
        )
        api_check = next(item for item in manifest["checks"] if item["id"] == "api-tests")
        self.assertEqual(300, api_check["timeoutSeconds"])
        self.assertGreater(api_check["timeoutSeconds"], 120)
        self.assertLessEqual(api_check["timeoutSeconds"], 300)
        self.assertEqual(
            ["{python-django}", "scripts/python/run_django_coverage.py"],
            commands["django-tests"],
        )
        for check_id in (
            "operations-domain-contract",
            "site-content-models",
            "identity-domain-models",
            "media-library-django-contract",
        ):
            command = commands[check_id]
            self.assertIn("addopts=", command)
            self.assertIn("no:cov", command)
        self.assertEqual(
            ["{python-orchestrator}", "scripts/python/run_digitalocean_coverage.py"],
            commands["digitalocean-tests"],
        )
        self.assertEqual(
            ["{python-api}", "scripts/python/run_data_rights_matrix.py"],
            commands["data-rights-contract"],
        )
        self.assertEqual(
            ["python3", "-m", "unittest", "scripts.tests.test_identity_postgres_contract"],
            commands["identity-postgres-contract"],
        )
        self.assertEqual(
            [
                "{python-orchestrator}",
                "digital_ocean/scripts/python/providerless_canary.py",
            ],
            commands["providerless-deployment-canary"],
        )
        self.assertEqual(
            [
                "{python-orchestrator}",
                "-m",
                "pytest",
                "digital_ocean/tests/test_live_canary_preflight.py",
                "-q",
            ],
            commands["live-canary-preflight-contract"],
        )
        django_wrapper = (repo_root / "scripts/python/run_django_coverage.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('"django/pytest.ini"', django_wrapper)
        self.assertIn('environment["COVERAGE_CORE"] = "sysmon"', django_wrapper)
        self.assertEqual(
            ["python3", "scripts/python/validate_compose_config.py"], commands["compose-config"]
        )
        powershell = (repo_root / "scripts/powershell/install-python-deps.ps1").read_text(
            encoding="utf-8"
        )
        for name in (".venv-api", ".venv-django", ".venv"):
            self.assertIn(name, powershell)

    def test_digitalocean_coverage_uses_deterministic_sysmon_tracer(self):
        repo_root = MODULE_PATH.parents[2]
        wrapper = (repo_root / "scripts/python/run_digitalocean_coverage.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("'COVERAGE_CORE': 'sysmon'", wrapper)
        self.assertIn("'digital_ocean' / 'tests'", wrapper)
        self.assertIn("'--source=digital_ocean/scripts/python'", wrapper)
        self.assertIn("'--parallel-mode'", wrapper)

    def test_data_rights_matrix_is_isolated_and_native_crash_bounded(self):
        repo_root = MODULE_PATH.parents[2]
        wrapper = (repo_root / "scripts/python/run_data_rights_matrix.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("MAX_ATTEMPTS = 3", wrapper)
        self.assertIn("NATIVE_FAILURES = {-11, 134, 139}", wrapper)
        self.assertIn("'-p', 'no:cov'", wrapper)
        for test_file in (
            "api/tests/contract/test_data_rights_contract.py",
            "api/tests/security/test_data_rights_restore.py",
            "api/tests/test_data_rights_repository.py",
            "api/tests/test_data_rights_worker.py",
            "api/tests/test_data_rights_tasks.py",
        ):
            self.assertIn(test_file, wrapper)

    def test_python_coverage_surfaces_use_their_verified_tracing_core(self):
        repo_root = MODULE_PATH.parents[2]
        for service in ("api", "django"):
            requirements = (repo_root / service / "requirements.txt").read_text(encoding="utf-8")
            self.assertIn("coverage[toml]==7.16.0", requirements)
            self.assertNotIn("coverage[toml]==7.15.4", requirements)
        api_wrapper = (repo_root / "scripts/python/run_api_coverage.py").read_text(encoding="utf-8")
        self.assertIn("environment['COVERAGE_CORE'] = 'ctrace'", api_wrapper)
        self.assertIn("(root / 'api' / 'tests').rglob('test_*.py')", api_wrapper)
        self.assertIn("coverage_dir / 'api.json'", api_wrapper)
        self.assertIn("PARTITION_SIZE = 4", api_wrapper)
        expected = {
            "run_django_coverage.py": (
                "sysmon",
                "django/tests",
                ".artifacts/coverage/django.json",
            ),
        }
        for name, (core, *markers) in expected.items():
            wrapper = (repo_root / "scripts/python" / name).read_text(encoding="utf-8")
            self.assertIn(f'environment["COVERAGE_CORE"] = "{core}"', wrapper)
            for marker in markers:
                self.assertIn(marker, wrapper)
        digitalocean_wrapper = (
            repo_root / "scripts/python/run_digitalocean_coverage.py"
        ).read_text(encoding="utf-8")
        self.assertIn("'COVERAGE_CORE': 'sysmon'", digitalocean_wrapper)
        self.assertIn("'digital_ocean' / 'tests'", digitalocean_wrapper)
        self.assertIn("coverage_dir / 'digitalocean.json'", digitalocean_wrapper)
        self.assertIn("PARTITION_SIZE = 4", digitalocean_wrapper)

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
