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
        local_branch = script[script.index('if [ "$USE_LOCAL_STACK" = true ]'):]
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
        self.assertIn("else\n    $COMPOSE_CMD exec -T", local_branch)

    def test_frontend_native_crash_retry_is_bounded_and_fail_closed(self):
        script = (ROOT / "scripts/bash/test.sh").read_text(encoding="utf-8")
        self.assertEqual(2, script.count("run_frontend_tests\n"))
        self.assertEqual(1, script.count('if [ "$FRONTEND_EXIT_CODE" -eq 139 ]'))
        self.assertIn("a second crash or any ordinary test failure remains a hard failure", script)
        self.assertIn("if [ $BACKEND_EXIT_CODE -eq 0 ] && [ $FRONTEND_EXIT_CODE -eq 0 ]", script)

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
            "celery-worker": ("python", "CELERY_BROKER_URL"),
            "celery-beat": ("python", "CELERY_BROKER_URL"),
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

    def test_privacy_worker_receives_only_its_required_runtime_secrets(self):
        api_environment = SERVICES["api"].get("environment") or []
        worker_environment = SERVICES["celery-worker"].get("environment") or []
        for binding in (
            "TOKEN_PEPPER=${TOKEN_PEPPER}",
            "IDENTITY_ENCRYPTION_KEY=${IDENTITY_ENCRYPTION_KEY}",
        ):
            self.assertIn(binding, api_environment)
            self.assertIn(binding, worker_environment)
        worker_command = " ".join(
            str(part) for part in (SERVICES["celery-worker"].get("command") or [])
        )
        self.assertNotIn("TOKEN_PEPPER", worker_command)
        self.assertNotIn("IDENTITY_ENCRYPTION_KEY", worker_command)

    def test_traefik_image_has_ping_health_contract(self):
        dockerfile = (ROOT / "traefik/Dockerfile").read_text(encoding="utf-8")
        self.assertIn("HEALTHCHECK", dockerfile)
        self.assertIn("/ping", dockerfile)
        self.assertIn("apk add --no-cache su-exec gettext wget", dockerfile)

    def test_compose_observer_is_isolated_staging_only_and_self_cleaning(self):
        observer = (ROOT / "scripts/bash/observe-compose-health.sh").read_text(
            encoding="utf-8"
        )
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
