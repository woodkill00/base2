from __future__ import annotations

import os
import re

from django.db import migrations

ROLE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,62}$")
API_RUNTIME_GRANTS = {
    "api_schema_migrations": "SELECT",
    "api_auth_users": "SELECT,INSERT,UPDATE",
    "api_auth_refresh_tokens": "SELECT,INSERT,UPDATE",
    "api_auth_one_time_tokens": "SELECT,INSERT,UPDATE",
    "api_auth_audit_events": "SELECT,INSERT",
    "api_auth_oauth_accounts": "SELECT,INSERT",
    "api_identity_organizations": "SELECT,INSERT",
    "api_identity_memberships": "SELECT,INSERT,UPDATE",
    "api_identity_invitations": "SELECT,INSERT,UPDATE",
    "api_identity_authenticators": "SELECT,INSERT,UPDATE,DELETE",
    "api_identity_recovery_codes": "SELECT,INSERT,UPDATE,DELETE",
    "api_identity_login_challenges": "SELECT,INSERT,UPDATE,DELETE",
    "api_identity_credentials": "SELECT,INSERT,UPDATE",
    "api_data_rights_operations": "SELECT,INSERT",
    "api_user_preferences": "SELECT,INSERT,UPDATE",
    "api_notification_preferences": "SELECT,INSERT,DELETE",
}


def create_reference_generation(apps, schema_editor):
    del apps
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(
        """
        CREATE TABLE sitecontent_objectreferencegeneration (
          singleton boolean PRIMARY KEY DEFAULT TRUE CHECK (singleton),
          generation bigint NOT NULL DEFAULT 0
        );
        INSERT INTO sitecontent_objectreferencegeneration(singleton,generation)
          VALUES(TRUE,0) ON CONFLICT(singleton) DO NOTHING;
        CREATE OR REPLACE FUNCTION base2_bump_object_reference_generation()
          RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER
          SET search_path=pg_catalog,public AS $$
          BEGIN
            UPDATE public.sitecontent_objectreferencegeneration
               SET generation=generation+1 WHERE singleton=TRUE;
            RETURN COALESCE(NEW,OLD);
          END $$;
        CREATE TRIGGER base2_mediaasset_reference_generation
          AFTER INSERT OR UPDATE OF site_id,storage_key,sha256 OR DELETE ON sitecontent_mediaasset
          FOR EACH STATEMENT EXECUTE FUNCTION base2_bump_object_reference_generation();
        CREATE TRIGGER base2_mediauploadpart_reference_generation
          AFTER INSERT OR UPDATE OF site_id,storage_key,sha256
          OR DELETE ON sitecontent_mediauploadpart
          FOR EACH STATEMENT EXECUTE FUNCTION base2_bump_object_reference_generation();
        CREATE TRIGGER base2_mediavariant_reference_generation
          AFTER INSERT OR UPDATE OF asset_id,storage_key,sha256
          OR DELETE ON sitecontent_mediavariant
          FOR EACH STATEMENT EXECUTE FUNCTION base2_bump_object_reference_generation();
        CREATE TRIGGER base2_mediaobjectversion_reference_generation
          AFTER INSERT OR UPDATE OF site_id,storage_key,sha256
          OR DELETE ON sitecontent_mediaobjectversion
          FOR EACH STATEMENT EXECUTE FUNCTION base2_bump_object_reference_generation();
        CREATE TRIGGER base2_importjob_reference_generation
          AFTER INSERT OR UPDATE OF site_id,source_object_key,source_sha256
          OR DELETE ON sitecontent_importjob
          FOR EACH STATEMENT EXECUTE FUNCTION base2_bump_object_reference_generation();
        CREATE TRIGGER base2_exportjob_reference_generation
          AFTER INSERT OR UPDATE OF site_id,encrypted_object_key,output_sha256
          OR DELETE ON sitecontent_exportjob
          FOR EACH STATEMENT EXECUTE FUNCTION base2_bump_object_reference_generation();
        REVOKE ALL ON sitecontent_objectreferencegeneration FROM PUBLIC;
        """
    )


