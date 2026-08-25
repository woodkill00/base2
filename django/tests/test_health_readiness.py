from unittest.mock import patch

from django.test import Client, SimpleTestCase


class HealthReadinessTests(SimpleTestCase):
    def test_internal_health_is_ready_when_database_connects(self):
        with patch("project.views.connections") as connections:
            response = Client().get("/internal/health")
        connections.__getitem__.return_value.ensure_connection.assert_called_once_with()
        self.assertEqual(200, response.status_code)
        self.assertEqual({"ok": True, "service": "django", "db_ok": True}, response.json())

    def test_internal_health_is_unavailable_when_database_fails(self):
        with patch("project.views.connections") as connections:
            connections.__getitem__.return_value.ensure_connection.side_effect = RuntimeError(
                "password=secret-value"
            )
            response = Client().get("/internal/health")
        self.assertEqual(503, response.status_code)
        self.assertEqual({"ok": False, "service": "django", "db_ok": False}, response.json())
        self.assertNotIn("secret-value", response.content.decode("utf-8"))
