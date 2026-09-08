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
    "sitecontent_workspaceauditevent": "SELECT, UPDATE",
    "sitecontent_mediauploadsession": "SELECT, UPDATE",
    "sitecontent_mediametadatarevision": "SELECT, UPDATE",
    "sitecontent_mediacollection": "SELECT, UPDATE",
    "sitecontent_mediaretentionhold": "SELECT, UPDATE",
    "sitecontent_mediadeliverygrant": "SELECT, UPDATE",
    "sitecontent_mediaauditevent": "SELECT, UPDATE",
    "sitecontent_mediaabusecase": "SELECT, UPDATE",
    "sitecontent_operationsincident": "SELECT, UPDATE",
    "sitecontent_operationsincidentevent": "SELECT, UPDATE",
    "sitecontent_tenantlifecycleevent": "SELECT, UPDATE",
    "sitecontent_durablejob": "SELECT, UPDATE",
    "sitecontent_breakglassgrant": "SELECT, UPDATE",
    "sitecontent_tenantnotification": "SELECT, UPDATE",
}
SPECIAL_WORKSPACE_GRANTS = {"sitecontent_contentrevision": "SELECT, UPDATE"}
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
    runtime_role, quoted_runtime = _role(schema_editor, "RUNTIME_WORKER_DB_USER")
    data_literal = "'" + data_role.replace("'", "''") + "'"
    content_literal = "'" + content_role.replace("'", "''") + "'"
    request_literal = "'" + request_role.replace("'", "''") + "'"
    runtime_literal = "'" + runtime_role.replace("'", "''") + "'"
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
        cursor.execute(
            """CREATE OR REPLACE FUNCTION base2_data_rights_claim_valid(
                   expected_tenant text, expected_user uuid)
               RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER
               SET search_path=pg_catalog,public AS $$
                 SELECT session_user = %s
                   AND EXISTS (
                     SELECT 1 FROM public.api_data_rights_operations rights
                      WHERE rights.id=NULLIF(current_setting(
                              'app.data_rights_operation_id',true),'')::uuid
                        AND rights.claim_token=NULLIF(current_setting(
                              'app.data_rights_claim_token',true),'')::uuid
                        AND rights.tenant_id=expected_tenant
                        AND (expected_user IS NULL OR rights.user_id=expected_user)
                        AND rights.status='running'
                        AND rights.claim_expires_at >= NOW()
                   )
               $$""",
            (data_role,),
        )
        cursor.execute(
            "REVOKE ALL ON FUNCTION base2_data_rights_claim_valid(text,uuid) FROM PUBLIC"
        )
        # The function exposes one boolean and independently requires the exact
        # dedicated session role, operation id, unguessable token, tenant and
        # optional user. Granting execution avoids leaking queue table access to
        # every other role whose RLS policy must invoke the guard.
        cursor.execute(
            "GRANT EXECUTE ON FUNCTION base2_data_rights_claim_valid(text,uuid) TO PUBLIC"
        )
        cursor.execute(f"GRANT USAGE ON SCHEMA public TO {quoted_data}")
        for table, privileges in {
            **IDENTITY_GRANTS,
            **WORKSPACE_GRANTS,
            **SPECIAL_WORKSPACE_GRANTS,
        }.items():
            quoted_table = schema_editor.connection.ops.quote_name(table)
            cursor.execute(f"REVOKE ALL PRIVILEGES ON TABLE {quoted_table} FROM PUBLIC")
            cursor.execute(f"REVOKE ALL PRIVILEGES ON TABLE {quoted_table} FROM {quoted_data}")
            cursor.execute(f"GRANT {privileges} ON TABLE {quoted_table} TO {quoted_data}")
        for table in WORKSPACE_GRANTS:
            if table == "sitecontent_contentfielddefinition":
                continue
            quoted_table = schema_editor.connection.ops.quote_name(table)
            cursor.execute(f"ALTER TABLE {quoted_table} ENABLE ROW LEVEL SECURITY")
            cursor.execute(f"ALTER TABLE {quoted_table} FORCE ROW LEVEL SECURITY")
            cursor.execute(f"DROP POLICY IF EXISTS data_rights_claim_fence ON {quoted_table}")
            cursor.execute(
                f"CREATE POLICY data_rights_claim_fence ON {quoted_table} AS RESTRICTIVE "
                f"USING (current_user<>{data_literal} OR "
                f"base2_data_rights_claim_valid({quoted_table}.site_id,NULL::uuid)) "
                f"WITH CHECK (current_user<>{data_literal} OR "
                f"base2_data_rights_claim_valid({quoted_table}.site_id,NULL::uuid))"
            )
        cursor.execute("ALTER TABLE sitecontent_contentrevision ENABLE ROW LEVEL SECURITY")
        cursor.execute("ALTER TABLE sitecontent_contentrevision FORCE ROW LEVEL SECURITY")
        cursor.execute(
            "DROP POLICY IF EXISTS data_rights_claim_fence ON sitecontent_contentrevision"
        )
        cursor.execute(
            "CREATE POLICY data_rights_claim_fence ON sitecontent_contentrevision AS RESTRICTIVE "
            f"USING (current_user<>{data_literal} OR EXISTS ("
            "SELECT 1 FROM sitecontent_contentrecord content "
            "WHERE content.id=sitecontent_contentrevision.content_id "
            "AND base2_data_rights_claim_valid(content.site_id,NULL::uuid))) WITH CHECK ("
            f"current_user<>{data_literal} OR EXISTS ("
            "SELECT 1 FROM sitecontent_contentrecord content "
            "WHERE content.id=sitecontent_contentrevision.content_id "
            "AND base2_data_rights_claim_valid(content.site_id,NULL::uuid)))"
        )
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
        operation_id = "NULLIF(current_setting('app.data_rights_operation_id', true),'')::uuid"
        claim_token = "NULLIF(current_setting('app.data_rights_claim_token', true),'')::uuid"
        cursor.execute(
            "CREATE POLICY data_rights_operation_worker ON api_data_rights_operations "
            f"USING (current_user={data_literal} AND id={operation_id} AND "
            f"(status='queued' OR (status='running' AND claim_expires_at<NOW()) "
            f"OR claim_token={claim_token})) "
            f"WITH CHECK (current_user={data_literal} AND id={operation_id} AND "
            f"claim_token={claim_token})"
        )
        cursor.execute(f"REVOKE ALL PRIVILEGES ON api_data_rights_operations FROM {quoted_runtime}")
        cursor.execute(
            "GRANT SELECT (id,status,claim_expires_at,retention_until,created_at,tenant_id) "
            f"ON api_data_rights_operations TO {quoted_runtime}"
        )
        cursor.execute("DROP POLICY IF EXISTS data_rights_dispatcher ON api_data_rights_operations")
        cursor.execute(
            "CREATE POLICY data_rights_dispatcher ON api_data_rights_operations FOR SELECT "
            f"USING (current_user={runtime_literal} AND "
            "(status='queued' OR (status='running' AND claim_expires_at < NOW())))"
        )
        for table in USER_TABLES:
            user_column = f"{table}.{'id' if table == 'api_auth_users' else 'user_id'}"
            claim_scope = f"base2_data_rights_claim_valid({tenant},{user_column})"
            predicate = f"current_user={data_literal} AND {claim_scope}"
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
            f"USING ({organization_scope} AND "
            f"base2_data_rights_claim_valid({tenant},NULL::uuid))"
        )
        membership_tenant_scope = (
            "EXISTS (SELECT 1 FROM api_identity_organizations organization "
            f"WHERE organization.id=organization_id AND organization.tenant_id={tenant})"
        )
        membership_scope = f"current_user={data_literal} AND {membership_tenant_scope}"
        membership_scope += (
            f" AND base2_data_rights_claim_valid({tenant},api_identity_memberships.user_id)"
        )
        cursor.execute("DROP POLICY IF EXISTS data_rights_tenant_scope ON api_identity_memberships")
        cursor.execute(
            "CREATE POLICY data_rights_tenant_scope ON api_identity_memberships "
            f"USING ({membership_scope}) WITH CHECK ({membership_scope})"
        )
        credential_scope = (
            f"current_user={data_literal} AND EXISTS ("
            "SELECT 1 FROM api_identity_organizations organization "
            f"WHERE organization.id=organization_id AND organization.tenant_id={tenant}) "
            f"AND base2_data_rights_claim_valid({tenant},api_identity_credentials.user_id)"
        )
        cursor.execute("DROP POLICY IF EXISTS data_rights_tenant_scope ON api_identity_credentials")
        cursor.execute(
            "CREATE POLICY data_rights_tenant_scope ON api_identity_credentials "
            f"USING ({credential_scope}) WITH CHECK ({credential_scope})"
        )
        audit_scope = (
            f"current_user={data_literal} AND "
            f"base2_data_rights_claim_valid({tenant},api_auth_audit_events.user_id)"
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
        cursor.execute(
            """CREATE OR REPLACE FUNCTION base2_expire_data_rights_results()
               RETURNS integer LANGUAGE plpgsql SECURITY DEFINER
               SET search_path=pg_catalog,public AS $$
               DECLARE changed integer;
               BEGIN
                 IF session_user <> %s THEN
                   RAISE EXCEPTION 'data_rights_role_required';
                 END IF;
                 UPDATE public.api_data_rights_operations
                    SET status='expired', request_ciphertext='', result_ciphertext='',
                        receipt_digest='', error_code='retention_expired', updated_at=NOW(),
                        claim_token=NULL, claim_expires_at=NULL
                  WHERE retention_until <= NOW()
                    AND status IN ('queued','running','completed','failed');
                 GET DIAGNOSTICS changed = ROW_COUNT;
                 RETURN changed;
               END $$""",
            (data_role,),
        )
        cursor.execute("REVOKE ALL ON FUNCTION base2_expire_data_rights_results() FROM PUBLIC")
        cursor.execute(
            f"GRANT EXECUTE ON FUNCTION base2_expire_data_rights_results() TO {quoted_data}"
        )
        cursor.execute(
            """CREATE OR REPLACE FUNCTION base2_finalize_data_rights_operation(
                   operation_id uuid, operation_claim_token uuid, terminal_status text,
                   operation_result text, operation_digest text, operation_error text)
               RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER
               SET search_path=pg_catalog,public AS $$
               DECLARE changed integer;
               BEGIN
                 IF session_user <> %s THEN
                   RAISE EXCEPTION 'data_rights_role_required';
                 END IF;
                 IF terminal_status NOT IN ('completed','failed') THEN
                   RAISE EXCEPTION 'data_rights_terminal_status_invalid';
                 END IF;
                 UPDATE public.api_data_rights_operations
                    SET status=terminal_status,
                        result_ciphertext=CASE WHEN terminal_status='completed'
                          THEN operation_result ELSE '' END,
                        receipt_digest=CASE WHEN terminal_status='completed'
                          THEN operation_digest ELSE '' END,
                        error_code=CASE WHEN terminal_status='failed'
                          THEN left(operation_error,80) ELSE '' END,
                        completed_at=CASE WHEN terminal_status='completed'
                          THEN NOW() ELSE completed_at END,
                        updated_at=NOW(), claim_token=NULL, claim_expires_at=NULL
                  WHERE id=operation_id AND status='running'
                    AND claim_token=operation_claim_token;
                 GET DIAGNOSTICS changed = ROW_COUNT;
                 RETURN changed = 1;
               END $$""",
            (data_role,),
        )
        cursor.execute(
            "REVOKE ALL ON FUNCTION base2_finalize_data_rights_operation(uuid,uuid,text,text,text,text) FROM PUBLIC"
        )
        cursor.execute(
            "GRANT EXECUTE ON FUNCTION "
            "base2_finalize_data_rights_operation(uuid,uuid,text,text,text,text) "
            f"TO {quoted_data}"
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
        cursor.execute(
            "DROP FUNCTION IF EXISTS "
            "base2_finalize_data_rights_operation(uuid,uuid,text,text,text,text)"
        )
        cursor.execute("DROP FUNCTION IF EXISTS base2_expire_data_rights_results()")
        for table in {**IDENTITY_GRANTS, **WORKSPACE_GRANTS, **SPECIAL_WORKSPACE_GRANTS}:
            quoted_table = schema_editor.connection.ops.quote_name(table)
            cursor.execute(f"REVOKE ALL PRIVILEGES ON TABLE {quoted_table} FROM {quoted_data}")
            cursor.execute(f"DROP POLICY IF EXISTS data_rights_claim_fence ON {quoted_table}")
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
            cursor.execute(f"DROP POLICY IF EXISTS data_rights_dispatcher ON {table}")
            cursor.execute(f"DROP POLICY IF EXISTS identity_api_access ON {table}")
        cursor.execute("DROP FUNCTION IF EXISTS base2_data_rights_claim_valid(text,uuid)")
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
