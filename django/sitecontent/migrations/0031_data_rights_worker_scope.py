from __future__ import annotations

import os
import re

from django.db import migrations

ROLE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,62}$")
IDENTITY_GRANTS = {
    "api_data_rights_operations": "SELECT, UPDATE",
    "api_auth_users": "SELECT, UPDATE",
    "api_identity_memberships": "SELECT, UPDATE, DELETE",
    "api_identity_organizations": "SELECT",
    "api_auth_refresh_tokens": "SELECT, UPDATE",
    "api_identity_recovery_codes": "SELECT, DELETE",
    "api_identity_login_challenges": "SELECT, DELETE",
    "api_identity_authenticators": "SELECT, DELETE",
    "api_identity_credentials": "SELECT, UPDATE",
    "api_auth_audit_events": "INSERT",
}
WORKSPACE_GRANTS = {
    "sitecontent_tenantlifecyclestate": "SELECT",
    "sitecontent_contentrecord": "SELECT",
    "sitecontent_workspaceauditevent": "SELECT",
    "sitecontent_contentfielddefinition": "SELECT",
    "sitecontent_savedview": "SELECT, DELETE",
    "sitecontent_mediaasset": "SELECT, UPDATE",
    "sitecontent_importjob": "SELECT, UPDATE",
    "sitecontent_exportjob": "SELECT, UPDATE",
}
USER_TABLES = (
    "api_auth_users",
    "api_auth_refresh_tokens",
    "api_identity_recovery_codes",
    "api_identity_login_challenges",
    "api_identity_authenticators",
)


def _role(schema_editor, variable: str) -> tuple[str, str]:
    role = os.environ.get(variable, "").strip()
    if not ROLE.fullmatch(role):
        raise RuntimeError(f"data_rights:{variable.lower()}_invalid")
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (role,))
        if not cursor.fetchone():
            raise RuntimeError(f"data_rights:{variable.lower()}_missing")
    return role, schema_editor.connection.ops.quote_name(role)


