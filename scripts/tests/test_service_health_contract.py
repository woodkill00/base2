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

    def test_api_waits_for_every_required_readiness_dependency(self):
        dependencies = SERVICES["api"]["depends_on"]
        self.assertEqual("service_healthy", dependencies["postgres"]["condition"])
        self.assertEqual("service_healthy", dependencies["redis"]["condition"])

    def test_traefik_image_has_ping_health_contract(self):
        dockerfile = (ROOT / "traefik/Dockerfile").read_text(encoding="utf-8")
        self.assertIn("HEALTHCHECK", dockerfile)
        self.assertIn("/ping", dockerfile)
        self.assertIn("apk add --no-cache su-exec gettext wget", dockerfile)


if __name__ == "__main__":
    unittest.main()
