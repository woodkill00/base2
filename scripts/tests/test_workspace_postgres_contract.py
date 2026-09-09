from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class WorkspacePostgresContractTests(unittest.TestCase):
    def _bootstrap_environment(self) -> dict[str, str]:
        environment = os.environ.copy()
        environment.update(
            {
                "POSTGRES_USER": "base2_owner",
                "POSTGRES_PASSWORD": "owner_password_distinct_0001",
                "POSTGRES_DB": "base2",
                "WORKSPACE_DB_USER": "workspace_runtime",
                "WORKSPACE_DB_PASSWORD": "workspace_password_distinct_02",
                "WORKSPACE_WORKER_DB_USER": "workspace_worker",
                "WORKSPACE_WORKER_DB_PASSWORD": "workspace_worker_distinct_03",
                "RUNTIME_WORKER_DB_USER": "runtime_worker",
                "RUNTIME_WORKER_DB_PASSWORD": "runtime_worker_distinct_0004",
                "API_RUNTIME_DB_USER": "api_runtime",
                "API_RUNTIME_DB_PASSWORD": "api_runtime_distinct_000005",
                "DATA_RIGHTS_WORKER_DB_USER": "data_rights_worker",
                "DATA_RIGHTS_WORKER_DB_PASSWORD": "data_rights_distinct_00006",
                "EMAIL_WORKER_DB_USER": "email_worker",
                "EMAIL_WORKER_DB_PASSWORD": "email_worker_distinct_000007",
            }
        )
        return environment

    def _run_bootstrap(
        self, environment: dict[str, str]
    ) -> tuple[subprocess.CompletedProcess[str], bool]:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            marker = root / "psql-invoked"
            psql = root / "psql"
            psql.write_text('#!/bin/sh\ntouch "$PSQL_MARKER"\ncat >/dev/null\n', encoding="utf-8")
            psql.chmod(0o755)
            environment = environment | {
                "PATH": f"{root}:{environment.get('PATH', '')}",
                "PSQL_MARKER": str(marker),
            }
            result = subprocess.run(
                ["/bin/sh", str(ROOT / "postgres/bootstrap-workspace-role.sh")],
                cwd=ROOT,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            return result, marker.exists()

    def test_bootstrap_rejects_every_role_collision_before_psql(self):
        role_names = (
            "POSTGRES_USER",
            "WORKSPACE_DB_USER",
            "WORKSPACE_WORKER_DB_USER",
            "RUNTIME_WORKER_DB_USER",
            "API_RUNTIME_DB_USER",
            "DATA_RIGHTS_WORKER_DB_USER",
            "EMAIL_WORKER_DB_USER",
        )
        for left_index, left in enumerate(role_names):
            for right in role_names[left_index + 1 :]:
                with self.subTest(left=left, right=right):
                    environment = self._bootstrap_environment()
                    environment[right] = environment[left]
                    result, psql_invoked = self._run_bootstrap(environment)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("database_role_collision", result.stderr)
                    self.assertFalse(psql_invoked)

    def test_bootstrap_rejects_every_password_collision_before_psql(self):
        password_names = (
            "POSTGRES_PASSWORD",
            "WORKSPACE_DB_PASSWORD",
            "WORKSPACE_WORKER_DB_PASSWORD",
            "RUNTIME_WORKER_DB_PASSWORD",
            "API_RUNTIME_DB_PASSWORD",
            "DATA_RIGHTS_WORKER_DB_PASSWORD",
            "EMAIL_WORKER_DB_PASSWORD",
        )
        for left_index, left in enumerate(password_names):
            for right in password_names[left_index + 1 :]:
                with self.subTest(left=left, right=right):
                    environment = self._bootstrap_environment()
                    environment[right] = environment[left]
                    result, psql_invoked = self._run_bootstrap(environment)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("database_password_collision", result.stderr)
                    self.assertFalse(psql_invoked)

    def test_bootstrap_valid_identity_set_reaches_psql(self):
        result, psql_invoked = self._run_bootstrap(self._bootstrap_environment())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(psql_invoked)

    def test_bootstrap_and_compose_keep_the_role_private_and_bounded(self):
        bootstrap = (ROOT / "postgres/bootstrap-workspace-role.sh").read_text()
        self.assertIn("NOBYPASSRLS", bootstrap)
        self.assertIn("NOSUPERUSER", bootstrap)
        self.assertIn("NOCREATEROLE", bootstrap)
        self.assertIn("WORKSPACE_WORKER_DB_USER", bootstrap)
        self.assertIn("RUNTIME_WORKER_DB_USER", bootstrap)
        self.assertIn("EMAIL_WORKER_DB_USER", bootstrap)
        self.assertNotIn('echo "$WORKSPACE_DB_PASSWORD', bootstrap)
        for compose_name in ("local.docker.yml", "development.docker.yml"):
            compose = (ROOT / compose_name).read_text()
            self.assertIn("workspace-db-role:", compose)
            self.assertIn("condition: service_completed_successfully", compose)
            self.assertIn("WORKSPACE_DB_PASSWORD=${WORKSPACE_DB_PASSWORD}", compose)
            self.assertIn("WORKSPACE_WORKER_DB_PASSWORD=${WORKSPACE_WORKER_DB_PASSWORD}", compose)
            self.assertIn("RUNTIME_WORKER_DB_PASSWORD=${RUNTIME_WORKER_DB_PASSWORD}", compose)
            self.assertIn("EMAIL_WORKER_DB_PASSWORD=${EMAIL_WORKER_DB_PASSWORD}", compose)
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
        self.assertIn("  api-migrate:", compose)
        self.assertIn("entrypoint: ['python', '-m', 'api.scripts.migrate']", compose)
        self.assertIn(
            "../postgres/bootstrap-workspace-role.sh:/bootstrap-workspace-role.sh:ro", compose
        )
        self.assertIn(
            "workspace-db-role:\n        condition: service_completed_successfully", compose
        )
        django_migrate = compose[
            compose.index("  django-migrate:") : compose.index("  api:")
        ]
        self.assertIn(
            "api-migrate:\n        condition: service_completed_successfully",
            django_migrate,
        )
        self.assertIn("WORKSPACE_DB_USER: base2_workspace_runtime_e2e", compose)
        self.assertIn("WORKSPACE_WORKER_DB_USER: base2_workspace_worker_e2e", compose)
        self.assertIn("RUNTIME_WORKER_DB_USER: base2_runtime_worker_e2e", compose)
        self.assertIn("EMAIL_WORKER_DB_USER: base2_email_worker_e2e", compose)
        self.assertIn("WORKSPACE_DB_PASSWORD: e2e_workspace_runtime_password", compose)
        self.assertIn("WORKSPACE_WORKER_DB_PASSWORD: e2e_workspace_worker_password", compose)
        self.assertIn("RUNTIME_WORKER_DB_PASSWORD: e2e_runtime_worker_password", compose)
        self.assertIn("EMAIL_WORKER_DB_PASSWORD: e2e_email_worker_password", compose)
        role_block = compose[
            compose.index("  workspace-db-role:") : compose.index("  api-migrate:")
        ]
        self.assertNotIn("ports:", role_block)
        self.assertIn("read_only: true", role_block)
        self.assertIn("cap_drop: [ALL]", role_block)
        api_migrate_block = compose[
            compose.index("  api-migrate:") : compose.index("  django-migrate:")
        ]
        self.assertNotIn("ports:", api_migrate_block)
        self.assertIn("DB_USER: e2e", api_migrate_block)
        self.assertIn("read_only: true", api_migrate_block)
        self.assertIn("cap_drop: [ALL]", api_migrate_block)
        support_block = compose[
            compose.index("  test-support:") : compose.index("  celery-worker:")
        ]
        self.assertIn("DB_USER: base2_email_worker_e2e", support_block)
        self.assertIn("api.test_support_main:app", support_block)
        self.assertIn("127.0.0.1:${E2E_TEST_SUPPORT_PORT:-5002}:5002", support_block)
        self.assertNotIn("base2_api_runtime_e2e", support_block)
        self.assertIn("read_only: true", support_block)

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
            "operations_cross_tenant_insert_was_not_blocked",
            "operations_cross_tenant_link_was_not_blocked",
            "relforcerowsecurity",
            "sitecontent_operationsservice",
            "quota_cross_tenant_insert_was_not_blocked",
            "quota_reservation_race()",
            "sitecontent_tenantquotareservation",
            "record_probe_batch(",
            'assert recovered == {"samples": 1, "opened": 0, "resolved": 1, "alerts": 0}',
            "runtime_worker_content_read_was_not_blocked",
            "email_worker_content_read_was_not_blocked",
            "email_worker_operations_read_was_not_blocked",
            "email_worker_outbox_insert_was_not_blocked",
            "api_runtime_cross_tenant_org_insert_was_not_blocked",
            "api_runtime_migration_ledger_dml_was_not_blocked",
            "api_runtime_queue_update_was_not_blocked",
            "global_closure_missed_orphaned_subject_tenant",
            "sitecontent_mediavariant",
            "sitecontent_mediaobjectversion",
        ):
            self.assertIn(marker, checks)

        role_checks = (
            ROOT / "scripts/python/run_workspace_role_migration_checks.py"
        ).read_text()
        for marker in (
            "has_schema_privilege",
            "0033_api_schema_readiness",
            "013_add_global_data_rights_operations",
            "if forward:\n                    cursor.execute(\n                        \"SELECT has_function_privilege",
        ):
            self.assertIn(marker, role_checks)

        self.assertIn("run(api_migration", runner)
        self.assertLess(runner.index("run(api_migration"), runner.index("django_migration ="))
        api_reverse = runner.index('django_migration + ["0031", "--noinput"]')
        api_forward = runner.index('django_migration + ["0033", "--noinput"]')
        self.assertLess(api_reverse, runner.index('role_check + ["api-reversed"]'))
        self.assertLess(runner.index('django_migration + ["0032", "--noinput"]'), api_forward)
        self.assertLess(api_forward, runner.index('role_check + ["api-forward"]'))

        self.assertIn('django_migration + ["0009", "--noinput"]', runner)
        self.assertIn('role_check + ["reversed"]', runner)
        self.assertIn('django_migration + ["0010", "--noinput"]', runner)
        self.assertIn('role_check + ["forward"]', runner)
        self.assertIn('django_migration + ["0017", "--noinput"]', runner)
        media_checks = (ROOT / "scripts/python/run_media_postgres_checks.py").read_text()
        for marker in (
            "media_asset_unbound_update_was_not_blocked",
            "media_variant_unbound_update_was_not_blocked",
            "media_asset_cross_tenant_update_was_not_blocked",
            "media_variant_cross_tenant_update_was_not_blocked",
        ):
            self.assertIn(marker, media_checks)


if __name__ == "__main__":
    unittest.main()