def configure_data_rights_role(apps, schema_editor):
    del apps
    if schema_editor.connection.vendor != "postgresql":
        return
    data_role, quoted_data = _role(schema_editor, "DATA_RIGHTS_WORKER_DB_USER")
    content_role, quoted_content = _role(schema_editor, "WORKSPACE_WORKER_DB_USER")
    request_role, _quoted_request = _role(schema_editor, "WORKSPACE_DB_USER")
    data_literal = "'" + data_role.replace("'", "''") + "'"
    content_literal = "'" + content_role.replace("'", "''") + "'"
    request_literal = "'" + request_role.replace("'", "''") + "'"
    tenant = "current_setting('app.tenant_id', true)"
    membership = (
        "(EXISTS (SELECT 1 FROM api_identity_memberships membership "
        "JOIN api_identity_organizations organization "
        "ON organization.id=membership.organization_id "
        f"WHERE membership.user_id={{user_column}} AND organization.tenant_id={tenant}) "
        "OR EXISTS (SELECT 1 FROM api_data_rights_operations rights "
        f"WHERE rights.user_id={{user_column}} AND rights.tenant_id={tenant} "
        "AND rights.status='running'))"
    )
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("SELECT current_user")
        api_role = str(cursor.fetchone()[0])
        api_literal = "'" + api_role.replace("'", "''") + "'"
        cursor.execute(f"GRANT USAGE ON SCHEMA public TO {quoted_data}")
        for table, privileges in {**IDENTITY_GRANTS, **WORKSPACE_GRANTS}.items():
            quoted_table = schema_editor.connection.ops.quote_name(table)
            cursor.execute(f"REVOKE ALL PRIVILEGES ON TABLE {quoted_table} FROM PUBLIC")
            cursor.execute(f"REVOKE ALL PRIVILEGES ON TABLE {quoted_table} FROM {quoted_data}")
            cursor.execute(f"GRANT {privileges} ON TABLE {quoted_table} TO {quoted_data}")
        for table in IDENTITY_GRANTS:
            quoted_table = schema_editor.connection.ops.quote_name(table)
            cursor.execute(f"REVOKE ALL PRIVILEGES ON TABLE {quoted_table} FROM {quoted_content}")
        quoted_request = schema_editor.connection.ops.quote_name(request_role)
        cursor.execute(f"REVOKE UPDATE ON api_auth_refresh_tokens FROM {quoted_request}")
        # The dedicated role still receives only tenant-scoped rows. Moving broad
        # grants to another login without RLS would merely relocate the breach.
        for table in {
            "api_data_rights_operations",
            *USER_TABLES,
            "api_identity_memberships",
            "api_identity_organizations",
            "api_identity_credentials",
            "api_auth_audit_events",
        }:
            cursor.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
            cursor.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
            cursor.execute(f"DROP POLICY IF EXISTS identity_api_access ON {table}")
            cursor.execute(
                f"CREATE POLICY identity_api_access ON {table} "
                f"USING (current_user={api_literal}) WITH CHECK (current_user={api_literal})"
            )
        cursor.execute(
            "DROP POLICY IF EXISTS data_rights_operation_worker ON api_data_rights_operations"
        )
        cursor.execute(
            "CREATE POLICY data_rights_operation_worker ON api_data_rights_operations "
            f"USING (current_user={data_literal}) WITH CHECK (current_user={data_literal})"
        )
        for table in USER_TABLES:
            user_column = f"{table}.{'id' if table == 'api_auth_users' else 'user_id'}"
            predicate = (
                f"current_user={data_literal} AND " f"{membership.format(user_column=user_column)}"
            )
            cursor.execute(f"DROP POLICY IF EXISTS data_rights_tenant_scope ON {table}")
            cursor.execute(
                f"CREATE POLICY data_rights_tenant_scope ON {table} "
                f"USING ({predicate}) WITH CHECK ({predicate})"
            )
        organization_tenant_scope = f"tenant_id={tenant}"
        organization_scope = f"current_user={data_literal} AND {organization_tenant_scope}"
        cursor.execute(
            "DROP POLICY IF EXISTS data_rights_tenant_scope ON api_identity_organizations"
        )
        cursor.execute(
            "CREATE POLICY data_rights_tenant_scope ON api_identity_organizations FOR SELECT "
            f"USING ({organization_scope})"
        )
        membership_tenant_scope = (
            "EXISTS (SELECT 1 FROM api_identity_organizations organization "
            f"WHERE organization.id=organization_id AND organization.tenant_id={tenant})"
        )
        membership_scope = f"current_user={data_literal} AND {membership_tenant_scope}"
        cursor.execute("DROP POLICY IF EXISTS data_rights_tenant_scope ON api_identity_memberships")
        cursor.execute(
            "CREATE POLICY data_rights_tenant_scope ON api_identity_memberships "
            f"USING ({membership_scope}) WITH CHECK ({membership_scope})"
        )
        credential_scope = (
            f"current_user={data_literal} AND EXISTS ("
            "SELECT 1 FROM api_identity_organizations organization "
            f"WHERE organization.id=organization_id AND organization.tenant_id={tenant})"
        )
        cursor.execute("DROP POLICY IF EXISTS data_rights_tenant_scope ON api_identity_credentials")
        cursor.execute(
            "CREATE POLICY data_rights_tenant_scope ON api_identity_credentials "
            f"USING ({credential_scope}) WITH CHECK ({credential_scope})"
        )
        audit_scope = f"current_user={data_literal} AND " + membership.format(
            user_column="api_auth_audit_events.user_id"
        )
        cursor.execute("DROP POLICY IF EXISTS data_rights_tenant_scope ON api_auth_audit_events")
        cursor.execute(
            "CREATE POLICY data_rights_tenant_scope ON api_auth_audit_events FOR INSERT "
            f"WITH CHECK ({audit_scope})"
        )
        # The request identity needs membership access only for the already-
        # tenant-bound ownership-transfer transaction.
        cursor.execute(
            "DROP POLICY IF EXISTS workspace_transfer_scope ON api_identity_organizations"
        )
        cursor.execute(
            "CREATE POLICY workspace_transfer_scope ON api_identity_organizations FOR SELECT "
            f"USING (current_user={request_literal} AND {organization_tenant_scope})"
        )
        cursor.execute("DROP POLICY IF EXISTS workspace_transfer_scope ON api_identity_memberships")
        cursor.execute(
            "CREATE POLICY workspace_transfer_scope ON api_identity_memberships "
            f"USING (current_user={request_literal} AND {membership_tenant_scope}) "
            f"WITH CHECK (current_user={request_literal} AND {membership_tenant_scope})"
        )
        cursor.execute(
            "DROP POLICY IF EXISTS tenant_lifecycle_content_discovery "
            "ON sitecontent_tenantlifecyclestate"
        )
        cursor.execute(
            "CREATE POLICY tenant_lifecycle_worker_discovery "
            "ON sitecontent_tenantlifecyclestate FOR SELECT "
            f"USING (site_id=current_setting('app.tenant_id', true) "
            f"OR current_user={content_literal} OR current_user={data_literal})"
        )


