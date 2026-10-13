"""Public API capabilities without workspace credentials or broad table access."""

import os
import re

from django.db import migrations

SELECT = {
    "sitecontent_contentrecord": (
        "id,site_id,content_type,slug,title,excerpt,body,metadata,state,"
        "published_at,updated_at,search_visible"
    ),
    "sitecontent_mediaasset": (
        "id,site_id,original_name,media_type,byte_size,sha256,attribution,metadata,"
        "updated_at,status,visibility"
    ),
    "sitecontent_searchdocument": (
        "id,site_id,content_id,title,body,url_path,indexed_at,source_updated_at,"
        "visibility,tombstoned_at"
    ),
    "sitecontent_formsubmission": "id,site_id,form_key,replay_key,request_digest,status,created_at",
}
INSERT = {
    "sitecontent_contentrecord": (
        "id,site_id,content_type,slug,title,excerpt,body,metadata,state,sitemap_include,"
        "search_visible,version,schedule_timezone,schema_version,values,created_at,updated_at"
    ),
    "sitecontent_formsubmission": (
        "id,site_id,form_key,replay_key,request_digest,payload,consent,request_id,status,"
        "retained_until,created_at,updated_at"
    ),
    "sitecontent_formdeliveryoutbox": (
        "id,submission_id,adapter,status,attempts,next_attempt_at,last_error_code,"
        "created_at,updated_at"
    ),
}
NEW_RLS = (
    "sitecontent_searchdocument",
    "sitecontent_formsubmission",
    "sitecontent_formdeliveryoutbox",
)
TENANT = "site_id=current_setting('app.tenant_id',true)"
READ_SCOPE = {
    "sitecontent_contentrecord": f"{TENANT} AND state='published' AND deleted_at IS NULL",
    "sitecontent_mediaasset": (
        f"{TENANT} AND status IN ('validated','ready') AND visibility='public' "
        "AND deleted_at IS NULL AND archived_at IS NULL"
    ),
    "sitecontent_searchdocument": (
        f"{TENANT} AND visibility='public' AND tombstoned_at IS NULL AND EXISTS "
        "(SELECT 1 FROM public.sitecontent_contentrecord c WHERE c.id=content_id "
        "AND c.site_id=sitecontent_searchdocument.site_id "
        "AND c.state='published' AND c.search_visible)"
    ),
    "sitecontent_formsubmission": TENANT,
}
WRITE_SCOPE = {
    "sitecontent_contentrecord": (
        f"{TENANT} AND content_type='community-post' AND state='draft' "
        "AND NOT sitemap_include AND NOT search_visible AND published_at IS NULL "
        "AND publish_at IS NULL AND deleted_at IS NULL AND definition_id IS NULL "
        "AND schema_version=1 AND version=1 AND values='{}'::jsonb "
        "AND metadata->>'moderationStatus'='pending'"
    ),
    "sitecontent_formsubmission": (
        f"{TENANT} AND status='queued' AND delivered_at IS NULL AND retained_until>NOW() "
        "AND retained_until<=NOW()+INTERVAL '3660 days'"
    ),
    "sitecontent_formdeliveryoutbox": (
        "adapter='disabled' AND status='queued' AND attempts=0 AND last_error_code='' "
        "AND delivered_at IS NULL AND EXISTS (SELECT 1 FROM public.sitecontent_formsubmission s "
        "WHERE s.id=submission_id AND s.site_id=current_setting('app.tenant_id',true))"
    ),
}


def role_name(editor, variable="API_RUNTIME_DB_USER"):
    role = os.environ.get(variable, "").strip()
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,62}", role):
        raise RuntimeError("public_content:role_invalid")
    with editor.connection.cursor() as cur:
        cur.execute(
            "SELECT rolsuper,rolcreatedb,rolcreaterole,rolbypassrls FROM pg_roles WHERE rolname=%s",
            (role,),
        )
        row = cur.fetchone()
        if row is None or any(row):
            raise RuntimeError("public_content:restricted_role_required")
    return editor.connection.ops.quote_name(role)


def configure(apps, editor):
    if editor.connection.vendor != "postgresql":
        return
    role = role_name(editor)
    data_role = role_name(editor, "DATA_RIGHTS_WORKER_DB_USER")
    with editor.connection.cursor() as cur:
        # Its predicate already excludes all other roles. Explicit targeting also
        # avoids requiring unrelated API readers to access private audit rows.
        cur.execute(
            f"ALTER POLICY data_rights_claim_fence ON sitecontent_contentrecord TO {data_role}"
        )
        for table in NEW_RLS:
            cur.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
            # Preserve existing non-API roles; their grants remain unchanged.
            # API restrictions below intersect this permissive baseline.
            cur.execute(
                f"CREATE POLICY public_content_existing_access ON {table} "
                "USING (true) WITH CHECK (true)"
            )
        for verb, grants, predicates in (
            ("SELECT", SELECT, READ_SCOPE),
            ("INSERT", INSERT, WRITE_SCOPE),
        ):
            for table, columns in grants.items():
                cur.execute(f"GRANT {verb} ({columns}) ON {table} TO {role}")
                predicate = predicates[table]
                clause = f"USING ({predicate})" if verb == "SELECT" else f"WITH CHECK ({predicate})"
                cur.execute(
                    f"CREATE POLICY public_content_{verb.lower()} ON {table} "
                    f"AS RESTRICTIVE FOR {verb} TO {role} {clause}"
                )


def reverse(apps, editor):
    if editor.connection.vendor != "postgresql":
        return
    role = role_name(editor)
    with editor.connection.cursor() as cur:
        for verb, grants in (("SELECT", SELECT), ("INSERT", INSERT)):
            for table, columns in grants.items():
                cur.execute(f"DROP POLICY public_content_{verb.lower()} ON {table}")
                cur.execute(f"REVOKE {verb} ({columns}) ON {table} FROM {role}")
        for table in NEW_RLS:
            cur.execute(f"DROP POLICY public_content_existing_access ON {table}")
            cur.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
        cur.execute("ALTER POLICY data_rights_claim_fence ON sitecontent_contentrecord TO PUBLIC")


class Migration(migrations.Migration):
    dependencies = [("sitecontent", "0033_api_schema_readiness")]
    operations = [migrations.RunPython(configure, reverse)]
