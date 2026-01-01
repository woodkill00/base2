import json
from typing import Any

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from django.db.migrations.executor import MigrationExecutor


class Command(BaseCommand):
    help = (
        "Checks DB schema compatibility after migrations "
        "(tables exist; no unapplied migrations)."
    )

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

    def _ensure_connection(self, conn) -> None:
        try:
            conn.ensure_connection()
        except Exception as e:
            raise CommandError(
                f"db_connection_failed: {e.__class__.__name__}: {e}"
            ) from e

    def _get_unapplied(self, conn) -> list[str]:
        try:
            executor = MigrationExecutor(conn)
            plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
            return [f"{m.app_label}.{m.name}" for (m, _backwards) in plan]
        except Exception as e:
            raise CommandError(
                f"migration_executor_failed: {e.__class__.__name__}: {e}"
            ) from e

    def _get_existing_tables(self, conn) -> set[str]:
        try:
            return set(conn.introspection.table_names())
        except Exception as e:
            raise CommandError(
                f"introspection_failed: {e.__class__.__name__}: {e}"
            ) from e

    def _missing_columns_for_model(self, conn, model) -> list[str]:
        table = model._meta.db_table
        try:
            desc = conn.introspection.get_table_description(conn.cursor(), table)
            present_cols = {c.name for c in desc}
        except Exception:
            return []

        expected_cols: list[str] = []
        for f in model._meta.local_concrete_fields:
            c = getattr(f, "column", None)
            if isinstance(c, str):
                expected_cols.append(c)
        return [c for c in expected_cols if c not in present_cols]

    def _collect_missing(
        self, conn, existing_tables: set[str], *, skip_columns: bool
    ) -> tuple[list[str], dict[str, list[str]]]:
        missing_tables: list[str] = []
        missing_columns: dict[str, list[str]] = {}
        for model in apps.get_models(include_auto_created=True):
            table = model._meta.db_table
            if table not in existing_tables:
                missing_tables.append(table)
                continue
            if skip_columns:
                continue
            missing = self._missing_columns_for_model(conn, model)
            if missing:
                missing_columns[table] = missing
        return missing_tables, missing_columns

    def _print_report(self, *, payload: dict, json_mode: bool) -> None:
        if json_mode:
            self.stdout.write(json.dumps(payload, indent=2, sort_keys=True))
            return
        if payload["ok"]:
            self.stdout.write("schema_compat_check: OK")
            return
        self.stdout.write("schema_compat_check: FAIL")
        if payload["unapplied_migrations"]:
            self.stdout.write("Unapplied migrations:")
            for m in payload["unapplied_migrations"]:
                self.stdout.write(f"  - {m}")
        if payload["missing_tables"]:
            self.stdout.write("Missing tables:")
            for t in payload["missing_tables"]:
                self.stdout.write(f"  - {t}")
        if payload["missing_columns"]:
            self.stdout.write("Missing columns:")
            for t, cols in payload["missing_columns"].items():
                self.stdout.write(f"  - {t}: {', '.join(cols)}")

    def handle(self, *args: Any, **options: Any):
        database = options["database"]
        json_mode = bool(options["json"])
        skip_columns = bool(options["skip_columns"])

        conn = connections[database]
        self._ensure_connection(conn)

        # 1) Migration drift check: if Django thinks there are unapplied migrations, fail.
        unapplied = []
        unapplied = self._get_unapplied(conn)

        # 2) Table (and optional column) checks
        existing_tables = self._get_existing_tables(conn)

        missing_tables, missing_columns = self._collect_missing(
            conn, existing_tables, skip_columns=skip_columns
        )

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

        self._print_report(payload=payload, json_mode=json_mode)

        if not ok:
            raise CommandError("schema_incompatible")
