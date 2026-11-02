"""Admit authorized tenant revisions while retaining the 0031 rights claim fence.

0031 enabled forced RLS on revisions but installed only a restrictive policy.
PostgreSQL also requires a permissive policy: without one all runtime operations
are denied. Resolve the parent through its own RLS, and bind its tenant explicitly.
No grants, public access, or data-rights claim authority are added here.
"""
from importlib import import_module

from django.db import migrations

POLICY = 'workspace_revision_tenant_scope'
TABLE = 'public.sitecontent_contentrevision'
PARENT = """EXISTS (SELECT 1 FROM public.sitecontent_contentrecord content
 WHERE content.id=sitecontent_contentrevision.content_id
 AND content.site_id=current_setting('app.tenant_id',true))"""


def configure(apps, editor):
    if editor.connection.vendor != 'postgresql':
        return
    helper = import_module('sitecontent.migrations.0034_public_content_runtime_scope')
    request = helper.role_name(editor, 'WORKSPACE_DB_USER')
    worker = helper.role_name(editor, 'WORKSPACE_WORKER_DB_USER')
    with editor.connection.cursor() as cursor:
        cursor.execute(
            f'CREATE POLICY {POLICY} ON {TABLE} AS PERMISSIVE FOR ALL TO {request}, {worker} '
            f'USING ({PARENT}) WITH CHECK ({PARENT})'
        )


def reverse(apps, editor):
    if editor.connection.vendor != 'postgresql':
        return
    with editor.connection.cursor() as cursor:
        # Remove only this admission policy; forced RLS and claim fence remain.
        cursor.execute(f'DROP POLICY IF EXISTS {POLICY} ON {TABLE}')


class Migration(migrations.Migration):
    dependencies = [('sitecontent', '0040_workspace_asset_retention')]
    operations = [migrations.RunPython(configure, reverse)]
