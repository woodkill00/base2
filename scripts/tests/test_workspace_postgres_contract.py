from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class WorkspacePostgresContractTests(unittest.TestCase):
    def test_bootstrap_and_compose_keep_the_role_private_and_bounded(self):
        bootstrap = (ROOT / "postgres/bootstrap-workspace-role.sh").read_text()
        self.assertIn("NOBYPASSRLS", bootstrap)
        self.assertIn("NOSUPERUSER", bootstrap)
        self.assertIn("NOCREATEROLE", bootstrap)
        self.assertIn("WORKSPACE_WORKER_DB_USER", bootstrap)
        self.assertNotIn('echo "$WORKSPACE_DB_PASSWORD', bootstrap)
        for compose_name in ("local.docker.yml", "development.docker.yml"):
            compose = (ROOT / compose_name).read_text()
            self.assertIn("workspace-db-role:", compose)
            self.assertIn("condition: service_completed_successfully", compose)
            self.assertIn("WORKSPACE_DB_PASSWORD=${WORKSPACE_DB_PASSWORD}", compose)
            self.assertIn("WORKSPACE_WORKER_DB_PASSWORD=${WORKSPACE_WORKER_DB_PASSWORD}", compose)
            role_block = compose[
                compose.rindex("  workspace-db-role:") : compose.index("  # pgAdmin")
            ]
            self.assertNotIn("ports:", role_block)

            api_block = compose[compose.index("  api:") : compose.index("  # Django")]
            self.assertNotIn("WORKSPACE_WORKER_DB_PASSWORD", api_block)

    def test_repository_and_policy_bind_the_dedicated_pool(self):
        repository = (ROOT / "api/repositories/content_workspace.py").read_text()
        database = (ROOT / "api/db.py").read_text()
        policy = json.loads((ROOT / "shared/config/tenant-security.json").read_text())
        self.assertIn("workspace_db_conn as db_conn", repository)
        self.assertIn("WORKSPACE_DB_USER", database)
        self.assertIn("WORKSPACE_DB_PASSWORD", database)
        self.assertIn("WORKSPACE_WORKER_DB_PASSWORD", database)
        worker = (ROOT / "api/services/content_workspace_worker.py").read_text()
        self.assertIn("workspace_worker_db_conn as db_conn", worker)
        self.assertEqual(policy["workspacePostgresqlRls"]["status"], "active")

    def test_e2e_stack_bootstraps_roles_before_migration_and_separates_runtime_users(self):
        compose = (ROOT / "e2e/docker-compose.e2e.yml").read_text()
        self.assertIn("  workspace-db-role:", compose)
        self.assertIn(
            "../postgres/bootstrap-workspace-role.sh:/bootstrap-workspace-role.sh:ro", compose
        )
        self.assertIn(
            "workspace-db-role:\n        condition: service_completed_successfully", compose
        )
        self.assertIn("WORKSPACE_DB_USER: base2_workspace_runtime_e2e", compose)
        self.assertIn("WORKSPACE_WORKER_DB_USER: base2_workspace_worker_e2e", compose)
        self.assertIn("WORKSPACE_DB_PASSWORD: e2e_workspace_runtime_password", compose)
        self.assertIn("WORKSPACE_WORKER_DB_PASSWORD: e2e_workspace_worker_password", compose)
        role_block = compose[
            compose.index("  workspace-db-role:") : compose.index("  django-migrate:")
        ]
        self.assertNotIn("ports:", role_block)
        self.assertIn("read_only: true", role_block)
        self.assertIn("cap_drop: [ALL]", role_block)

    def test_acceptance_is_disposable_synthetic_and_checks_hostile_paths(self):
        runner = (ROOT / "scripts/python/run_workspace_postgres_acceptance.py").read_text()
        checks = (ROOT / "scripts/python/run_workspace_postgres_checks.py").read_text()
        self.assertIn('"--rm"', runner)
        self.assertIn("secrets.token_urlsafe(32)", runner)
        self.assertIn('"docker", "rm", "--force"', runner)
        for marker in (
            "rolbypassrls",
            "cross_tenant_insert_was_not_blocked",
            "same_tenant_composite_uniqueness_not_enforced",
            "sitecontent_type_state_idx",
            "threading.Barrier(2)",
            "sitecontent_savedview",
            "sitecontent_importjob",
            "state='scheduled'",
            "assert sorted(results) == [0, 1]",
        ):
            self.assertIn(marker, checks)

        self.assertIn('django_migration + ["0009", "--noinput"]', runner)
        self.assertIn('role_check + ["reversed"]', runner)
        self.assertIn('django_migration + ["0010", "--noinput"]', runner)
        self.assertIn('role_check + ["forward"]', runner)


if __name__ == "__main__":
    unittest.main()
