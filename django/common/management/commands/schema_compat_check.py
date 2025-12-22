import json
from typing import Any

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from django.db.migrations.executor import MigrationExecutor


class Command(BaseCommand):
    help = "Checks DB schema compatibility after migrations (tables exist; no unapplied migrations)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--database",
            default="default",
            help="Database connection name (default: default)",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Output machine-readable JSON.",
        )
        parser.add_argument(
            "--skip-columns",
            action="store_true",
            help="Skip per-column checks (table presence only).",
        )

    def handle(self, *args: Any, **options: Any):
        database = options["database"]
        json_mode = bool(options["json"])
        skip_columns = bool(options["skip_columns"])

        conn = connections[database]

        try:
            conn.ensure_connection()
        except Exception as e:
            raise CommandError(f"db_connection_failed: {e.__class__.__name__}: {e}")

        # 1) Migration drift check: if Django thinks there are unapplied migrations, fail.
        unapplied = []
        try:
            executor = MigrationExecutor(conn)
            plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
            unapplied = [f"{m.app_label}.{m.name}" for (m, _backwards) in plan]
        except Exception as e:
            raise CommandError(f"migration_executor_failed: {e.__class__.__name__}: {e}")

        # 2) Table (and optional column) checks
        try:
            existing_tables = set(conn.introspection.table_names())
        except Exception as e:
            raise CommandError(f"introspection_failed: {e.__class__.__name__}: {e}")

        missing_tables: list[str] = []
        missing_columns: dict[str, list[str]] = {}

        for model in apps.get_models(include_auto_created=True):
            table = model._meta.db_table
            if table not in existing_tables:
                missing_tables.append(table)
                continue

            if skip_columns:
                continue

            try:
                desc = conn.introspection.get_table_description(conn.cursor(), table)
                present_cols = {c.name for c in desc}
            except Exception:
                # If introspection is limited for some table, don't hard-fail columns.
                continue

            expected_cols = []
            for field in model._meta.local_concrete_fields:
                col = getattr(field, "column", None)
                if col:
                    expected_cols.append(col)

            missing = [c for c in expected_cols if c not in present_cols]
            if missing:
                missing_columns[table] = missing

        ok = (len(unapplied) == 0) and (len(missing_tables) == 0) and (len(missing_columns) == 0)

        payload = {
            "ok": ok,
            "database": database,
            "unapplied_migrations": unapplied,
            "missing_tables": sorted(set(missing_tables)),
            "missing_columns": missing_columns,
            "counts": {
                "unapplied_migrations": len(unapplied),
                "missing_tables": len(set(missing_tables)),
                "tables_with_missing_columns": len(missing_columns),
            },
        }

        if json_mode:
            self.stdout.write(json.dumps(payload, indent=2, sort_keys=True))
        else:
            if ok:
                self.stdout.write("schema_compat_check: OK")
                return
            self.stdout.write("schema_compat_check: FAIL")
            if unapplied:
                self.stdout.write("Unapplied migrations:")
                for m in unapplied:
                    self.stdout.write(f"  - {m}")
            if missing_tables:
                self.stdout.write("Missing tables:")
                for t in sorted(set(missing_tables)):
                    self.stdout.write(f"  - {t}")
            if missing_columns:
                self.stdout.write("Missing columns:")
                for t, cols in missing_columns.items():
                    self.stdout.write(f"  - {t}: {', '.join(cols)}")

        if not ok:
            raise CommandError("schema_incompatible")
