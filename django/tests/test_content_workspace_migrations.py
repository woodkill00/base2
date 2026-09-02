from __future__ import annotations

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

pytestmark = pytest.mark.django_db(transaction=True)

BASE = ("sitecontent", "0001_initial")
LATEST = ("sitecontent", "0010_workspace_worker_role")


def _executor() -> MigrationExecutor:
    return MigrationExecutor(connection)


def test_workspace_migrations_reverse_and_forward_without_losing_legacy_records():
    # 0001 is the exact workspace-free schema on current Base2 main. The
    # populated row represents a previously generated site profile.
    executor = _executor()
    executor.migrate([BASE])
    base_apps = executor.loader.project_state([BASE]).apps
    LegacyRecord = base_apps.get_model("sitecontent", "ContentRecord")
    legacy = LegacyRecord.objects.create(
        site_id="site-a",
        content_type="page",
        slug="migration-proof",
        title="Migration proof",
    )

    try:
        executor = _executor()
        executor.migrate([LATEST])
        latest_apps = executor.loader.project_state([LATEST]).apps
        CurrentRecord = latest_apps.get_model("sitecontent", "ContentRecord")
        migrated = CurrentRecord.objects.get(pk=legacy.pk)
        assert migrated.slug == "migration-proof"
        assert migrated.values == {}
        assert migrated.schema_version == 1
        assert migrated.schedule_timezone == ""

        ImportJob = latest_apps.get_model("sitecontent", "ImportJob")
        ExportJob = latest_apps.get_model("sitecontent", "ExportJob")
        MediaAsset = latest_apps.get_model("sitecontent", "MediaAsset")
        assert ImportJob._meta.get_field("source_object_key").default == ""
        assert ExportJob._meta.get_field("projection_fields").default is list
        assert "rejected" in dict(MediaAsset._meta.get_field("status").choices)

        executor = _executor()
        executor.migrate([BASE])
        reversed_apps = executor.loader.project_state([BASE]).apps
        ReversedRecord = reversed_apps.get_model("sitecontent", "ContentRecord")
        assert ReversedRecord.objects.filter(pk=legacy.pk, slug="migration-proof").exists()
    finally:
        _executor().migrate([LATEST])


def test_latest_workspace_state_contains_expected_constraints_and_indexes():
    executor = _executor()
    state = executor.loader.project_state([LATEST])
    definition = state.models[("sitecontent", "contenttypedefinition")]
    record = state.models[("sitecontent", "contentrecord")]
    relationship = state.models[("sitecontent", "contentrelationship")]
    assert any(
        constraint.name == "sitecontent_type_version_uq"
        for constraint in definition.options["constraints"]
    )
    assert any(
        constraint.name == "sitecontent_record_slug_uq"
        for constraint in record.options["constraints"]
    )
    assert any(
        constraint.name == "sitecontent_no_self_rel"
        for constraint in relationship.options["constraints"]
    )
    assert any(index.name == "sitecontent_type_idx" for index in record.options["indexes"])
