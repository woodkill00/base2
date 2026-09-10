import importlib.util
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

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

    def test_does_not_confuse_scanner_action_input_with_service_image(self):
        body = (
            "on:\n  pull_request:\njobs:\n  gate:\n    steps:\n"
            "      - uses: anchore/sbom-action@" + "a" * 40 + "\n"
            "        with:\n          image: locally-built:security\n"
        )
        self.assertEqual([], self.scan(body))

    def test_rejects_deeply_indented_mutable_service_image(self):
        body = (
            "on:\n  pull_request:\njobs:\n  gate:\n    services:\n"
            "          unusual-db:\n            image: postgres:16\n"
            "    steps:\n      - run: scan\n"
        )
        findings = self.scan(body)
        self.assertTrue(any("mutable image postgres:16" in item for item in findings))

    def test_current_repository_satisfies_t019_policy(self):
        repo_root = MODULE_PATH.parents[2]
        policy = __import__("json").loads((repo_root / "scripts/config/ci-policy.json").read_text(encoding="utf-8"))
        findings = self.policy.validate(repo_root, policy)
        self.assertEqual([], findings)

    def test_backend_ci_uses_pinned_dev_tools_and_complete_schema_order(self):
        repo_root = MODULE_PATH.parents[2]
        workflow = (repo_root / ".github/workflows/ci-backend.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("python -m pip install -r requirements-dev-api.txt", workflow)
        self.assertIn("python -m pip install -r requirements-dev-django.txt", workflow)
        self.assertIn("python -m pip check", workflow)
        self.assertNotIn("python -m pip install ruff mypy", workflow)
        self.assertIn("python -m mypy api", workflow)
        self.assertIn("python -m mypy --exclude '.*/migrations/.*' django", workflow)
        bootstrap = workflow.index("/bin/sh postgres/bootstrap-workspace-role.sh")
        api_migrate = workflow.index("python -m api.scripts.migrate", bootstrap)
        django_migrate = workflow.index("python manage.py migrate --noinput", api_migrate)
        integration = workflow.index("pytest -q -m integration", django_migrate)
        self.assertLess(bootstrap, api_migrate)
        self.assertLess(api_migrate, django_migrate)
        self.assertLess(django_migrate, integration)
        self.assertNotIn("manage.py migrate api_schema", workflow)
        self.assertIn('DB_USER="$API_RUNTIME_DB_USER"', workflow)
        self.assertIn("EMAIL_WORKER_DB_USER: ci_email_worker", workflow)
        self.assertIn(
            "pytest -q -m integration tests/test_email_outbox.py -c pytest.ini",
            workflow,
        )

    def test_staged_api_python_is_linted_with_the_pinned_environment(self):
        repo_root = MODULE_PATH.parents[2]
        lint_staged = __import__("json").loads(
            (repo_root / ".lintstagedrc.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            [".venv-api/bin/python -m ruff check"],
            lint_staged["api/**/*.py"],
        )

    def test_media_inspector_build_inputs_are_immutable_and_scanned(self):
        repo_root = MODULE_PATH.parents[2]
        dockerfile = (repo_root / "api/Dockerfile.media-inspector").read_text(encoding="utf-8")
        requirements = (repo_root / "api/requirements-media-inspector.txt").read_text(
            encoding="utf-8"
        )
        workflow = (repo_root / ".github/workflows/security.yml").read_text(encoding="utf-8")

        self.assertEqual("ARG TARGETPLATFORM=linux/amd64", dockerfile.splitlines()[0])
        self.assertIn("RUN test \"$TARGETPLATFORM\" = 'linux/amd64'", dockerfile)
        self.assertIn(
            "FROM --platform=linux/amd64 clamav/clamav@sha256:1fdfd24c6f0a0fb60788481487459a6d4eda8a9b448641594e04db8410d34422 AS clamav-definitions",
            dockerfile,
        )
        self.assertIn("cgr.dev/chainguard/python@sha256:c23539f", dockerfile)
        self.assertIn("cgr.dev/chainguard/python@sha256:1f37785", dockerfile)
        self.assertIn("mwader/static-ffmpeg@sha256:54e55b0c", dockerfile)
        self.assertIn("clamav-1.5.4.linux.x86_64.deb", dockerfile)
        self.assertIn(
            "28d6efc5b4423e7830c3559339552eb53870a9eac51ac4efb37d60530d329886",
            dockerfile,
        )
        self.assertNotIn("clamav-1.5-scanner=", dockerfile)
        self.assertIn("/tmp/clamav/control /var/lib/dpkg/status", dockerfile)
        self.assertNotIn("apk add", dockerfile)
        self.assertNotIn("apt-get", dockerfile)
        self.assertIn("--only-binary=:all: --no-deps --require-hashes", dockerfile)
        self.assertIn("--target /tmp/vendor", dockerfile)
        self.assertIn("PYTHONPATH=/app/vendor:/app", dockerfile)
        package_lines = [
            line for line in requirements.splitlines() if line and not line.startswith("#")
        ]
        self.assertTrue(package_lines)
        pins = [line for line in package_lines if "==" in line]
        hashes = [line for line in package_lines if "--hash=sha256:" in line]
        self.assertEqual(5, len(pins))
        self.assertEqual(5, len(hashes))
        self.assertTrue(all(len(line.rsplit(":", 1)[1]) == 64 for line in hashes))
        self.assertIn("docker build --platform linux/amd64", workflow)
        self.assertIn("--target media-inspector-production", workflow)
        self.assertIn("--target media-inspector-acceptance", workflow)
        self.assertIn("base2-media-inspector:acceptance", workflow)
        self.assertIn("Verify production inspector excludes acceptance code", workflow)
        self.assertIn(
            "Path('/app/api/tests/media_inspector_acceptance_entrypoint.py').exists()",
            workflow,
        )
        self.assertIn("FROM media-inspector-production AS media-inspector-acceptance", dockerfile)
        self.assertIn("FROM media-inspector-production AS media-inspector-final", dockerfile)
        production_section = dockerfile.split(
            "FROM media-inspector-production AS media-inspector-acceptance", 1
        )[0]
        self.assertNotIn("media_inspector_acceptance_entrypoint", production_section)
        self.assertNotIn("media_inspector_container_acceptance", production_section)
        self.assertIn("Exercise hardened media inspector supervisor", workflow)
        self.assertIn("Exercise hardened ClamAV updater lifecycle", workflow)
        self.assertIn("bash api/tests/clamav_updater_container_acceptance.sh", workflow)
        for compose_name in ("local.docker.yml", "development.docker.yml"):
            compose = __import__("yaml").safe_load(
                (repo_root / compose_name).read_text(encoding="utf-8")
            )
            self.assertEqual(["clamav_egress"], compose["services"]["clamav"]["networks"])
            self.assertFalse(compose["networks"]["clamav_egress"]["internal"])
            peers = [
                name
                for name, service in compose["services"].items()
                if "clamav_egress" in service.get("networks", [])
            ]
            self.assertEqual(["clamav"], peers)
        self.assertIn("--network none", workflow)
        self.assertIn("--read-only", workflow)
        self.assertIn("--cap-drop ALL", workflow)
        self.assertIn("--security-opt no-new-privileges", workflow)
        self.assertIn("media_inspector_container_acceptance.py", workflow)
        self.assertIn("media_inspector_two_uid_container_acceptance.sh", workflow)
        self.assertIn("media-inspector-sbom.cdx.json", workflow)
        self.assertIn(
            "if: always() && steps.inspector-grype.outputs.sarif != ''",
            workflow,
        )
        self.assertIn("media-inspector-grype.normalized.json", workflow)
        producer = (
            repo_root / "api/tests/media_inspector_two_uid_producer.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("shutil.rmtree", producer)
        updater_acceptance = (
            repo_root / "api/tests/clamav_updater_container_acceptance.sh"
        ).read_text(encoding="utf-8")
        self.assertIn("readonly evidence_timeout_seconds=120", updater_acceptance)
        self.assertIn("readonly evidence_safety_margin_seconds=6", updater_acceptance)
        self.assertIn("readonly command_timeout_seconds=30", updater_acceptance)
        self.assertIn("readonly evidence_kill_grace_seconds=5", updater_acceptance)
        self.assertIn("readonly cleanup_timeout_seconds=10", updater_acceptance)
        self.assertIn("readonly cleanup_kill_grace_seconds=5", updater_acceptance)
        self.assertLess(
            updater_acceptance.index('evidence_deadline='),
            updater_acceptance.index('start_updater 24'),
        )
        self.assertIn(
            '--kill-after="$evidence_kill_grace_seconds"',
            updater_acceptance,
        )
        self.assertIn('reject_timeout "$identity_status"', updater_acceptance)
        self.assertIn('reject_timeout "$health_status"', updater_acceptance)
        self.assertIn('bounded cleanup will now remove the exact container and volume', updater_acceptance)
        self.assertNotIn("$(docker exec", updater_acceptance)
        self.assertIn("--memory 1024m", updater_acceptance)
        self.assertIn('--reference-epoch "$reference_epoch"', updater_acceptance)
        self.assertIn('fixedReferenceClock', updater_acceptance)
        self.assertIn('docker_call logs "$container" >&2 || true', updater_acceptance)
        inspector_acceptance = (
            repo_root / "api/tests/media_inspector_container_acceptance.py"
        ).read_text(encoding="utf-8")
        self.assertIn("media_inspector_acceptance_entrypoint.py", inspector_acceptance)
        self.assertIn("reference_now = definitions_at + timedelta(hours=1)", inspector_acceptance)
        self.assertIn("observed_at=observed_at", inspector_acceptance)
        production_profiles = "\n".join(
            (repo_root / name).read_text(encoding="utf-8")
            for name in ("local.docker.yml", "development.docker.yml")
        )
        self.assertNotIn("media_inspector_acceptance_entrypoint", production_profiles)
        self.assertNotIn("--reference-epoch", production_profiles)

    def test_updater_acceptance_hung_docker_stays_inside_total_bounded_window(self):
        repo_root = MODULE_PATH.parents[2]
        source = (
            repo_root / "api/tests/clamav_updater_container_acceptance.sh"
        ).read_text(encoding="utf-8")
        source = source.replace("evidence_timeout_seconds=120", "evidence_timeout_seconds=4")
        source = source.replace(
            "evidence_safety_margin_seconds=6", "evidence_safety_margin_seconds=2"
        )
        source = source.replace("command_timeout_seconds=30", "command_timeout_seconds=1")
        source = source.replace(
            "evidence_kill_grace_seconds=5", "evidence_kill_grace_seconds=1"
        )
        source = source.replace("cleanup_timeout_seconds=10", "cleanup_timeout_seconds=1")
        source = source.replace("cleanup_kill_grace_seconds=5", "cleanup_kill_grace_seconds=1")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            script = root / "acceptance.sh"
            script.write_text(source, encoding="utf-8")
            fake_docker = root / "docker"
            fake_docker.write_text(
                "#!/bin/sh\n"
                "if test ! -e \"$FAKE_DOCKER_STATE\"; then\n"
                "  test \"${1-}\" = rm && exit 0\n"
                "  if test \"${1-}:${2-}\" = volume:rm; then\n"
                "    : > \"$FAKE_DOCKER_STATE\"\n"
                "    exit 0\n"
                "  fi\n"
                "fi\n"
                "exec python3 -c 'import signal,time; "
                "signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(60)'\n",
                encoding="utf-8",
            )
            fake_docker.chmod(0o755)
            started = time.monotonic()
            completed = subprocess.run(
                ["/bin/sh", str(script)],
                capture_output=True,
                check=False,
                env={
                    **os.environ,
                    "FAKE_DOCKER_STATE": str(root / "initial-cleanup-complete"),
                    "PATH": f"{root}:{os.environ['PATH']}",
                },
                text=True,
            )
            elapsed = time.monotonic() - started
        self.assertIn(completed.returncode, (124, 137))
        # Four seconds for the public evidence ceiling plus at most four for
        # the reduced two-command cleanup allowance used by this fixture.
        self.assertLess(elapsed, 8.0)
        self.assertIn("bounded Docker operation timed out", completed.stderr)

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
        self.assertEqual(10, compose.count("mirror.gcr.io/library"))
        self.assertEqual(2, compose.count("mirror.gcr.io/library/postgres@sha256:"))
        self.assertEqual(1, compose.count("mirror.gcr.io/library/redis@sha256:"))

    def test_isolated_e2e_port_names_are_exactly_documented(self):
        repo_root = MODULE_PATH.parents[2]
        compose_text = (repo_root / "e2e/docker-compose.e2e.yml").read_text(encoding="utf-8")
        compose = __import__("yaml").safe_load(compose_text)
        guide = (repo_root / "docs/TESTING.md").read_text(encoding="utf-8")
        runner = (repo_root / "scripts/bash/e2e-isolated.sh").read_text(encoding="utf-8")
        concurrency_proof = (
            repo_root / "scripts/bash/e2e-isolated-concurrency-proof.sh"
        ).read_text(encoding="utf-8")
        for variable in ("E2E_API_PORT", "E2E_TEST_SUPPORT_PORT", "E2E_WEB_PORT"):
            self.assertIn(f"${{{variable}:-", compose_text)
            self.assertIn(variable, guide)
            self.assertIn(f'validate_port {variable} "${variable}"', runner)
        for service in ("api", "test-support", "react-app"):
            published = compose["services"][service]["ports"][0]
            self.assertTrue(published.startswith("127.0.0.1:"), published)
        self.assertEqual(
            "${E2E_WEB_ORIGIN:-http://localhost:8080}",
            compose["services"]["api"]["environment"]["CORS_ALLOW_ORIGINS"],
        )
        nginx = (repo_root / "react-app/nginx/default.conf").read_text(encoding="utf-8")
        self.assertIn("location /api/", nginx)
        self.assertIn("proxy_pass http://api:5001;", nginx)
        self.assertNotIn("E2E_BROWSER_API_URL", compose_text + guide + runner)
        self.assertIn('project="base2-e2e-isolated"', runner)
        self.assertIn('lock_file="$repo_root/.artifacts/e2e-isolated.lock"', runner)
        self.assertIn('scripts/python/secure_file_lock.py', runner)
        self.assertIn("--held-environment BASE2_E2E_LOCK_HELD", runner)
        self.assertNotIn("e2e-isolated.lock-ready", runner + concurrency_proof)
        self.assertLess(
            runner.index('if [[ "${BASE2_E2E_LOCK_HELD:-}" != 1 ]]'),
            runner.index("compose=(docker compose"),
        )
        self.assertIn('trap cleanup EXIT INT TERM', runner)
        self.assertGreaterEqual(runner.count('down -v --remove-orphans'), 1)
        self.assertIn(
            'http://127.0.0.1:$E2E_TEST_SUPPORT_PORT/synthetic-health', runner
        )
        self.assertIn('scripts/bash/e2e-isolated.sh', guide)
        self.assertIn('contender_rc" -ne 3', concurrency_proof)
        self.assertIn("coproc OWNER", concurrency_proof)
        self.assertIn("E2E_READY_FD=3", concurrency_proof)
        self.assertIn("read -r -t 20 owner_ready", concurrency_proof)
        self.assertIn("mktemp -d --tmpdir", concurrency_proof)
        self.assertNotIn("flock -n", concurrency_proof)
        self.assertIn("inventory=empty", concurrency_proof)

    def test_e2e_workflow_waits_for_synthetic_support_readiness(self):
        repo_root = MODULE_PATH.parents[2]
        workflow = (repo_root / ".github/workflows/ci-e2e.yml").read_text(encoding="utf-8")
        compose = (repo_root / "e2e/docker-compose.e2e.yml").read_text(encoding="utf-8")
        self.assertIn("http://localhost:5002/synthetic-health", workflow)
        self.assertIn("conn.request(''GET'', ''/synthetic-health'')", compose)
        self.assertIn("test-support:\n", compose)

    def test_backend_and_postgres_acceptance_avoid_anonymous_public_ecr(self):
        repo_root = MODULE_PATH.parents[2]
        workflow = (repo_root / ".github" / "workflows" / "ci-backend.yml").read_text()
        acceptance = (
            repo_root / "scripts" / "python" / "run_workspace_postgres_acceptance.py"
        ).read_text()
        combined = workflow + acceptance
        self.assertNotIn("public.ecr.aws/docker/library", combined)
        self.assertNotIn('"postgres:16-alpine"', acceptance)
        self.assertEqual(2, workflow.count("mirror.gcr.io/library/"))
        self.assertEqual(1, acceptance.count("mirror.gcr.io/library/postgres@sha256:"))

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
