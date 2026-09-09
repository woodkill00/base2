from __future__ import annotations

import os
import re

from django.db import migrations


ROLE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,62}$")


def grant_schema_readiness(apps, schema_editor):
    del apps
    if schema_editor.connection.vendor != "postgresql":
        return
    role = os.environ.get("API_RUNTIME_DB_USER", "").strip()
    if not ROLE.fullmatch(role):
        raise RuntimeError("api_runtime:role_invalid")
    quoted = schema_editor.connection.ops.quote_name(role)
    schema_editor.execute(f"GRANT SELECT ON TABLE django_migrations TO {quoted}")


def revoke_schema_readiness(apps, schema_editor):
    del apps
    if schema_editor.connection.vendor != "postgresql":
        return
    role = os.environ.get("API_RUNTIME_DB_USER", "").strip()
    if not ROLE.fullmatch(role):
        raise RuntimeError("api_runtime:role_invalid")
    quoted = schema_editor.connection.ops.quote_name(role)
    schema_editor.execute(f"REVOKE SELECT ON TABLE django_migrations FROM {quoted}")


class Migration(migrations.Migration):
    dependencies = [("sitecontent", "0032_api_runtime_least_privilege")]
    operations = [migrations.RunPython(grant_schema_readiness, revoke_schema_readiness)]
