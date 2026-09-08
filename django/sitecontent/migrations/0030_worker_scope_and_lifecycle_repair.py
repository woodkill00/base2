from __future__ import annotations

import os
import re

from django.db import migrations

ROLE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,62}$")
TENANT_TABLES = (
    "sitecontent_contenttypedefinition",
    "sitecontent_contentrecord",
    "sitecontent_contentrelationship",
    "sitecontent_savedview",
    "sitecontent_assetbinding",
    "sitecontent_importjob",
    "sitecontent_exportjob",
    "sitecontent_workspaceauditevent",
    "sitecontent_mediaasset",
    "sitecontent_mediacollection",
    "sitecontent_mediacollectionmembership",
    "sitecontent_mediajob",
    "sitecontent_mediametadatarevision",
    "sitecontent_mediaobjectversion",
    "sitecontent_mediaretentionhold",
    "sitecontent_mediauploadsession",
)
MEDIA_POLICY_TABLES = {
    "sitecontent_mediaasset",
    "sitecontent_mediacollection",
    "sitecontent_mediacollectionmembership",
    "sitecontent_mediajob",
    "sitecontent_mediametadatarevision",
    "sitecontent_mediaobjectversion",
    "sitecontent_mediaretentionhold",
    "sitecontent_mediauploadsession",
}
DATA_RIGHTS_GRANTS = {
    "sitecontent_tenantlifecyclestate": "SELECT",
    "api_data_rights_operations": "SELECT, UPDATE",
    "api_auth_users": "SELECT, UPDATE",
    "api_identity_memberships": "SELECT, UPDATE, DELETE",
    "api_identity_organizations": "SELECT",
    "api_auth_refresh_tokens": "UPDATE",
    "api_identity_recovery_codes": "DELETE",
    "api_identity_login_challenges": "DELETE",
    "api_identity_authenticators": "DELETE",
    "api_identity_credentials": "UPDATE",
    "api_auth_audit_events": "INSERT",
}


def _content_role(schema_editor) -> tuple[str, str]:
    role = os.environ.get("WORKSPACE_WORKER_DB_USER", "").strip()
    if not ROLE.fullmatch(role):
        raise RuntimeError("runtime:content_worker_role_invalid")
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (role,))
        if not cursor.fetchone():
            raise RuntimeError("runtime:content_worker_role_missing")
    return role, schema_editor.connection.ops.quote_name(role)


def _request_role(schema_editor) -> str:
    role = os.environ.get("WORKSPACE_DB_USER", "").strip()
    if not ROLE.fullmatch(role):
        raise RuntimeError("runtime:workspace_role_invalid")
    return schema_editor.connection.ops.quote_name(role)


def repair_worker_scope_and_lifecycle(apps, schema_editor):
    del apps
    if schema_editor.connection.vendor != "postgresql":
        return
    role, quoted_role = _content_role(schema_editor)
    request_role = _request_role(schema_editor)
    role_literal = "'" + role.replace("'", "''") + "'"
    tenant = "site_id = current_setting('app.tenant_id', true)"
    with schema_editor.connection.cursor() as cursor:
        for table, privileges in DATA_RIGHTS_GRANTS.items():
            quoted_table = schema_editor.connection.ops.quote_name(table)
            cursor.execute(f"REVOKE ALL PRIVILEGES ON TABLE {quoted_table} FROM {quoted_role}")
            cursor.execute(f"GRANT {privileges} ON TABLE {quoted_table} TO {quoted_role}")
        cursor.execute(f"GRANT SELECT ON api_identity_organizations TO {request_role}")
        cursor.execute(f"GRANT SELECT, UPDATE ON api_identity_memberships TO {request_role}")
        cursor.execute(f"GRANT UPDATE ON api_auth_refresh_tokens TO {request_role}")
        for table in TENANT_TABLES:
            quoted_table = schema_editor.connection.ops.quote_name(table)
            cursor.execute(f'DROP POLICY IF EXISTS "{table}_tenant_scope" ON {quoted_table}')
            for suffix in ("select", "insert", "update", "delete"):
                cursor.execute(
                    f'DROP POLICY IF EXISTS "{table}_content_{suffix}" ON {quoted_table}'
                )
            cursor.execute(
                f'CREATE POLICY "{table}_content_select" ON {quoted_table} FOR SELECT '
                f"USING ({tenant} OR current_user = {role_literal})"
            )
            cursor.execute(
                f'CREATE POLICY "{table}_content_insert" ON {quoted_table} FOR INSERT '
                f"WITH CHECK ({tenant})"
            )
            cursor.execute(
                f'CREATE POLICY "{table}_content_update" ON {quoted_table} FOR UPDATE '
                f"USING ({tenant}) WITH CHECK ({tenant})"
            )
            cursor.execute(
                f'CREATE POLICY "{table}_content_delete" ON {quoted_table} FOR DELETE '
                f"USING ({tenant})"
            )
        cursor.execute(
            "DROP POLICY IF EXISTS tenant_lifecycle_content_discovery "
            "ON sitecontent_tenantlifecyclestate"
        )
        cursor.execute(
            "CREATE POLICY tenant_lifecycle_content_discovery "
            "ON sitecontent_tenantlifecyclestate FOR SELECT "
            f"USING (current_user = {role_literal})"
        )
        # Existing installations may contain a lifecycle owner that cannot pass
        # the authorization layer. Prefer an active owner/admin. If none exists,
        # suspend serving and retain an explicit recovery marker.
        cursor.execute(
            """UPDATE sitecontent_tenantlifecyclestate state
                  SET owner_ref=(
                        SELECT membership.user_id::text
                          FROM api_identity_organizations organization
                          JOIN api_identity_memberships membership
                            ON membership.organization_id=organization.id
                         WHERE organization.tenant_id=state.site_id
                           AND membership.status='active'
                           AND membership.role IN ('owner','admin')
                         ORDER BY CASE membership.role WHEN 'owner' THEN 0 ELSE 1 END,
                                  membership.created_at, membership.user_id
                         LIMIT 1
                      ),
                      updated_at=NOW()
                WHERE EXISTS (
                  SELECT 1 FROM api_identity_organizations organization
                  JOIN api_identity_memberships membership
                    ON membership.organization_id=organization.id
                 WHERE organization.tenant_id=state.site_id
                   AND membership.status='active'
                   AND membership.role IN ('owner','admin')
                )
                  AND NOT EXISTS (
                  SELECT 1 FROM api_identity_organizations organization
                  JOIN api_identity_memberships membership
                    ON membership.organization_id=organization.id
                 WHERE organization.tenant_id=state.site_id
                   AND membership.user_id::text=state.owner_ref
                   AND membership.status='active'
                   AND membership.role IN ('owner','admin')
                )"""
        )
        cursor.execute(
            """UPDATE sitecontent_tenantlifecyclestate state
                  SET state='suspended',
                      configuration=configuration || '{"_ownerRecoveryRequired":true}'::jsonb,
                      updated_at=NOW()
                WHERE NOT EXISTS (
                  SELECT 1 FROM api_identity_organizations organization
                  JOIN api_identity_memberships membership
                    ON membership.organization_id=organization.id
                 WHERE organization.tenant_id=state.site_id
                   AND membership.user_id::text=state.owner_ref
                   AND membership.status='active'
                   AND membership.role IN ('owner','admin')
                )"""
        )


