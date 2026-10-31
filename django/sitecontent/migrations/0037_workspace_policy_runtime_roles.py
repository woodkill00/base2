"""Least-privilege storage grants; application authorization remains mandatory."""

import importlib

from django.db import migrations

REQUEST_GRANTS = {
    "sitecontent_workspacepolicy": "SELECT, INSERT, UPDATE",
    "sitecontent_reviewsubject": "SELECT, INSERT, UPDATE",
    "sitecontent_reviewapproval": "SELECT, INSERT",
    "sitecontent_reviewnotificationintent": "SELECT, INSERT, UPDATE",
    "sitecontent_reviewdigestbatch": "SELECT",
    "sitecontent_reviewnotificationdelivery": "SELECT",
}
WORKER_GRANTS = {
    "sitecontent_workspacepolicy": "SELECT",
    "sitecontent_reviewsubject": "SELECT, INSERT, UPDATE",
    "sitecontent_reviewapproval": "SELECT",
    "sitecontent_reviewnotificationintent": "SELECT, INSERT, UPDATE",
    "sitecontent_reviewdigestbatch": "SELECT, INSERT, UPDATE",
    "sitecontent_reviewnotificationdelivery": "SELECT, INSERT",
}
HEADER = "api_notification_preference_sets"
POLICY_COLUMNS = "site_id,schema_version,version,require_review,public_access"


def roles(editor):
    helper = importlib.import_module("sitecontent.migrations.0034_public_content_runtime_scope")
    return {
        "request": helper.role_name(editor, "WORKSPACE_DB_USER"),
        "worker": helper.role_name(editor, "WORKSPACE_WORKER_DB_USER"),
        "api": helper.role_name(editor, "API_RUNTIME_DB_USER"),
    }


def configure(apps, editor):
    if editor.connection.vendor != "postgresql":
        return
    resolved = roles(editor)
    with editor.connection.cursor() as cursor:
        for table in REQUEST_GRANTS:
            cursor.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
            cursor.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
            for kind, grants in (("request", REQUEST_GRANTS), ("worker", WORKER_GRANTS)):
                role = resolved[kind]
                cursor.execute(f"GRANT {grants[table]} ON {table} TO {role}")
                cursor.execute(
                    f"CREATE POLICY review_{kind}_scope ON {table} TO {role} "
                    "USING (site_id=current_setting('app.tenant_id',true)) "
                    "WITH CHECK (site_id=current_setting('app.tenant_id',true))"
                )
        # Only fields needed by restrictive public-read predicates, not identity/provenance.
        cursor.execute(f"GRANT SELECT ({POLICY_COLUMNS}) ON sitecontent_workspacepolicy TO {resolved['api']}")
        cursor.execute(
            f"CREATE POLICY review_public_policy_read ON sitecontent_workspacepolicy "
            f"FOR SELECT TO {resolved['api']} "
            "USING (site_id=current_setting('app.tenant_id',true))"
        )
        cursor.execute(f"GRANT SELECT, INSERT, UPDATE ON {HEADER} TO {resolved['api']}")
        cursor.execute(f"ALTER TABLE {HEADER} ENABLE ROW LEVEL SECURITY")
        cursor.execute(f"ALTER TABLE {HEADER} FORCE ROW LEVEL SECURITY")
        cursor.execute(
            f"CREATE POLICY review_notification_scope ON {HEADER} TO {resolved['api']} "
            "USING (tenant_id=current_setting('app.tenant_id',true)) "
            "WITH CHECK (tenant_id=current_setting('app.tenant_id',true))"
        )


def reverse(apps, editor):
    if editor.connection.vendor != "postgresql":
        return
    resolved = roles(editor)
    with editor.connection.cursor() as cursor:
        for table in REQUEST_GRANTS:
            for kind, grants in (("request", REQUEST_GRANTS), ("worker", WORKER_GRANTS)):
                cursor.execute(f"DROP POLICY review_{kind}_scope ON {table}")
                cursor.execute(f"REVOKE {grants[table]} ON {table} FROM {resolved[kind]}")
        cursor.execute("DROP POLICY review_public_policy_read ON sitecontent_workspacepolicy")
        cursor.execute(f"REVOKE SELECT ({POLICY_COLUMNS}) ON sitecontent_workspacepolicy FROM {resolved['api']}")
        cursor.execute(f"DROP POLICY review_notification_scope ON {HEADER}")
        cursor.execute(f"REVOKE SELECT, INSERT, UPDATE ON {HEADER} FROM {resolved['api']}")
        # Keep RLS enabled and forced: reversal must not make surviving data permissive.


class Migration(migrations.Migration):
    dependencies = [
        ("sitecontent", "0036_workspace_policy_review_state"),
        ("api_schema", "0006_notification_preference_sets"),
    ]
    operations = [migrations.RunPython(configure, reverse)]