def drop_reference_generation(apps, schema_editor):
    del apps
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(
        """
        DROP TRIGGER IF EXISTS base2_exportjob_reference_generation ON sitecontent_exportjob;
        DROP TRIGGER IF EXISTS base2_importjob_reference_generation ON sitecontent_importjob;
        DROP TRIGGER IF EXISTS base2_mediaobjectversion_reference_generation
          ON sitecontent_mediaobjectversion;
        DROP TRIGGER IF EXISTS base2_mediavariant_reference_generation ON sitecontent_mediavariant;
        DROP TRIGGER IF EXISTS base2_mediauploadpart_reference_generation
          ON sitecontent_mediauploadpart;
        DROP TRIGGER IF EXISTS base2_mediaasset_reference_generation ON sitecontent_mediaasset;
        DROP FUNCTION IF EXISTS base2_bump_object_reference_generation();
        DROP TABLE IF EXISTS sitecontent_objectreferencegeneration;
        """
    )


def configure_api_runtime(apps, schema_editor):
    del apps
    if schema_editor.connection.vendor != "postgresql":
        return
    role = os.environ.get("API_RUNTIME_DB_USER", "").strip()
    if not ROLE.fullmatch(role):
        raise RuntimeError("api_runtime:role_invalid")
    quoted = schema_editor.connection.ops.quote_name(role)
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            "SELECT rolsuper,rolcreatedb,rolcreaterole,rolbypassrls "
            "FROM pg_roles WHERE rolname=%s",
            (role,),
        )
        row = cursor.fetchone()
        if not row or any(row):
            raise RuntimeError("api_runtime:least_privilege_role_required")
        cursor.execute(f"REVOKE CREATE ON SCHEMA public FROM {quoted}")
        cursor.execute(f"GRANT USAGE ON SCHEMA public TO {quoted}")
        cursor.execute(f"REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM {quoted}")
        cursor.execute(f"REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM {quoted}")
        for table, privileges in API_RUNTIME_GRANTS.items():
            quoted_table = schema_editor.connection.ops.quote_name(table)
            cursor.execute("SELECT to_regclass(%s)", (f"public.{table}",))
            if cursor.fetchone()[0] is None:
                raise RuntimeError(f"api_runtime:table_unavailable:{table}")
            cursor.execute(f"GRANT {privileges} ON TABLE {quoted_table} TO {quoted}")

        cursor.execute(
            """CREATE OR REPLACE FUNCTION base2_enqueue_email(
                   requested_id uuid, requested_to text, requested_subject text,
                   requested_body_text text, requested_body_html text)
               RETURNS TABLE(outbox_id uuid, outbox_status text, outbox_provider text,
                             outbox_created_at timestamptz, outbox_delivery_key text)
               LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
               BEGIN
                 IF session_user <> %s OR requested_id IS NULL
                    OR octet_length(requested_to) NOT BETWEEN 3 AND 320
                    OR octet_length(requested_subject) NOT BETWEEN 1 AND 998
                    OR octet_length(requested_body_text) > 1048576
                    OR octet_length(requested_body_html) > 1048576 THEN
                   RAISE EXCEPTION 'email_enqueue_denied' USING ERRCODE='42501';
                 END IF;
                 RETURN QUERY
                   INSERT INTO public.api_email_outbox(
                     id,to_email,subject,body_text,body_html,delivery_key)
                   VALUES(requested_id,requested_to,requested_subject,
                          requested_body_text,requested_body_html,requested_id::text)
                   RETURNING id,status,provider,created_at,delivery_key;
               END $$""",
            (role,),
        )
        cursor.execute(
            "REVOKE ALL ON FUNCTION base2_enqueue_email(uuid,text,text,text,text) FROM PUBLIC"
        )
        cursor.execute(
            f"GRANT EXECUTE ON FUNCTION base2_enqueue_email(uuid,text,text,text,text) TO {quoted}"
        )

        api_literal = "'" + role.replace("'", "''") + "'"
        tenant = "current_setting('app.tenant_id', true)"
        tenant_predicates = {
            "api_identity_organizations": f"tenant_id={tenant}",
            "api_identity_memberships": (
                "EXISTS (SELECT 1 FROM api_identity_organizations scope_org "
                "WHERE scope_org.id=api_identity_memberships.organization_id "
                f"AND scope_org.tenant_id={tenant})"
            ),
            "api_identity_invitations": (
                "EXISTS (SELECT 1 FROM api_identity_organizations scope_org "
                "WHERE scope_org.id=api_identity_invitations.organization_id "
                f"AND scope_org.tenant_id={tenant})"
            ),
            "api_identity_credentials": (
                "EXISTS (SELECT 1 FROM api_identity_organizations scope_org "
                "WHERE scope_org.id=api_identity_credentials.organization_id "
                f"AND scope_org.tenant_id={tenant})"
            ),
            "api_data_rights_operations": f"tenant_id={tenant}",
            "api_user_preferences": f"tenant_id={tenant}",
            "api_notification_preferences": f"tenant_id={tenant}",
        }
        for table, scope in tenant_predicates.items():
            quoted_table = schema_editor.connection.ops.quote_name(table)
            cursor.execute(f"ALTER TABLE {quoted_table} ENABLE ROW LEVEL SECURITY")
            cursor.execute(f"ALTER TABLE {quoted_table} FORCE ROW LEVEL SECURITY")
            cursor.execute(f"DROP POLICY IF EXISTS identity_api_access ON {quoted_table}")
            cursor.execute(f"DROP POLICY IF EXISTS api_runtime_tenant_scope ON {quoted_table}")
            cursor.execute(
                f"CREATE POLICY api_runtime_tenant_scope ON {quoted_table} "
                f"USING (current_user={api_literal} AND ({scope})) "
                f"WITH CHECK (current_user={api_literal} AND ({scope}))"
            )


