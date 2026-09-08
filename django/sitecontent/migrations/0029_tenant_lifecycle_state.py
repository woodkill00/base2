from __future__ import annotations

import os
import re
import uuid

import django.core.validators
from django.db import migrations, models

import sitecontent.models

ROLE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,62}$")
STATE_TABLE = "sitecontent_tenantlifecyclestate"
EVENT_TABLE = "sitecontent_tenantlifecycleevent"
TABLES = (STATE_TABLE, EVENT_TABLE)


def _runtime_role(schema_editor):
    value = os.environ.get("WORKSPACE_DB_USER", "").strip()
    if not ROLE.fullmatch(value):
        raise RuntimeError("tenant_lifecycle:workspace_db_user_invalid")
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (value,))
        if not cursor.fetchone():
            raise RuntimeError("tenant_lifecycle:workspace_db_user_missing")
    return value


def install_rls(apps, schema_editor):
    del apps
    if schema_editor.connection.vendor != "postgresql":
        return
    runtime = _runtime_role(schema_editor).replace('"', '""')
    tenant = "site_id = current_setting('app.tenant_id', true)"
    with schema_editor.connection.cursor() as cursor:
        for table in TABLES:
            cursor.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
            cursor.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')
            cursor.execute(
                f'CREATE POLICY "{table}_select" ON "{table}" FOR SELECT USING ({tenant})'
            )
            cursor.execute(
                f'CREATE POLICY "{table}_insert" ON "{table}" FOR INSERT WITH CHECK ({tenant})'
            )
        cursor.execute(
            f'CREATE POLICY "{STATE_TABLE}_update" ON "{STATE_TABLE}" FOR UPDATE '
            f"USING ({tenant}) WITH CHECK ({tenant})"
        )
        cursor.execute(
            f'CREATE POLICY "{STATE_TABLE}_delete" ON "{STATE_TABLE}" FOR DELETE USING ({tenant})'
        )
        cursor.execute(
            f'GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE "{STATE_TABLE}" TO "{runtime}"'
        )
        cursor.execute(f'GRANT SELECT, INSERT ON TABLE "{EVENT_TABLE}" TO "{runtime}"')
        cursor.execute(
            """CREATE FUNCTION sitecontent_reject_tenant_lifecycle_event_mutation()
               RETURNS trigger LANGUAGE plpgsql AS $$
               BEGIN
                 RAISE EXCEPTION 'tenant_lifecycle:event_immutable';
               END;
               $$"""
        )
        cursor.execute(
            f'''CREATE TRIGGER tenant_lifecycle_event_immutable
                  BEFORE UPDATE OR DELETE ON "{EVENT_TABLE}"
                  FOR EACH ROW EXECUTE FUNCTION
                  sitecontent_reject_tenant_lifecycle_event_mutation()'''
        )


def uninstall_rls(apps, schema_editor):
    del apps
    if schema_editor.connection.vendor != "postgresql":
        return
    runtime = _runtime_role(schema_editor).replace('"', '""')
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            f'DROP TRIGGER IF EXISTS tenant_lifecycle_event_immutable ON "{EVENT_TABLE}"'
        )
        cursor.execute(
            "DROP FUNCTION IF EXISTS sitecontent_reject_tenant_lifecycle_event_mutation()"
        )
        for table in reversed(TABLES):
            cursor.execute(
                f'REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLE "{table}" FROM "{runtime}"'
            )
            for action in ("select", "insert", "update", "delete"):
                cursor.execute(f'DROP POLICY IF EXISTS "{table}_{action}" ON "{table}"')
            cursor.execute(f'ALTER TABLE "{table}" NO FORCE ROW LEVEL SECURITY')
            cursor.execute(f'ALTER TABLE "{table}" DISABLE ROW LEVEL SECURITY')


class Migration(migrations.Migration):
    dependencies = [("sitecontent", "0028_worker_runtime_least_privilege")]
    operations = [
        migrations.CreateModel(
            name="TenantLifecycleState",
            fields=[
                (
                    "site_id",
                    models.CharField(
                        db_index=True,
                        max_length=63,
                        validators=[sitecontent.models.site_id_validator],
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                (
                    "state",
                    models.CharField(
                        choices=[
                            ("provisioning", "Provisioning"),
                            ("active", "Active"),
                            ("suspended", "Suspended"),
                            ("archived", "Archived"),
                            ("restoring", "Restoring"),
                            ("deleting", "Deleting"),
                            ("deleted", "Deleted"),
                        ],
                        default="provisioning",
                        max_length=16,
                    ),
                ),
                ("owner_ref", models.CharField(max_length=200)),
                (
                    "configuration",
                    models.JSONField(
                        default=dict, validators=[sitecontent.models.validate_operations_dimensions]
                    ),
                ),
                (
                    "revision",
                    models.PositiveBigIntegerField(
                        default=1, validators=[django.core.validators.MinValueValidator(1)]
                    ),
                ),
                ("last_operation_id", models.UUIDField(default=uuid.uuid4)),
                (
                    "last_receipt_digest",
                    models.CharField(
                        max_length=64, validators=[sitecontent.models.sha256_validator]
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(fields=["state", "updated_at"], name="tenant_lifecycle_state_idx")
                ],
                "constraints": [
                    models.UniqueConstraint(fields=("site_id",), name="tenant_lifecycle_site_uq")
                ],
            },
        ),
        migrations.CreateModel(
            name="TenantLifecycleEvent",
            fields=[
                (
                    "site_id",
                    models.CharField(
                        db_index=True,
                        max_length=63,
                        validators=[sitecontent.models.site_id_validator],
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("operation_id", models.UUIDField()),
                (
                    "operation",
                    models.CharField(
                        max_length=32,
                        validators=[sitecontent.models.operations_identifier_validator],
                    ),
                ),
                ("from_state", models.CharField(max_length=16)),
                ("to_state", models.CharField(max_length=16)),
                ("actor_ref", models.CharField(max_length=200)),
                ("target_owner_ref", models.CharField(blank=True, default="", max_length=200)),
                (
                    "revision",
                    models.PositiveBigIntegerField(
                        validators=[django.core.validators.MinValueValidator(1)]
                    ),
                ),
                (
                    "receipt_digest",
                    models.CharField(
                        max_length=64, validators=[sitecontent.models.sha256_validator]
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(
                        fields=["site_id", "created_at"], name="tenant_lifecycle_event_idx"
                    )
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("site_id", "operation_id"), name="tenant_lifecycle_operation_uq"
                    )
                ],
            },
        ),
        migrations.RunPython(install_rls, uninstall_rls),
    ]
