from django.db import migrations

WORKSPACE_TABLES = (
    "sitecontent_contenttypedefinition",
    "sitecontent_contentrecord",
    "sitecontent_contentrelationship",
    "sitecontent_savedview",
    "sitecontent_assetbinding",
    "sitecontent_importjob",
    "sitecontent_exportjob",
    "sitecontent_workspaceauditevent",
    "sitecontent_mediaasset",
)


def enable_workspace_rls(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cursor:
        for table in WORKSPACE_TABLES:
            policy = f"{table}_tenant_scope"
            cursor.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
            cursor.execute(f'DROP POLICY IF EXISTS "{policy}" ON "{table}"')
            cursor.execute(
                f"""CREATE POLICY "{policy}" ON "{table}"
                    USING (site_id = current_setting('app.tenant_id', true))
                    WITH CHECK (site_id = current_setting('app.tenant_id', true))"""
            )


def disable_workspace_rls(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cursor:
        for table in reversed(WORKSPACE_TABLES):
            policy = f"{table}_tenant_scope"
            cursor.execute(f'DROP POLICY IF EXISTS "{policy}" ON "{table}"')
            cursor.execute(f'ALTER TABLE "{table}" DISABLE ROW LEVEL SECURITY')


class Migration(migrations.Migration):
    dependencies = [("sitecontent", "0002_workspaceauditevent_contentrecordversion_and_more")]

    operations = [migrations.RunPython(enable_workspace_rls, disable_workspace_rls)]
