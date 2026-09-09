from __future__ import annotations

import os
import re

from django.db import migrations

ROLE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,62}$")


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
          AFTER INSERT OR UPDATE OF storage_key,sha256 OR DELETE ON sitecontent_mediaasset
          FOR EACH STATEMENT EXECUTE FUNCTION base2_bump_object_reference_generation();
        CREATE TRIGGER base2_mediauploadpart_reference_generation
          AFTER INSERT OR UPDATE OF storage_key,sha256 OR DELETE ON sitecontent_mediauploadpart
          FOR EACH STATEMENT EXECUTE FUNCTION base2_bump_object_reference_generation();
        CREATE TRIGGER base2_importjob_reference_generation
          AFTER INSERT OR UPDATE OF source_object_key,source_sha256 OR DELETE ON sitecontent_importjob
          FOR EACH STATEMENT EXECUTE FUNCTION base2_bump_object_reference_generation();
        CREATE TRIGGER base2_exportjob_reference_generation
          AFTER INSERT OR UPDATE OF encrypted_object_key,output_sha256 OR DELETE ON sitecontent_exportjob
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
        DROP TRIGGER IF EXISTS base2_mediauploadpart_reference_generation ON sitecontent_mediauploadpart;
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
        cursor.execute(
            "SELECT relname FROM pg_class JOIN pg_namespace n ON n.oid=relnamespace "
            "WHERE n.nspname='public' AND relkind IN ('r','p') AND relname LIKE 'api\\_%' ESCAPE '\\'"
        )
        tables = [schema_editor.connection.ops.quote_name(row[0]) for row in cursor.fetchall()]
        if not tables:
            raise RuntimeError("api_runtime:tables_unavailable")
        cursor.execute(
            f"GRANT SELECT,INSERT,UPDATE,DELETE ON TABLE {','.join(tables)} TO {quoted}"
        )
        cursor.execute(
            "SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
            "WHERE n.nspname='public' AND c.relkind='S' AND c.relname LIKE 'api\\_%' ESCAPE '\\'"
        )
        sequences = [schema_editor.connection.ops.quote_name(row[0]) for row in cursor.fetchall()]
        if sequences:
            cursor.execute(f"GRANT USAGE,SELECT ON SEQUENCE {','.join(sequences)} TO {quoted}")


def revoke_api_runtime(apps, schema_editor):
    del apps
    if schema_editor.connection.vendor != "postgresql":
        return
    role = os.environ.get("API_RUNTIME_DB_USER", "").strip()
    if not ROLE.fullmatch(role):
        raise RuntimeError("api_runtime:role_invalid")
    quoted = schema_editor.connection.ops.quote_name(role)
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(f"REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM {quoted}")
        cursor.execute(f"REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM {quoted}")
        cursor.execute(f"REVOKE USAGE ON SCHEMA public FROM {quoted}")


class Migration(migrations.Migration):
    dependencies = [("sitecontent", "0031_data_rights_worker_scope")]
    operations = [
        migrations.RunPython(create_reference_generation, drop_reference_generation),
        migrations.RunPython(configure_api_runtime, revoke_api_runtime),
    ]
