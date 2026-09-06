from __future__ import annotations

import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "django/sitecontent/migrations/0012_universal_media_library_roles.py"
GOVERNANCE_MIGRATION = ROOT / "django/sitecontent/migrations/0013_media_governance.py"
PROCESSING_MIGRATION = ROOT / "django/sitecontent/migrations/0014_media_processing_governance.py"
PORTABILITY_MIGRATION = ROOT / "django/sitecontent/migrations/0015_media_portability_and_abuse.py"
SECURITY_MIGRATION = ROOT / "django/sitecontent/migrations/0016_media_security_boundaries.py"
WORKER_COMPLETION_MIGRATION = (
    ROOT / "django/sitecontent/migrations/0017_media_worker_rls_completion.py"
)


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
        self.assertIn('django_migration + ["0017", "--noinput"]', runner)
        self.assertIn('media_check + ["forward"]', runner)
        self.assertIn('media_check + ["reversed"]', runner)
        self.assertIn("media_cross_tenant_insert_was_not_blocked", checks)
        self.assertIn("relforcerowsecurity", checks)
        self.assertIn("rolbypassrls", checks)
        self.assertIn("docker", runner)

    def test_governance_tables_are_forced_rls_and_reversed_safely(self):
        source = GOVERNANCE_MIGRATION.read_text()
        ast.parse(source)
        for table in (
            "sitecontent_mediaauditevent",
            "sitecontent_mediadeliverygrant",
            "sitecontent_mediaexportpackage",
            "sitecontent_mediaoutboxevent",
            "sitecontent_mediareference",
        ):
            self.assertIn(f'"{table}"', source)
        self.assertIn("FORCE ROW LEVEL SECURITY", source)
        reverse = source.split("def remove_media_governance_roles", 1)[1]
        self.assertLess(reverse.index("DROP POLICY"), reverse.index("DISABLE ROW LEVEL SECURITY"))

    def test_processing_tables_are_forced_rls_and_reversed_safely(self):
        source = PROCESSING_MIGRATION.read_text()
        ast.parse(source)
        for table in (
            "sitecontent_mediainspectionresult",
            "sitecontent_mediapurgeplan",
            "sitecontent_mediauploadpart",
        ):
            self.assertIn(f'"{table}"', source)
        self.assertIn("FORCE ROW LEVEL SECURITY", source)
        reverse = source.split("def remove_media_processing_roles", 1)[1]
        self.assertLess(reverse.index("DROP POLICY"), reverse.index("DISABLE ROW LEVEL SECURITY"))

    def test_portability_tables_are_forced_rls_and_reversed_safely(self):
        source = PORTABILITY_MIGRATION.read_text()
        ast.parse(source)
        for table in (
            "sitecontent_mediaabusecase",
            "sitecontent_mediaencryptionenvelope",
        ):
            self.assertIn(f'"{table}"', source)
        self.assertIn("FORCE ROW LEVEL SECURITY", source)
        reverse = source.split("def remove_media_portability_roles", 1)[1]
        self.assertLess(reverse.index("DROP POLICY"), reverse.index("DISABLE ROW LEVEL SECURITY"))

    def test_security_migration_binds_tenant_relations_and_worker_mutations(self):
        source = SECURITY_MIGRATION.read_text()
        ast.parse(source)
        self.assertIn("media_upload_asset_ref_uq", source)
        self.assertIn("FOREIGN KEY (site_id", source)
        self.assertIn("VALIDATE CONSTRAINT", source)
        self.assertIn("FOR SELECT", source)
        self.assertIn("OR current_user = '{worker}'", source)
        self.assertIn("FOR INSERT", source)
        self.assertIn("WITH CHECK ({tenant})", source)
        self.assertNotIn("WITH CHECK ({tenant} OR current_user", source)

    def test_worker_completion_migration_hardens_assets_and_variants(self):
        source = WORKER_COMPLETION_MIGRATION.read_text()
        ast.parse(source)
        self.assertIn('ASSET_TABLE = "sitecontent_mediaasset"', source)
        self.assertIn('VARIANT_TABLE = "sitecontent_mediavariant"', source)
        self.assertIn("ENABLE ROW LEVEL SECURITY", source)
        self.assertIn("FORCE ROW LEVEL SECURITY", source)
        self.assertIn("FOR SELECT", source)
        self.assertIn("FOR UPDATE", source)
        self.assertIn("WITH CHECK ({tenant_asset})", source)
        self.assertNotIn("WITH CHECK ({tenant_asset} OR", source)

    def test_complete_gate_requires_real_postgres_media_acceptance(self):
        import json

        manifest = json.loads((ROOT / "scripts/config/complete-gate-v1.json").read_text())
        checks = {item["id"]: item for item in manifest["checks"]}
        acceptance = checks["workspace-postgres-acceptance"]
        self.assertTrue(acceptance["required"])
        self.assertEqual(
            acceptance["command"],
            ["python3", "scripts/python/run_workspace_postgres_acceptance.py"],
        )
        self.assertIn("docker", acceptance["requiredTools"])
        self.assertIn(
            "workspace-postgres-acceptance",
            checks["media-library-contract"]["dependsOn"],
        )


if __name__ == "__main__":
    unittest.main()
