from __future__ import annotations

import os
import re

from django.db import migrations

ROLE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,62}$")
IDENTITY_GRANTS = {
    "api_auth_users": "SELECT",
    "api_identity_memberships": "SELECT",
    "api_identity_organizations": "SELECT",
    "api_auth_refresh_tokens": "SELECT",
    "api_identity_recovery_codes": "SELECT",
    "api_identity_login_challenges": "SELECT",
    "api_identity_authenticators": "SELECT",
    "api_identity_credentials": "SELECT",
    "api_auth_audit_events": "SELECT",
}
LEGACY_CONTENT_IDENTITY_GRANTS = {
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
    "sitecontent_contentfielddefinition": "SELECT",
    "sitecontent_savedview": "SELECT",
    "sitecontent_mediaasset": "SELECT",
    "sitecontent_importjob": "SELECT",
    "sitecontent_exportjob": "SELECT",
    "sitecontent_workspaceauditevent": "SELECT",
    "sitecontent_mediauploadsession": "SELECT",
    "sitecontent_mediametadatarevision": "SELECT",
    "sitecontent_mediacollection": "SELECT",
    "sitecontent_mediaretentionhold": "SELECT",
    "sitecontent_mediadeliverygrant": "SELECT",
    "sitecontent_mediaauditevent": "SELECT",
    "sitecontent_mediaabusecase": "SELECT",
    "sitecontent_operationsincident": "SELECT",
    "sitecontent_operationsincidentevent": "SELECT",
    "sitecontent_tenantlifecycleevent": "SELECT",
    "sitecontent_durablejob": "SELECT",
    "sitecontent_breakglassgrant": "SELECT",
    "sitecontent_tenantnotification": "SELECT",
}
SPECIAL_WORKSPACE_GRANTS = {"sitecontent_contentrevision": "SELECT"}
USER_TABLES = (
    "api_auth_users",
    "api_auth_refresh_tokens",
    "api_identity_recovery_codes",
    "api_identity_login_challenges",
    "api_identity_authenticators",
)
WORKSPACE_SUBJECT_COLUMNS = {
    "sitecontent_tenantlifecyclestate": ("owner_ref",),
    "sitecontent_savedview": ("owner_ref",),
    "sitecontent_importjob": ("requester_ref",),
    "sitecontent_exportjob": ("requester_ref",),
    "sitecontent_workspaceauditevent": ("actor_ref",),
    "sitecontent_mediaasset": ("owner_ref",),
    "sitecontent_mediauploadsession": ("actor_ref",),
    "sitecontent_mediametadatarevision": ("actor_ref",),
    "sitecontent_mediacollection": ("owner_ref",),
    "sitecontent_mediaretentionhold": ("owner_ref",),
    "sitecontent_mediadeliverygrant": ("audience_ref",),
    "sitecontent_mediaauditevent": ("actor_ref", "subject_ref"),
    "sitecontent_mediaabusecase": ("reporter_ref", "reviewer_ref", "appellant_ref"),
    "sitecontent_operationsincident": ("owner_ref",),
    "sitecontent_operationsincidentevent": ("actor_ref",),
    "sitecontent_tenantlifecycleevent": ("actor_ref", "target_owner_ref"),
    "sitecontent_durablejob": ("owner_ref",),
    "sitecontent_breakglassgrant": ("requester_ref", "approver_ref"),
    "sitecontent_tenantnotification": ("owner_ref",),
}
WORKSPACE_SUBJECT_TREATMENTS = {
    (table, column): (
        "delete" if (table, column) == ("sitecontent_savedview", "owner_ref")
        else "media_delete" if (table, column) == ("sitecontent_mediaasset", "owner_ref")
        else "pseudonymize"
    )
    for table, columns in WORKSPACE_SUBJECT_COLUMNS.items()
    for column in columns
}
WORKSPACE_SUBJECT_TREATMENTS[("sitecontent_contentrevision", "actor_ref")] = "pseudonymize"


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
    inventory_values = ",".join(
        f"('{table}','{column}','{treatment}')"
        for (table, column), treatment in sorted(WORKSPACE_SUBJECT_TREATMENTS.items())
    )
    tenant = "current_setting('app.tenant_id', true)"
    with schema_editor.connection.cursor() as cursor:
        api_role = os.environ.get("API_RUNTIME_DB_USER", "").strip()
        if not ROLE.fullmatch(api_role):
            raise RuntimeError("api_runtime:role_invalid")
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
        cursor.execute(
            """CREATE OR REPLACE FUNCTION base2_data_rights_subject_id(expected_tenant text)
               RETURNS uuid LANGUAGE sql STABLE SECURITY DEFINER
               SET search_path=pg_catalog,public AS $$
                 SELECT rights.user_id FROM public.api_data_rights_operations rights
                  WHERE session_user=%s
                    AND rights.id=NULLIF(current_setting(
                      'app.data_rights_operation_id',true),'')::uuid
                    AND rights.claim_token=NULLIF(current_setting(
                      'app.data_rights_claim_token',true),'')::uuid
                    AND rights.tenant_id=expected_tenant AND rights.status='running'
                    AND rights.claim_expires_at>=NOW() AND rights.retention_until>NOW()
               $$""",
            (data_role,),
        )
        cursor.execute("REVOKE ALL ON FUNCTION base2_data_rights_subject_id(text) FROM PUBLIC")
        cursor.execute("GRANT EXECUTE ON FUNCTION base2_data_rights_subject_id(text) TO PUBLIC")
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
            if table == "sitecontent_contentrecord":
                subject_predicate = (
                    "EXISTS (SELECT 1 FROM sitecontent_workspaceauditevent subject_audit "
                    f"WHERE subject_audit.site_id={quoted_table}.site_id "
                    "AND subject_audit.object_type='content_record' "
                    f"AND subject_audit.object_ref={quoted_table}.id::text "
                    "AND subject_audit.action='content.create' "
                    f"AND subject_audit.actor_ref=base2_data_rights_subject_id({quoted_table}.site_id)::text)"
                )
            else:
                columns = WORKSPACE_SUBJECT_COLUMNS.get(table, ())
                subject_predicate = " OR ".join(
                    f"{quoted_table}.{column}=base2_data_rights_subject_id({quoted_table}.site_id)::text"
                    for column in columns
                ) or "FALSE"
            cursor.execute(
                f"CREATE POLICY data_rights_claim_fence ON {quoted_table} AS RESTRICTIVE "
                f"USING (current_user<>{data_literal} OR "
                f"({subject_predicate})) "
                f"WITH CHECK (current_user<>{data_literal} OR "
                f"({subject_predicate}))"
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
            "AND sitecontent_contentrevision.actor_ref="
            "base2_data_rights_subject_id(content.site_id)::text)) WITH CHECK ("
            f"current_user<>{data_literal} OR EXISTS ("
            "SELECT 1 FROM sitecontent_contentrecord content "
            "WHERE content.id=sitecontent_contentrevision.content_id "
            "AND sitecontent_contentrevision.actor_ref="
            "base2_data_rights_subject_id(content.site_id)::text))"
        )
        for table in IDENTITY_GRANTS:
            quoted_table = schema_editor.connection.ops.quote_name(table)
            cursor.execute(f"REVOKE ALL PRIVILEGES ON TABLE {quoted_table} FROM {quoted_content}")
        cursor.execute(
            f"REVOKE ALL PRIVILEGES ON TABLE api_data_rights_operations FROM {quoted_content}"
        )
        cursor.execute(
            f"REVOKE ALL PRIVILEGES ON TABLE api_data_rights_operations FROM {quoted_data}"
        )
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
            f"status='running' AND claim_expires_at>=NOW() AND claim_token={claim_token}) "
            f"WITH CHECK (current_user={data_literal} AND id={operation_id} AND "
            f"claim_token={claim_token})"
        )
        cursor.execute(f"REVOKE ALL PRIVILEGES ON api_data_rights_operations FROM {quoted_runtime}")
        cursor.execute("DROP POLICY IF EXISTS data_rights_dispatcher ON api_data_rights_operations")
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
            "CREATE POLICY data_rights_tenant_scope ON api_auth_audit_events FOR SELECT "
            f"USING ({audit_scope})"
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
            "ALTER TABLE api_data_rights_operations ADD COLUMN IF NOT EXISTS dispatch_token uuid NULL"
        )
        cursor.execute(
            "ALTER TABLE api_data_rights_operations ADD COLUMN IF NOT EXISTS dispatch_expires_at timestamptz NULL"
        )
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS sitecontent_subjectdataregistry (
                 version integer NOT NULL, table_name text NOT NULL, column_name text NOT NULL,
                 treatment text NOT NULL CHECK (treatment IN ('delete','media_delete','pseudonymize')),
                 PRIMARY KEY(table_name,column_name))"""
        )
        cursor.execute("DELETE FROM sitecontent_subjectdataregistry")
        cursor.execute(
            f"INSERT INTO sitecontent_subjectdataregistry(version,table_name,column_name,treatment) "
            f"SELECT 1,fixed.table_name,fixed.column_name,fixed.treatment FROM (VALUES {inventory_values}) "
            "AS fixed(table_name,column_name,treatment)"
        )
        cursor.execute("REVOKE ALL ON sitecontent_subjectdataregistry FROM PUBLIC")
        cursor.execute(
            "ALTER TABLE api_data_rights_operations DROP CONSTRAINT IF EXISTS api_data_rights_operations_kind_check"
        )
        cursor.execute(
            "ALTER TABLE api_data_rights_operations ADD CONSTRAINT api_data_rights_operations_kind_check "
            "CHECK (kind IN ('export','correction','deactivation','deletion','global_deactivation','global_deletion'))"
        )
        cursor.execute(
            """CREATE OR REPLACE FUNCTION base2_list_due_data_rights_operations(requested_limit integer)
               RETURNS TABLE(id uuid,dispatch_token uuid) LANGUAGE plpgsql SECURITY DEFINER
               SET search_path=pg_catalog,public AS $$
               BEGIN
                 IF session_user <> %s THEN
                   RAISE EXCEPTION 'dispatcher_role_required';
                 END IF;
                 RETURN QUERY
                   WITH due AS (
                     SELECT rights.id FROM public.api_data_rights_operations rights
                      WHERE (rights.status='queued' OR (
                             rights.status='running' AND rights.claim_expires_at < NOW()))
                        AND (rights.dispatch_expires_at IS NULL OR rights.dispatch_expires_at < NOW())
                        AND rights.retention_until > NOW()
                        AND EXISTS (
                          SELECT 1 FROM public.sitecontent_tenantlifecyclestate lifecycle
                           WHERE lifecycle.site_id=rights.tenant_id AND lifecycle.state='active')
                      ORDER BY rights.created_at ASC FOR UPDATE SKIP LOCKED
                      LIMIT greatest(1,least(COALESCE(requested_limit,25),100))
                   )
                   UPDATE public.api_data_rights_operations rights
                      SET status='queued',claim_token=NULL,claim_expires_at=NULL,
                          dispatch_token=gen_random_uuid(),
                          dispatch_expires_at=NOW()+INTERVAL '2 minutes',updated_at=NOW()
                     FROM due WHERE rights.id=due.id
                   RETURNING rights.id,rights.dispatch_token;
               END $$""",
            (runtime_role,),
        )
        cursor.execute(
            "REVOKE ALL ON FUNCTION base2_list_due_data_rights_operations(integer) FROM PUBLIC"
        )
        cursor.execute(
            "GRANT EXECUTE ON FUNCTION base2_list_due_data_rights_operations(integer) "
            f"TO {quoted_runtime}"
        )
        cursor.execute(
            """CREATE OR REPLACE FUNCTION base2_claim_data_rights_operation(
                   requested_id uuid, requested_dispatch_token uuid, requested_claim_token uuid)
               RETURNS TABLE(id uuid,tenant_id text,user_id uuid,kind text,
                             request_ciphertext text,claim_token uuid)
               LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
               BEGIN
                 IF session_user <> %s OR requested_dispatch_token IS NULL OR requested_claim_token IS NULL THEN
                   RAISE EXCEPTION 'data_rights_role_required';
                 END IF;
                 RETURN QUERY
                   UPDATE public.api_data_rights_operations rights
                      SET status='running', started_at=COALESCE(rights.started_at,NOW()),
                          updated_at=NOW(), claim_token=requested_claim_token,
                          claim_expires_at=NOW() + INTERVAL '5 minutes',
                          dispatch_token=NULL,dispatch_expires_at=NULL
                    WHERE rights.id=requested_id
                      AND rights.status='queued'
                      AND rights.dispatch_token=requested_dispatch_token
                      AND rights.dispatch_expires_at >= NOW()
                      AND rights.retention_until > NOW()
                      AND EXISTS (
                        SELECT 1 FROM public.sitecontent_tenantlifecyclestate lifecycle
                         WHERE lifecycle.site_id=rights.tenant_id AND lifecycle.state='active')
                   RETURNING rights.id,rights.tenant_id,rights.user_id,rights.kind,
                             rights.request_ciphertext,rights.claim_token;
               END $$""",
            (data_role,),
        )
        cursor.execute(
            "REVOKE ALL ON FUNCTION base2_claim_data_rights_operation(uuid,uuid,uuid) FROM PUBLIC"
        )
        cursor.execute(
            "GRANT EXECUTE ON FUNCTION base2_claim_data_rights_operation(uuid,uuid,uuid) "
            f"TO {quoted_data}"
        )
        cursor.execute(
            """CREATE OR REPLACE FUNCTION base2_export_data_rights_subject_surfaces()
               RETURNS TABLE(table_name text,column_name text,treatment text,row_data jsonb)
               LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
               DECLARE rights record; item record; operation_id uuid; operation_token uuid;
               BEGIN
                 IF session_user <> %s THEN RAISE EXCEPTION 'data_rights_role_required'; END IF;
                 operation_id := NULLIF(current_setting('app.data_rights_operation_id',true),'')::uuid;
                 operation_token := NULLIF(current_setting('app.data_rights_claim_token',true),'')::uuid;
                 SELECT * INTO rights FROM public.api_data_rights_operations operation
                  WHERE operation.id=operation_id AND operation.claim_token=operation_token
                    AND operation.status='running' AND operation.claim_expires_at>=NOW()
                    AND operation.retention_until>NOW();
                 IF NOT FOUND THEN RAISE EXCEPTION 'data_rights_claim_invalid'; END IF;
                 FOR item IN SELECT * FROM public.sitecontent_subjectdataregistry ORDER BY table_name,column_name LOOP
                   table_name:=item.table_name; column_name:=item.column_name; treatment:=item.treatment;
                   IF item.table_name='sitecontent_contentrevision' THEN
                     RETURN QUERY EXECUTE format(
                       'SELECT $1,$2,$3,to_jsonb(subject_row) FROM public.%%I subject_row JOIN public.sitecontent_contentrecord content ON content.id=subject_row.content_id WHERE content.site_id=$4 AND subject_row.%%I=$5 ORDER BY subject_row.id LIMIT 1001',
                       item.table_name,item.column_name)
                       USING table_name,column_name,treatment,rights.tenant_id,rights.user_id::text;
                   ELSE
                     RETURN QUERY EXECUTE format(
                       'SELECT $1,$2,$3,to_jsonb(subject_row) FROM public.%%I subject_row WHERE site_id=$4 AND %%I=$5 ORDER BY id LIMIT 1001',
                       item.table_name,item.column_name)
                       USING table_name,column_name,treatment,rights.tenant_id,rights.user_id::text;
                   END IF;
                 END LOOP;
               END $$""",
            (data_role,),
        )
        cursor.execute("REVOKE ALL ON FUNCTION base2_export_data_rights_subject_surfaces() FROM PUBLIC")
        cursor.execute(
            f"GRANT EXECUTE ON FUNCTION base2_export_data_rights_subject_surfaces() TO {quoted_data}"
        )
        cursor.execute(
            """CREATE OR REPLACE FUNCTION base2_apply_data_rights_subject_action(
                   requested_id uuid, requested_claim_token uuid,
                   requested_action text, requested_fields jsonb)
               RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER
               SET search_path=pg_catalog,public AS $$
               DECLARE rights record; item record; anonymous text; discovered_tenants text[];
                       has_other boolean; affected integer := 0; scope_tenants text[];
               BEGIN
                 IF session_user <> %s THEN RAISE EXCEPTION 'data_rights_role_required'; END IF;
                 SELECT * INTO rights FROM public.api_data_rights_operations operation
                  WHERE operation.id=requested_id AND operation.claim_token=requested_claim_token
                    AND operation.status='running' AND operation.claim_expires_at >= NOW()
                    AND operation.retention_until > NOW() FOR UPDATE;
                 IF NOT FOUND OR rights.kind<>requested_action THEN
                   RAISE EXCEPTION 'data_rights_claim_invalid';
                 END IF;
                 IF requested_action='correction' THEN
                   UPDATE public.api_auth_users subject SET
                     display_name=CASE WHEN requested_fields ? 'display_name'
                       THEN requested_fields->>'display_name' ELSE subject.display_name END,
                     avatar_url=CASE WHEN requested_fields ? 'avatar_url'
                       THEN requested_fields->>'avatar_url' ELSE subject.avatar_url END,
                     bio=CASE WHEN requested_fields ? 'bio'
                       THEN requested_fields->>'bio' ELSE subject.bio END,
                     updated_at=NOW()
                    WHERE subject.id=rights.user_id AND subject.is_active=TRUE;
                   IF NOT FOUND THEN RAISE EXCEPTION 'account_state_changed'; END IF;
                   RETURN jsonb_build_object('account_id',rights.user_id);
                 END IF;
                 IF requested_action NOT IN ('deletion','deactivation','global_deletion','global_deactivation') THEN
                   RAISE EXCEPTION 'data_rights_action_invalid';
                 END IF;
                 IF requested_action LIKE 'global_%%' THEN
                   SELECT COALESCE(array_agg(DISTINCT organization.tenant_id),ARRAY[]::text[])
                     INTO scope_tenants
                     FROM public.api_identity_memberships membership
                     JOIN public.api_identity_organizations organization
                       ON organization.id=membership.organization_id
                   WHERE membership.user_id=rights.user_id;
                   FOR item IN SELECT table_name,column_name
                     FROM public.sitecontent_subjectdataregistry
                     ORDER BY table_name,column_name LOOP
                     IF item.table_name='sitecontent_contentrevision' THEN
                       EXECUTE format(
                         'SELECT COALESCE(array_agg(DISTINCT content.site_id),ARRAY[]::text[]) FROM public.%%I subject_row JOIN public.sitecontent_contentrecord content ON content.id=subject_row.content_id WHERE subject_row.%%I=$1',
                         item.table_name,item.column_name)
                         INTO discovered_tenants USING rights.user_id::text;
                     ELSE
                       EXECUTE format(
                         'SELECT COALESCE(array_agg(DISTINCT site_id),ARRAY[]::text[]) FROM public.%%I WHERE %%I=$1',
                         item.table_name,item.column_name)
                         INTO discovered_tenants USING rights.user_id::text;
                     END IF;
                     SELECT COALESCE(array_agg(DISTINCT tenant_id),ARRAY[]::text[])
                       INTO scope_tenants
                       FROM unnest(scope_tenants || discovered_tenants) tenant_id;
                   END LOOP;
                 ELSE
                   scope_tenants := ARRAY[rights.tenant_id];
                 END IF;
                 IF requested_action IN ('deactivation','global_deactivation') AND EXISTS (
                    SELECT 1 FROM public.api_identity_memberships mine
                    JOIN public.api_identity_organizations organization
                      ON organization.id=mine.organization_id
                    WHERE mine.user_id=rights.user_id AND mine.role='owner'
                      AND mine.status='active' AND organization.tenant_id=ANY(scope_tenants)
                      AND NOT EXISTS (
                        SELECT 1 FROM public.api_identity_memberships other
                         WHERE other.organization_id=mine.organization_id
                           AND other.user_id<>mine.user_id AND other.role='owner'
                           AND other.status='active')) THEN
                   RAISE EXCEPTION 'last_owner_required';
                 END IF;
                 anonymous := 'deleted:' || left(md5(
                   rights.tenant_id || ':' || rights.user_id::text || ':' || requested_id::text),24);
                 IF requested_action IN ('deletion','global_deletion') THEN
                   FOR item IN SELECT table_name,column_name,treatment
                     FROM public.sitecontent_subjectdataregistry
                     WHERE table_name<>'sitecontent_contentrevision'
                     ORDER BY table_name,column_name LOOP
                     IF item.treatment='delete' THEN
                       EXECUTE format('DELETE FROM public.%%I WHERE site_id=ANY($1) AND %%I=$2',
                         item.table_name,item.column_name) USING scope_tenants,rights.user_id::text;
                     ELSIF item.treatment='media_delete' THEN
                       EXECUTE format('UPDATE public.%%I SET %%I='''', status=''deleted'', retention_until=NOW(), updated_at=NOW() WHERE site_id=ANY($1) AND %%I=$2',
                         item.table_name,item.column_name,item.column_name)
                         USING scope_tenants,rights.user_id::text;
                     ELSE
                       EXECUTE format('UPDATE public.%%I SET %%I=$1 WHERE site_id=ANY($2) AND %%I=$3',
                         item.table_name,item.column_name,item.column_name)
                         USING anonymous,scope_tenants,rights.user_id::text;
                     END IF;
                   END LOOP;
                   UPDATE public.sitecontent_contentrevision revision SET actor_ref=anonymous
                     FROM public.sitecontent_contentrecord content
                    WHERE content.id=revision.content_id AND content.site_id=ANY(scope_tenants)
                      AND revision.actor_ref=rights.user_id::text;
                   DELETE FROM public.api_identity_memberships membership
                    USING public.api_identity_organizations organization
                    WHERE membership.organization_id=organization.id
                      AND organization.tenant_id=ANY(scope_tenants)
                      AND membership.user_id=rights.user_id;
                 ELSE
                   UPDATE public.api_identity_memberships membership SET
                     status='suspended',updated_at=NOW()
                    FROM public.api_identity_organizations organization
                    WHERE membership.organization_id=organization.id
                      AND organization.tenant_id=ANY(scope_tenants)
                      AND membership.user_id=rights.user_id AND membership.status='active';
                 END IF;
                 SELECT EXISTS(SELECT 1 FROM public.api_identity_memberships membership
                   WHERE membership.user_id=rights.user_id AND membership.status='active')
                   INTO has_other;
                 IF requested_action LIKE 'global_%%' THEN
                   UPDATE public.api_auth_refresh_tokens SET revoked_at=NOW()
                    WHERE user_id=rights.user_id AND revoked_at IS NULL;
                   IF requested_action='global_deletion' THEN
                     DELETE FROM public.api_identity_recovery_codes WHERE user_id=rights.user_id;
                     DELETE FROM public.api_identity_login_challenges WHERE user_id=rights.user_id;
                     DELETE FROM public.api_identity_authenticators WHERE user_id=rights.user_id;
                     UPDATE public.api_identity_credentials SET revoked_at=NOW()
                      WHERE user_id=rights.user_id AND revoked_at IS NULL;
                     UPDATE public.api_auth_users SET
                       email='deleted-' || rights.user_id::text || '@deleted.invalid',
                       password_hash='',is_active=FALSE,is_email_verified=FALSE,
                       display_name='',avatar_url='',bio='',updated_at=NOW()
                      WHERE id=rights.user_id AND is_active=TRUE;
                   ELSE
                     UPDATE public.api_auth_users SET is_active=FALSE,updated_at=NOW()
                      WHERE id=rights.user_id AND is_active=TRUE;
                   END IF;
                 END IF;
                 RETURN jsonb_build_object(
                   'tenant_id',rights.tenant_id,
                   CASE WHEN requested_action IN ('deletion','global_deletion') THEN 'tenant_membership_deleted'
                        ELSE 'tenant_membership_deactivated' END,TRUE,
                   'global_account_deleted',requested_action='global_deletion',
                   'global_account_deactivated',requested_action='global_deactivation',
                   'scope',CASE WHEN requested_action LIKE 'global_%%' THEN 'all_tenants' ELSE 'tenant' END);
               END $$""",
            (data_role,),
        )
        cursor.execute(
            "REVOKE ALL ON FUNCTION base2_apply_data_rights_subject_action(uuid,uuid,text,jsonb) FROM PUBLIC"
        )
        cursor.execute(
            "GRANT EXECUTE ON FUNCTION base2_apply_data_rights_subject_action(uuid,uuid,text,jsonb) "
            f"TO {quoted_data}"
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
                   operation_result text, operation_digest text, operation_error text,
                   operation_tenant text, operation_user uuid, operation_kind text)
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
                    AND claim_token=operation_claim_token AND claim_expires_at >= NOW()
                    AND retention_until > NOW()
                    AND (terminal_status='failed' OR (tenant_id=operation_tenant
                         AND user_id=operation_user AND kind=operation_kind));
                 GET DIAGNOSTICS changed = ROW_COUNT;
                 IF changed=1 AND terminal_status='completed' THEN
                   INSERT INTO public.api_auth_audit_events
                     (id,user_id,action,ip,user_agent,metadata_json,created_at)
                   VALUES (gen_random_uuid(),operation_user,
                     'privacy.' || operation_kind || '_completed','','',
                     jsonb_build_object('operation_id',operation_id,'tenant_id',operation_tenant),NOW());
                 END IF;
                 RETURN changed = 1;
               END $$""",
            (data_role,),
        )
        cursor.execute(
            "REVOKE ALL ON FUNCTION base2_finalize_data_rights_operation(uuid,uuid,text,text,text,text,text,uuid,text) FROM PUBLIC"
        )
        cursor.execute(
            "GRANT EXECUTE ON FUNCTION "
            "base2_finalize_data_rights_operation(uuid,uuid,text,text,text,text,text,uuid,text) "
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
            "base2_finalize_data_rights_operation(uuid,uuid,text,text,text,text,text,uuid,text)"
        )
        cursor.execute(
            "DROP FUNCTION IF EXISTS base2_apply_data_rights_subject_action(uuid,uuid,text,jsonb)"
        )
        cursor.execute("DROP FUNCTION IF EXISTS base2_export_data_rights_subject_surfaces()")
        cursor.execute("DROP FUNCTION IF EXISTS base2_claim_data_rights_operation(uuid,uuid,uuid)")
        cursor.execute("DROP FUNCTION IF EXISTS base2_list_due_data_rights_operations(integer)")
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
        cursor.execute("DROP FUNCTION IF EXISTS base2_data_rights_subject_id(text)")
        cursor.execute("DROP TABLE IF EXISTS sitecontent_subjectdataregistry")
        cursor.execute("ALTER TABLE api_data_rights_operations DROP COLUMN IF EXISTS dispatch_expires_at")
        cursor.execute("ALTER TABLE api_data_rights_operations DROP COLUMN IF EXISTS dispatch_token")
        cursor.execute(
            "ALTER TABLE api_data_rights_operations DROP CONSTRAINT IF EXISTS api_data_rights_operations_kind_check"
        )
        cursor.execute(
            "ALTER TABLE api_data_rights_operations ADD CONSTRAINT api_data_rights_operations_kind_check "
            "CHECK (kind IN ('export','correction','deactivation','deletion'))"
        )
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
        for table, privileges in LEGACY_CONTENT_IDENTITY_GRANTS.items():
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