def remove_data_rights_grants(apps, schema_editor):
    del apps
    if schema_editor.connection.vendor != "postgresql":
        return
    role, quoted_role = _content_role(schema_editor)
    request_role = _request_role(schema_editor)
    role_literal = "'" + role.replace("'", "''") + "'"
    tenant = "site_id = current_setting('app.tenant_id', true)"
    with schema_editor.connection.cursor() as cursor:
        for table in DATA_RIGHTS_GRANTS:
            quoted_table = schema_editor.connection.ops.quote_name(table)
            cursor.execute(f"REVOKE ALL PRIVILEGES ON TABLE {quoted_table} FROM {quoted_role}")
        cursor.execute(f"REVOKE SELECT ON api_identity_organizations FROM {request_role}")
        cursor.execute(f"REVOKE SELECT, UPDATE ON api_identity_memberships FROM {request_role}")
        cursor.execute(f"REVOKE UPDATE ON api_auth_refresh_tokens FROM {request_role}")
        for table in TENANT_TABLES:
            quoted_table = schema_editor.connection.ops.quote_name(table)
            for suffix in ("select", "insert", "update", "delete"):
                cursor.execute(
                    f'DROP POLICY IF EXISTS "{table}_content_{suffix}" ON {quoted_table}'
                )
            cursor.execute(f'DROP POLICY IF EXISTS "{table}_tenant_scope" ON {quoted_table}')
            if table in MEDIA_POLICY_TABLES:
                for suffix in ("select", "insert", "update", "delete"):
                    cursor.execute(f'DROP POLICY IF EXISTS "{table}_{suffix}" ON {quoted_table}')
                cursor.execute(
                    f'CREATE POLICY "{table}_select" ON {quoted_table} FOR SELECT '
                    f"USING ({tenant} OR current_user={role_literal})"
                )
                cursor.execute(
                    f'CREATE POLICY "{table}_insert" ON {quoted_table} FOR INSERT '
                    f"WITH CHECK ({tenant})"
                )
                cursor.execute(
                    f'CREATE POLICY "{table}_update" ON {quoted_table} FOR UPDATE '
                    f"USING ({tenant}) WITH CHECK ({tenant})"
                )
                cursor.execute(
                    f'CREATE POLICY "{table}_delete" ON {quoted_table} FOR DELETE '
                    f"USING ({tenant})"
                )
            else:
                cursor.execute(
                    f'CREATE POLICY "{table}_tenant_scope" ON {quoted_table} '
                    f"USING ({tenant} OR current_user={role_literal}) "
                    f"WITH CHECK ({tenant} OR current_user={role_literal})"
                )
        cursor.execute(
            "DROP POLICY IF EXISTS tenant_lifecycle_content_discovery "
            "ON sitecontent_tenantlifecyclestate"
        )


class Migration(migrations.Migration):
    dependencies = [
        ("api_schema", "0004_protect_api_audit_events"),
        ("sitecontent", "0029_tenant_lifecycle_state"),
    ]
    operations = [
        migrations.RunPython(repair_worker_scope_and_lifecycle, remove_data_rights_grants),
    ]
