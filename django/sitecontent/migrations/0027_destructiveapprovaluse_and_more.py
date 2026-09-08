import os
import re
import uuid

import django.core.validators
import django.utils.timezone
from django.db import migrations, models

ROLE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,62}$")
TABLE = "sitecontent_destructiveapprovaluse"


def _runtime_role(schema_editor):
    value = os.environ.get("WORKSPACE_DB_USER", "").strip()
    if not ROLE.fullmatch(value):
        raise RuntimeError("runtime:workspace_db_user_invalid")
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (value,))
        if not cursor.fetchone():
            raise RuntimeError("runtime:workspace_db_user_missing")
    return value


def install_rls(apps, schema_editor):
    del apps
    if schema_editor.connection.vendor != "postgresql":
        return
    runtime = _runtime_role(schema_editor).replace('"', '""')
    tenant = "site_id = current_setting('app.tenant_id', true)"
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(f'ALTER TABLE "{TABLE}" ENABLE ROW LEVEL SECURITY')
        cursor.execute(f'ALTER TABLE "{TABLE}" FORCE ROW LEVEL SECURITY')
        cursor.execute(f'CREATE POLICY "{TABLE}_select" ON "{TABLE}" FOR SELECT USING ({tenant})')
        cursor.execute(
            f'CREATE POLICY "{TABLE}_insert" ON "{TABLE}" FOR INSERT WITH CHECK ({tenant})'
        )
        cursor.execute(f'GRANT SELECT, INSERT ON TABLE "{TABLE}" TO "{runtime}"')


def uninstall_rls(apps, schema_editor):
    del apps
    if schema_editor.connection.vendor != "postgresql":
        return
    runtime = _runtime_role(schema_editor).replace('"', '""')
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(f'REVOKE SELECT, INSERT ON TABLE "{TABLE}" FROM "{runtime}"')
        cursor.execute(f'DROP POLICY IF EXISTS "{TABLE}_select" ON "{TABLE}"')
        cursor.execute(f'DROP POLICY IF EXISTS "{TABLE}_insert" ON "{TABLE}"')
        cursor.execute(f'ALTER TABLE "{TABLE}" NO FORCE ROW LEVEL SECURITY')
        cursor.execute(f'ALTER TABLE "{TABLE}" DISABLE ROW LEVEL SECURITY')


class Migration(migrations.Migration):
    dependencies = [
        ("sitecontent", "0026_runtime_delivery_integrity"),
    ]

    operations = [
        migrations.CreateModel(
            name="DestructiveApprovalUse",
            fields=[
                (
                    "site_id",
                    models.CharField(
                        db_index=True,
                        max_length=63,
                        validators=[
                            django.core.validators.RegexValidator(
                                "^[a-z][a-z0-9-]{2,62}$", "Enter a canonical site identifier."
                            )
                        ],
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
                ("nonce", models.CharField(max_length=128)),
                (
                    "approval_digest",
                    models.CharField(
                        max_length=64,
                        validators=[
                            django.core.validators.RegexValidator(
                                "^[a-f0-9]{64}$", "Enter a lowercase SHA-256 digest."
                            )
                        ],
                    ),
                ),
                ("expires_at", models.DateTimeField()),
                ("consumed_at", models.DateTimeField(default=django.utils.timezone.now)),
            ],
        ),
        migrations.AddConstraint(
            model_name="destructiveapprovaluse",
            constraint=models.UniqueConstraint(
                fields=("site_id", "nonce"), name="destructive_approval_nonce_uq"
            ),
        ),
        migrations.AddConstraint(
            model_name="destructiveapprovaluse",
            constraint=models.CheckConstraint(
                condition=models.Q(("expires_at__gt", models.F("consumed_at"))),
                name="destructive_approval_lifetime_ck",
            ),
        ),
        migrations.RunPython(install_rls, uninstall_rls),
    ]