def remove_data_rights_role(apps, schema_editor):
    del apps
    if schema_editor.connection.vendor != "postgresql":
        return
    _data_role, quoted_data = _role(schema_editor, "DATA_RIGHTS_WORKER_DB_USER")
    content_role, quoted_content = _role(schema_editor, "WORKSPACE_WORKER_DB_USER")
    _request_role, quoted_request = _role(schema_editor, "WORKSPACE_DB_USER")
    content_literal = "'" + content_role.replace("'", "''") + "'"
    with schema_editor.connection.cursor() as cursor:
        for table in {**IDENTITY_GRANTS, **WORKSPACE_GRANTS}:
            quoted_table = schema_editor.connection.ops.quote_name(table)
            cursor.execute(f"REVOKE ALL PRIVILEGES ON TABLE {quoted_table} FROM {quoted_data}")
        for table in {
            "api_data_rights_operations",
            *USER_TABLES,
            "api_identity_memberships",
            "api_identity_organizations",
            "api_identity_credentials",
            "api_auth_audit_events",
        }:
            cursor.execute(f"DROP POLICY IF EXISTS data_rights_operation_worker ON {table}")
            cursor.execute(f"DROP POLICY IF EXISTS data_rights_tenant_scope ON {table}")
            cursor.execute(f"DROP POLICY IF EXISTS identity_api_access ON {table}")
        cursor.execute(
            "DROP POLICY IF EXISTS workspace_transfer_scope ON api_identity_organizations"
        )
        cursor.execute("DROP POLICY IF EXISTS workspace_transfer_scope ON api_identity_memberships")
        for table in {
            "api_data_rights_operations",
            *USER_TABLES,
            "api_identity_memberships",
            "api_identity_organizations",
            "api_identity_credentials",
            "api_auth_audit_events",
        }:
            cursor.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
            cursor.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
        for table, privileges in IDENTITY_GRANTS.items():
            quoted_table = schema_editor.connection.ops.quote_name(table)
            cursor.execute(f"GRANT {privileges} ON TABLE {quoted_table} TO {quoted_content}")
        cursor.execute(f"GRANT UPDATE ON api_auth_refresh_tokens TO {quoted_request}")
        cursor.execute(
            "DROP POLICY IF EXISTS tenant_lifecycle_worker_discovery "
            "ON sitecontent_tenantlifecyclestate"
        )
        cursor.execute(
            "CREATE POLICY tenant_lifecycle_content_discovery "
            "ON sitecontent_tenantlifecyclestate FOR SELECT "
            f"USING (current_user={content_literal})"
        )


class Migration(migrations.Migration):
    dependencies = [
        ("api_schema", "0005_data_rights_claim_fencing"),
        ("sitecontent", "0030_worker_scope_and_lifecycle_repair"),
    ]
    operations = [migrations.RunPython(configure_data_rights_role, remove_data_rights_role)]