def revoke_api_runtime(apps, schema_editor):
    del apps
    if schema_editor.connection.vendor != "postgresql":
        return
    role = os.environ.get("API_RUNTIME_DB_USER", "").strip()
    if not ROLE.fullmatch(role):
        raise RuntimeError("api_runtime:role_invalid")
    quoted = schema_editor.connection.ops.quote_name(role)
    with schema_editor.connection.cursor() as cursor:
        api_literal = "'" + role.replace("'", "''") + "'"
        predecessor_policy_tables = {
            "api_identity_organizations",
            "api_identity_memberships",
            "api_identity_credentials",
            "api_data_rights_operations",
        }
        introduced_rls_tables = {
            "api_identity_invitations",
            "api_user_preferences",
            "api_notification_preferences",
        }
        for table in predecessor_policy_tables | introduced_rls_tables:
            quoted_table = schema_editor.connection.ops.quote_name(table)
            cursor.execute(f"DROP POLICY IF EXISTS api_runtime_tenant_scope ON {quoted_table}")
            if table in predecessor_policy_tables:
                cursor.execute(
                    f"CREATE POLICY identity_api_access ON {quoted_table} "
                    f"USING (current_user={api_literal}) WITH CHECK (current_user={api_literal})"
                )
            else:
                cursor.execute(f"ALTER TABLE {quoted_table} NO FORCE ROW LEVEL SECURITY")
                cursor.execute(f"ALTER TABLE {quoted_table} DISABLE ROW LEVEL SECURITY")
        cursor.execute("DROP FUNCTION IF EXISTS base2_enqueue_email(uuid,text,text,text,text)")
        cursor.execute(f"REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM {quoted}")
        cursor.execute(f"REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM {quoted}")
        cursor.execute(f"REVOKE USAGE ON SCHEMA public FROM {quoted}")


class Migration(migrations.Migration):
    dependencies = [("sitecontent", "0031_data_rights_worker_scope")]
    operations = [
        migrations.RunPython(create_reference_generation, drop_reference_generation),
        migrations.RunPython(configure_api_runtime, revoke_api_runtime),
    ]
