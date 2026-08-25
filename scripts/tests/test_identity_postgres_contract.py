import unittest
from pathlib import Path


class IdentityPostgresContractTests(unittest.TestCase):
    def test_api_and_django_migrations_protect_audit_rows(self):
        root = Path(__file__).parents[2]
        api_sql = (root / 'api/migrations/sql/007_protect_audit_events.sql').read_text()
        django_sql = (
            root / 'django/api_schema/migrations/0004_protect_api_audit_events.py'
        ).read_text()
        for marker in ('BEFORE UPDATE OR DELETE', 'api_auth_audit_events_append_only', '55000'):
            self.assertIn(marker, api_sql)
            self.assertIn(marker, django_sql)
        runner = (root / 'api/migrations/runner.py').read_text()
        self.assertIn("'007_protect_audit_events'", runner)


if __name__ == '__main__':
    unittest.main()
