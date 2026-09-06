from __future__ import annotations

import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "django/sitecontent/migrations/0012_universal_media_library_roles.py"


class MediaLibraryMigrationTests(unittest.TestCase):
    def test_role_migration_is_parseable_and_covers_every_site_owned_media_table(self):
        source = MIGRATION.read_text()
        ast.parse(source)
        for table in (
            "sitecontent_mediacollection",
            "sitecontent_mediacollectionmembership",
            "sitecontent_mediajob",
            "sitecontent_mediametadatarevision",
            "sitecontent_mediaobjectversion",
            "sitecontent_mediaretentionhold",
            "sitecontent_mediauploadsession",
        ):
            self.assertIn(f'"{table}"', source)

    def test_migration_forces_rls_and_scopes_runtime_while_admitting_fixed_worker(self):
        source = MIGRATION.read_text()
        self.assertIn("ENABLE ROW LEVEL SECURITY", source)
        self.assertIn("FORCE ROW LEVEL SECURITY", source)
        self.assertIn("site_id = current_setting('app.tenant_id', true)", source)
        self.assertIn("current_user = {worker_literal}", source)
        self.assertNotIn("BYPASSRLS", source)
        self.assertNotIn("SUPERUSER", source)

    def test_reverse_drops_policy_before_disabling_rls_and_revoking_exact_roles(self):
        source = MIGRATION.read_text()
        reverse = source.split("def remove_media_roles", 1)[1]
        self.assertLess(reverse.index("DROP POLICY"), reverse.index("DISABLE ROW LEVEL SECURITY"))
        self.assertIn("REVOKE ALL PRIVILEGES", reverse)

    def test_disposable_postgres_acceptance_proves_forward_reverse_and_tenant_isolation(self):
        runner = (ROOT / "scripts/python/run_workspace_postgres_acceptance.py").read_text()
        checks = (ROOT / "scripts/python/run_media_postgres_checks.py").read_text()
        self.assertIn('django_migration + ["0012", "--noinput"]', runner)
        self.assertIn('media_check + ["forward"]', runner)
        self.assertIn('media_check + ["reversed"]', runner)
        self.assertIn("media_cross_tenant_insert_was_not_blocked", checks)
        self.assertIn("relforcerowsecurity", checks)
        self.assertIn("rolbypassrls", checks)
        self.assertIn("docker", runner)


if __name__ == "__main__":
    unittest.main()
