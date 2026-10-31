import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

pytestmark = pytest.mark.django_db(transaction=True)
BASE = ("sitecontent", "0035_booking_runtime_capability")
LATEST = ("sitecontent", "0036_workspace_policy_review_state")


def test_compatibility_backfill_covers_content_without_membership_and_reverses():
    executor = MigrationExecutor(connection)
    leaves = executor.loader.graph.leaf_nodes()
    executor.migrate([BASE])
    try:
        apps = executor.loader.project_state([BASE]).apps
        Record = apps.get_model("sitecontent", "ContentRecord")
        row = Record.objects.create(
            site_id="legacy-without-members",
            content_type="page",
            slug="legacy",
            title="Preserved",
            state="published",
        )
        before = Record.objects.values().get(pk=row.pk)
        executor = MigrationExecutor(connection)
        executor.migrate([LATEST])
        apps = executor.loader.project_state([LATEST]).apps
        Policy = apps.get_model("sitecontent", "WorkspacePolicy")
        for site in [row.site_id]:
            policy = Policy.objects.get(site_id=site)
            assert not policy.require_review and policy.public_access == "public_allowed"
            assert policy.provenance == "migrated" and policy.version == 1
        assert (
            apps.get_model("sitecontent", "ContentRecord").objects.values().get(pk=row.pk) == before
        )
        assert not apps.get_model("sitecontent", "ReviewApproval").objects.exists()
        assert not apps.get_model("sitecontent", "ReviewSubject").objects.exists()
        executor = MigrationExecutor(connection)
        executor.migrate([BASE])
        apps = executor.loader.project_state([BASE]).apps
        assert (
            apps.get_model("sitecontent", "ContentRecord").objects.values().get(pk=row.pk) == before
        )
    finally:
        MigrationExecutor(connection).migrate(leaves)


def test_identity_only_tenants_are_backfilled_without_uuid_realm_join(monkeypatch):
    from contextlib import nullcontext
    from importlib import import_module
    from types import SimpleNamespace
    from unittest.mock import Mock
    from uuid import uuid4

    from django.apps import apps

    migration = import_module("sitecontent.migrations.0036_workspace_policy_review_state")
    organization_id = uuid4()
    cursor = Mock()
    cursor.fetchone.return_value = ("api_identity_organizations",)
    cursor.fetchall.return_value = [("1", organization_id)]
    editor = SimpleNamespace(
        connection=SimpleNamespace(
            alias="default", vendor="postgresql", cursor=lambda: nullcontext(cursor)
        )
    )
    migration.backfill_workspace_policies(apps, editor)
    Policy = apps.get_model("sitecontent", "WorkspacePolicy")
    policy = Policy.objects.get(site_id="1")
    assert policy.organization_id == organization_id
    assert policy.provenance == "migrated" and not policy.require_review
    # Repeated migration cannot overwrite an explicit owner's later policy.
    Policy.objects.filter(pk=policy.pk).update(
        require_review=True, provenance="explicit", version=2
    )
    migration.backfill_workspace_policies(apps, editor)
    policy.refresh_from_db()
    assert policy.require_review and policy.version == 2 and policy.provenance == "explicit"
    cursor.fetchone.return_value = (None,)
    migration.backfill_workspace_policies(apps, editor)


def test_backfill_invalid_historical_scope_fails_closed():
    from importlib import import_module
    from types import SimpleNamespace

    from django.apps import apps

    apps.get_model("sitecontent", "ContentRecord").objects.create(
        site_id="INVALID", content_type="page", slug="invalid", title="Invalid legacy scope"
    )
    migration = import_module("sitecontent.migrations.0036_workspace_policy_review_state")
    editor = SimpleNamespace(connection=SimpleNamespace(alias="default", vendor="sqlite"))
    with pytest.raises(RuntimeError, match="workspace_policy_backfill_invalid_scope"):
        migration.backfill_workspace_policies(apps, editor)


def test_fresh_configured_site_does_not_receive_permissive_compatibility_policy(settings):
    from importlib import import_module
    from types import SimpleNamespace

    from django.apps import apps

    settings.SITE_ID = "fresh-install"
    migration = import_module("sitecontent.migrations.0036_workspace_policy_review_state")
    editor = SimpleNamespace(connection=SimpleNamespace(alias="default", vendor="sqlite"))
    migration.backfill_workspace_policies(apps, editor)
    Policy = apps.get_model("sitecontent", "WorkspacePolicy")
    assert not Policy.objects.filter(site_id=settings.SITE_ID).exists()
    policy = Policy.objects.create(site_id=settings.SITE_ID)
    assert policy.require_review and policy.public_access == "members_only"
    assert policy.provenance == "default"
