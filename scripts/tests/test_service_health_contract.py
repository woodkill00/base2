from __future__ import annotations

import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
COMPOSE = yaml.safe_load((ROOT / "development.docker.yml").read_text(encoding="utf-8"))
SERVICES = COMPOSE["services"]


def health_command(service: str) -> str:
    health = SERVICES[service].get("healthcheck") or {}
    test = health.get("test") or []
    return " ".join(str(part) for part in test)


class ServiceHealthContractTests(unittest.TestCase):
    def test_start_parses_environment_override_before_validation(self):
        script = (ROOT / "scripts/bash/start.sh").read_text(encoding="utf-8")
        parse_end = script.index("# Validate the selected environment")
        self.assertLess(script.index("--env-file|-e)"), parse_end)
        self.assertLess(script.index('ENV_FILE="$2"'), parse_end)
        self.assertGreater(script.index('if [ ! -f "$ENV_FILE" ]', parse_end), parse_end)
        self.assertNotIn("cp .env.example .env.build", script)
        self.assertIn('bash "$SCRIPT_DIR/sync-env.sh"', script)

    def test_local_api_gate_uses_ephemeral_read_only_contract_mounts(self):
        script = (ROOT / "scripts/bash/test.sh").read_text(encoding="utf-8")
        local_branch = script[script.index('if [ "$USE_LOCAL_STACK" = true ]') :]
        self.assertIn("run --rm -T --no-deps", local_branch)
        self.assertEqual(2, script.count('"${API_PYTEST_CONFIG[@]}" api/tests'))
        for binding in (
            '"$PWD/django:/app/django:ro"',
            '"$PWD/docs:/app/docs:ro"',
            '"$PWD/local.docker.yml:/app/local.docker.yml:ro"',
            '"$PWD/development.docker.yml:/app/development.docker.yml:ro"',
            '"$PWD/.coveragerc:/app/.coveragerc:ro"',
        ):
            self.assertIn(binding, local_branch)
        self.assertIn("else\n        $COMPOSE_CMD exec -T", local_branch)

    def test_frontend_native_crash_retry_is_bounded_and_fail_closed(self):
        script = (ROOT / "scripts/bash/test.sh").read_text(encoding="utf-8")
        self.assertEqual(2, script.count("run_frontend_tests\n"))
        self.assertEqual(1, script.count('if [ "$FRONTEND_EXIT_CODE" -eq 139 ]'))
        self.assertIn("a second crash or any ordinary test failure remains a hard failure", script)
        self.assertIn("if [ $BACKEND_EXIT_CODE -eq 0 ] && [ $FRONTEND_EXIT_CODE -eq 0 ]", script)

    def test_python_native_crash_retries_are_bounded_and_fail_closed(self):
        script = (ROOT / "scripts/bash/test.sh").read_text(encoding="utf-8")
        self.assertEqual(2, script.count("run_api_tests\n"))
        self.assertEqual(2, script.count("run_django_tests\n"))
        self.assertEqual(1, script.count('if [ "$API_EXIT_CODE" -eq 139 ]'))
        self.assertEqual(1, script.count('if [ "$DJANGO_EXIT_CODE" -eq 139 ]'))
        self.assertIn("a second crash or any ordinary test failure remains a hard failure", script)
        self.assertIn("if [ $API_EXIT_CODE -ne 0 ] || [ $DJANGO_EXIT_CODE -ne 0 ]", script)

    def test_every_runtime_service_has_meaningful_health(self):
        expected = {
            "react-app": ("wget", "http://localhost:8080/"),
            "api": ("python", "/api/health"),
            "django": ("python", "/internal/health"),
            "nginx": ("curl", "http://localhost:${NGINX_PORT}/"),
            "nginx-static": ("wget", "/health"),
            "postgres": ("pg_isready", "${POSTGRES_DB}"),
            "pgadmin": ("wget", "/misc/ping"),
            "redis": ("redis-cli", "PONG"),
            "celery-worker": ("python", "workers:runtime-worker"),
            "celery-content-worker": ("python", "workers:content-worker"),
            "celery-data-rights-worker": ("python", "workers:data-rights-worker"),
            "celery-email-worker": ("python", "workers:email-worker"),
            "celery-beat": ("python", "_runtime_heartbeat", "schedules"),
            "flower": ("python", "HTTPConnection", "5555"),
        }
        for service, markers in expected.items():
            command = health_command(service)
            with self.subTest(service=service):
                self.assertTrue(command, f"{service} lacks healthcheck")
                for marker in markers:
                    self.assertIn(marker, command)

    def test_health_commands_use_installed_binaries(self):
        dockerfiles = {
            "react-app": (ROOT / "react-app/Dockerfile").read_text(encoding="utf-8"),
            "api": (ROOT / "api/Dockerfile").read_text(encoding="utf-8"),
            "django": (ROOT / "django/Dockerfile").read_text(encoding="utf-8"),
            "nginx": (ROOT / "nginx/Dockerfile").read_text(encoding="utf-8"),
        }
        self.assertIn("apk add --no-cache wget", dockerfiles["react-app"])
        self.assertIn("FROM ${DOCKER_LIBRARY_REGISTRY}/python:", dockerfiles["api"])
        self.assertIn("FROM ${DOCKER_LIBRARY_REGISTRY}/python:", dockerfiles["django"])
        self.assertIn("apk add --no-cache gettext curl", dockerfiles["nginx"])
        self.assertNotIn("curl", health_command("react-app"))
        self.assertNotIn("wget", health_command("flower"))

    def test_nginx_static_health_avoids_localhost_ipv6_ambiguity(self):
        command = health_command("nginx-static")
        self.assertIn("http://127.0.0.1:8081/health", command)
        self.assertNotIn("http://localhost:8081/health", command)

    def test_api_waits_for_every_required_readiness_dependency(self):
        dependencies = SERVICES["api"]["depends_on"]
        self.assertEqual("service_healthy", dependencies["postgres"]["condition"])
        self.assertEqual("service_healthy", dependencies["redis"]["condition"])

    def test_flower_broker_secret_is_environment_only_and_never_in_argv(self):
        flower = SERVICES["flower"]
        environment = flower.get("environment") or []
        command = " ".join(str(part) for part in (flower.get("command") or []))

        self.assertIn(
            "CELERY_BROKER_URL=redis://:${REDIS_PASSWORD}@redis:6379/0",
            environment,
        )
        self.assertNotIn("REDIS_PASSWORD", command)
        self.assertNotIn("redis://", command)
        self.assertNotIn("--broker", command)

    def test_runtime_worker_does_not_receive_identity_secrets(self):
        api_environment = SERVICES["api"].get("environment") or []
        worker_environment = SERVICES["celery-worker"].get("environment") or []
        for binding in (
            "TOKEN_PEPPER=${TOKEN_PEPPER}",
            "IDENTITY_ENCRYPTION_KEY=${IDENTITY_ENCRYPTION_KEY}",
        ):
            self.assertIn(binding, api_environment)
            self.assertNotIn(binding, worker_environment)
        worker_command = " ".join(
            str(part) for part in (SERVICES["celery-worker"].get("command") or [])
        )
        self.assertNotIn("TOKEN_PEPPER", worker_command)
        self.assertNotIn("IDENTITY_ENCRYPTION_KEY", worker_command)

    def test_worker_and_scheduler_use_only_the_narrow_worker_database_identity(self):
        for name in ("celery-worker", "celery-beat"):
            environment = SERVICES[name].get("environment") or []
            self.assertIn("DB_USER=${RUNTIME_WORKER_DB_USER}", environment)
            self.assertIn("DB_PASSWORD=${RUNTIME_WORKER_DB_PASSWORD}", environment)
            self.assertIn("WORKSPACE_DB_USER=${RUNTIME_WORKER_DB_USER}", environment)
            self.assertIn("WORKSPACE_DB_PASSWORD=${RUNTIME_WORKER_DB_PASSWORD}", environment)
            self.assertNotIn("DB_USER=${POSTGRES_USER}", environment)
            self.assertNotIn("WORKSPACE_DB_USER=${WORKSPACE_DB_USER}", environment)

    def test_content_and_email_workers_use_distinct_least_privilege_identities(self):
        api = SERVICES["api"].get("environment") or []
        runtime = SERVICES["celery-worker"].get("environment") or []
        content = SERVICES["celery-content-worker"].get("environment") or []
        email = SERVICES["celery-email-worker"].get("environment") or []
        data_rights = SERVICES["celery-data-rights-worker"].get("environment") or []
        self.assertIn("DB_USER=${WORKSPACE_WORKER_DB_USER}", content)
        self.assertIn("DB_PASSWORD=${WORKSPACE_WORKER_DB_PASSWORD}", content)
        self.assertIn("WORKSPACE_WORKER_DB_USER=${WORKSPACE_WORKER_DB_USER}", content)
        self.assertNotIn("RUNTIME_WORKER_DB_PASSWORD=${RUNTIME_WORKER_DB_PASSWORD}", content)
        self.assertIn("DB_USER=${DATA_RIGHTS_WORKER_DB_USER}", data_rights)
        self.assertIn("DB_PASSWORD=${DATA_RIGHTS_WORKER_DB_PASSWORD}", data_rights)
        self.assertIn("TOKEN_PEPPER=${TOKEN_PEPPER}", data_rights)
        self.assertIn("IDENTITY_ENCRYPTION_KEY=${IDENTITY_ENCRYPTION_KEY}", data_rights)
        self.assertNotIn(
            "DATA_RIGHTS_WORKER_DB_PASSWORD=${DATA_RIGHTS_WORKER_DB_PASSWORD}", content
        )
        self.assertIn("DB_USER=${EMAIL_WORKER_DB_USER}", email)
        self.assertIn("DB_PASSWORD=${EMAIL_WORKER_DB_PASSWORD}", email)
        self.assertNotIn("WORKSPACE_DB_PASSWORD=${WORKSPACE_DB_PASSWORD}", email)
        self.assertNotIn("WORKSPACE_WORKER_DB_PASSWORD=${WORKSPACE_WORKER_DB_PASSWORD}", email)
        for environment in (api, runtime, content, data_rights):
            self.assertFalse(any(value.startswith("BASE2_EMAIL_") for value in environment))
        self.assertIn("BASE2_EMAIL_ADAPTER=${BASE2_EMAIL_ADAPTER:-disabled}", email)
        self.assertIn("BASE2_EMAIL_SMTP_PASSWORD_FILE=/run/secrets/email-smtp-password", email)

    def test_every_python_process_receives_explicit_environment_tls_and_role(self):
        expected_roles = {
            "api": "api",
            "celery-worker": "runtime-worker",
            "celery-content-worker": "content-worker",
            "celery-data-rights-worker": "data-rights-worker",
            "celery-email-worker": "email-worker",
            "celery-beat": "runtime-worker",
        }
        for name, role in expected_roles.items():
            environment = SERVICES[name].get("environment") or []
            self.assertIn("ENV=${ENV:-development}", environment)
            self.assertIn(f"BASE2_PROCESS_ROLE={role}", environment)
            self.assertIn("DB_SSLMODE=${DB_SSLMODE:-disable}", environment)
            self.assertIn("DB_SSLROOTCERT=${DB_SSLROOTCERT:-/run/secrets/db-ca.pem}", environment)
            self.assertIn("DB_HOST=${DB_HOST:-postgres}", environment)
            volumes = SERVICES[name].get("volumes") or []
            self.assertIn("${DB_SSLROOTCERT_HOST:-/dev/null}:/run/secrets/db-ca.pem:ro", volumes)

    def test_traefik_image_has_ping_health_contract(self):
        dockerfile = (ROOT / "traefik/Dockerfile").read_text(encoding="utf-8")
        self.assertIn("HEALTHCHECK", dockerfile)
        self.assertIn("/ping", dockerfile)
        self.assertIn("apk add --no-cache su-exec gettext wget", dockerfile)

    def test_remote_verification_fails_hard_on_required_worker_or_health_failure(self):
        deploy = (ROOT / "digital_ocean/scripts/powershell/deploy.ps1").read_text(encoding="utf-8")
        required = (
            "celery-worker",
            "celery-content-worker",
            "celery-data-rights-worker",
            "celery-email-worker",
            "celery-beat",
        )
        build_line = next(line for line in deploy.splitlines() if "build celery-worker" in line)
        up_line = next(
            line
            for line in deploy.splitlines()
            if "celery-up.txt" in line and "up -d --build" in line
        )
        for service in required:
            self.assertIn(service, build_line)
            self.assertIn(service, up_line)
        self.assertNotIn("|| true", build_line)
        self.assertNotIn("|| true", up_line)
        deployment = deploy[
            deploy.index("# Only the broker may start") : deploy.index(
                "# Django deploy checks"
            )
        ]
        for line in deployment.splitlines():
            if "docker compose" in line and (" build " in line or " up " in line):
                self.assertNotIn("|| true", line)
        core_up = next(line for line in deployment.splitlines() if "compose-up-core.txt" in line)
        self.assertIn(" redis ", f" {core_up} ")
        self.assertIn("--no-deps", core_up)
        self.assertNotIn(" postgres ", f" {core_up} ")
        self.assertNotIn("celery-worker", core_up)
        role_offset = deployment.index("workspace-role-bootstrap.txt")
        api_migration_offset = deployment.index("api-migrate.txt")
        django_migration_offset = deployment.index("django-migrate.txt")
        request_start_offset = deployment.index("compose-up-after-migrations.txt")
        self.assertLess(role_offset, api_migration_offset)
        self.assertLess(api_migration_offset, django_migration_offset)
        self.assertLess(django_migration_offset, request_start_offset)
        build_offset = deploy.index(build_line)
        self.assertNotIn("RUN_CELERY_CHECK", deploy[build_offset - 500 : build_offset])
        self.assertNotIn(
            "manage.py migrate --noinput > /root/logs/django-migrate.txt 2>&1 || true", deploy
        )
        self.assertIn('if [ "$SCHEMA_STATUS" != "0" ]; then', deploy)
        self.assertIn('if [ "$READY" != "1" ]; then', deploy)
        self.assertIn("FAILED: required services did not become healthy", deploy)
        self.assertIn("DEPLOY_EXPECTED_COMMIT", deploy)
        self.assertIn('git reset --hard "$EXPECTED_COMMIT"', deploy)
        self.assertGreaterEqual(
            deploy.count('test "$(git rev-parse HEAD)" = "$EXPECTED_COMMIT"'), 2
        )
        self.assertIn("$script:ExitCode = 1", deploy[deploy.index("if (-not $resolvedIp)") :])
        rollback = deploy[
            deploy.index("trap 'code=$?;") : deploy.index("'@", deploy.index("trap 'code=$?;"))
        ]
        self.assertNotIn('git reset --hard "$PREV" || true', rollback)
        self.assertNotIn("rollback-compose-up.txt 2>&1 || true", rollback)
        self.assertIn("rollback-failed.txt", rollback)

    def test_e2e_compose_keeps_data_rights_queue_and_identity_separate(self):
        e2e = yaml.safe_load((ROOT / "e2e/docker-compose.e2e.yml").read_text(encoding="utf-8"))[
            "services"
        ]
        runtime = e2e["celery-worker"]
        data_rights = e2e["celery-data-rights-worker"]
        self.assertEqual("runtime-worker", runtime["environment"]["BASE2_PROCESS_ROLE"])
        self.assertIn("-Q runtime", " ".join(runtime["command"]))
        self.assertNotIn("DATA_RIGHTS_WORKER_DB_PASSWORD", runtime["environment"])
        self.assertEqual("data-rights-worker", data_rights["environment"]["BASE2_PROCESS_ROLE"])
        self.assertIn("-Q data-rights", " ".join(data_rights["command"]))
        self.assertEqual("base2_data_rights_worker_e2e", data_rights["environment"]["DB_USER"])

    def test_compose_database_endpoint_and_bootstrap_tls_are_configurable(self):
        for name in (
            "api",
            "django",
            "celery-worker",
            "celery-content-worker",
            "celery-data-rights-worker",
            "celery-email-worker",
            "celery-beat",
        ):
            environment = SERVICES[name].get("environment") or []
            self.assertIn("DB_HOST=${DB_HOST:-postgres}", environment)
            self.assertIn("DB_PORT=${DB_PORT:-5432}", environment)
        bootstrap = SERVICES["workspace-db-role"]
        self.assertIn("PGSSLMODE=${DB_SSLMODE:-disable}", bootstrap["environment"])
        self.assertIn(
            "${DB_SSLROOTCERT_HOST:-/dev/null}:/run/secrets/db-ca.pem:ro",
            bootstrap["volumes"],
        )

    def test_compose_observer_is_isolated_staging_only_and_self_cleaning(self):
        observer = (ROOT / "scripts/bash/observe-compose-health.sh").read_text(encoding="utf-8")
        self.assertIn('PROJECT_NAME="base2-f093-$$"', observer)
        self.assertIn("handle_signal 130", observer)
        self.assertIn("handle_signal 143", observer)
        self.assertIn("down -v --remove-orphans", observer)
        self.assertIn("acme-staging.json", observer)
        self.assertIn("acme-staging-v02.api.letsencrypt.org", observer)
        self.assertIn("/tmp/traefik.yml", observer)
        self.assertNotIn("acme-v02.api.letsencrypt.org", observer)


if __name__ == "__main__":
    unittest.main()
