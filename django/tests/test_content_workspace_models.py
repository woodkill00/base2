from __future__ import annotations

from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from sitecontent.models import (
    AssetBinding,
    ContentFieldDefinition,
    ContentRecord,
    ContentRecordVersion,
    ContentRelationship,
    ContentTypeDefinition,
    ExportJob,
    ImportJob,
    SavedView,
    WorkflowDefinition,
    WorkspaceAuditEvent,
)

pytestmark = pytest.mark.django_db


def definition(*, site_id: str = "site-a", version: int = 1, status: str = "draft"):
    return ContentTypeDefinition.objects.create(
        site_id=site_id,
        type_key="article",
        version=version,
        name="Article",
        status=status,
        lock_version=1,
    )


def test_definition_version_is_site_scoped_and_published_rows_are_immutable():
    first = definition(status="published")
    definition(site_id="site-b", status="published")
    with pytest.raises((IntegrityError, ValidationError)), transaction.atomic():
        definition(status="published")

    first.name = "Changed in place"
    with pytest.raises(ValidationError, match="published_definition_immutable"):
        first.save()


def test_field_definitions_use_closed_kinds_and_bounded_configuration():
    content_type = definition()
    field = ContentFieldDefinition(
        definition=content_type,
        field_key="title",
        label="Title",
        field_kind="short_text",
        required=True,
        validation={"minLength": 1, "maxLength": 240},
        presentation={"renderer": "text", "width": "full"},
    )
    field.full_clean()

    field.field_kind = "python"
    with pytest.raises(ValidationError):
        field.full_clean()
    field.field_kind = "short_text"
    field.validation = {"regularExpression": ".*"}
    with pytest.raises(ValidationError, match="field_validation_key_invalid"):
        field.full_clean()


def test_workflow_graph_rejects_unknown_states_actions_and_destinations():
    content_type = definition()
    workflow = WorkflowDefinition(
        definition=content_type,
        states=["draft", "in_review", "published", "archived"],
        initial_state="draft",
        transitions=[
            {
                "action": "submit_review",
                "from": ["draft"],
                "to": "in_review",
                "permission": "content.review",
            }
        ],
    )
    workflow.full_clean()
    workflow.transitions[0]["to"] = "execute-shell"
    with pytest.raises(ValidationError, match="workflow_state_invalid"):
        workflow.full_clean()


def test_definition_preview_classifies_loss_and_publication_requires_confirmation():
    first = definition(status="published")
    ContentFieldDefinition.objects.create(
        definition=first,
        field_key="title",
        label="Title",
        field_kind="short_text",
        required=True,
    )
    candidate = definition(version=2)
    preview = candidate.preview_compatibility(previous=first)
    assert preview["classification"] == "lossy"
    assert preview["removedFields"] == ["title"]
    with pytest.raises(ValidationError, match="lossy_confirmation_required"):
        candidate.publish(expected_lock_version=1)
    candidate.publish(expected_lock_version=1, confirm_lossy=True)
    candidate.refresh_from_db()
    assert candidate.status == "published"
    assert candidate.published_at is not None


def test_definition_publication_rejects_stale_lock_and_unpublished_field_defaults():
    candidate = definition()
    ContentFieldDefinition.objects.create(
        definition=candidate,
        field_key="title",
        label="Title",
        field_kind="short_text",
        required=True,
        validation={"minLength": 1, "maxLength": 10},
    )
    with pytest.raises(ValidationError, match="definition_version_conflict"):
        candidate.publish(expected_lock_version=2)
    candidate.publish(expected_lock_version=1)


def test_records_bind_exact_schema_and_reject_stale_expected_version():
    content_type = definition(status="published")
    record = ContentRecord.objects.create(
        site_id="site-a",
        content_type="article",
        slug="hello",
        title="Hello",
        definition=content_type,
        schema_version=1,
        values={"title": "Hello"},
    )
    record.update_values({"title": "Updated"}, expected_version=1, actor_ref="user:test")
    record.refresh_from_db()
    assert record.version == 2
    assert record.values == {"title": "Updated"}
    with pytest.raises(ValidationError, match="content_version_conflict"):
        record.update_values({"title": "Stale"}, expected_version=1, actor_ref="user:test")
    version = ContentRecordVersion.objects.get(record=record, version=1)
    assert version.snapshot_sha256 and len(version.snapshot_sha256) == 64


def test_record_workflow_soft_delete_and_restore_append_history():
    content_type = definition(status="published")
    workflow = WorkflowDefinition.objects.create(
        definition=content_type,
        states=["draft", "in_review", "published", "archived", "deleted"],
        initial_state="draft",
        transitions=[
            {
                "action": "submit_review",
                "from": ["draft"],
                "to": "in_review",
                "permission": "content.review",
            },
            {
                "action": "publish",
                "from": ["in_review"],
                "to": "published",
                "permission": "content.publish",
            },
            {
                "action": "archive",
                "from": ["published"],
                "to": "archived",
                "permission": "content.archive",
            },
            {
                "action": "delete",
                "from": ["archived"],
                "to": "deleted",
                "permission": "content.delete",
            },
        ],
    )
    workflow.full_clean()
    record = ContentRecord.objects.create(
        site_id="site-a",
        content_type="article",
        slug="workflow",
        title="Workflow",
        definition=content_type,
        values={"title": "First"},
    )
    record.transition_action("submit_review", expected_version=1, actor_ref="user:reviewer")
    record.transition_action("publish", expected_version=2, actor_ref="user:publisher")
    record.update_values({"title": "Second"}, expected_version=3, actor_ref="user:editor")
    restored = record.restore_version(1, expected_version=4, actor_ref="user:editor")
    assert restored.version == 5
    assert restored.values == {"title": "First"}
    record.transition_action("archive", expected_version=5, actor_ref="user:publisher")
    record.soft_delete(expected_version=6, actor_ref="user:admin")
    record.refresh_from_db()
    assert record.state == "deleted"
    assert record.deleted_at is not None
    assert ContentRecordVersion.objects.filter(record=record).count() == 6


def test_relationship_scope_cardinality_and_soft_deleted_target_are_enforced():
    content_type = definition(status="published")
    source = ContentRecord.objects.create(
        site_id="site-a",
        content_type="article",
        slug="source",
        title="Source",
        definition=content_type,
    )
    target = ContentRecord.objects.create(
        site_id="site-a",
        content_type="article",
        slug="target",
        title="Target",
        definition=content_type,
    )
    relation = ContentRelationship(
        site_id="site-a",
        source=source,
        target=target,
        field_key="related",
        order=0,
        deletion_policy="restrict",
    )
    relation.full_clean()
    cross_site = ContentRecord.objects.create(
        site_id="site-b",
        content_type="article",
        slug="foreign",
        title="Foreign",
        definition=definition(site_id="site-b", status="published"),
    )
    relation.target = cross_site
    with pytest.raises(ValidationError, match="relationship_scope_invalid"):
        relation.full_clean()


def test_saved_views_are_private_by_default_and_queries_are_closed():
    content_type = definition(status="published")
    view = SavedView(
        site_id="site-a",
        definition=content_type,
        owner_ref="user:test",
        title="Recent",
        query={"filters": [{"field": "title", "operator": "contains", "value": "safe"}]},
    )
    view.full_clean()
    assert view.visibility == "private"
    view.query = {"sql": "select * from secrets"}
    with pytest.raises(ValidationError, match="saved_view_query_invalid"):
        view.full_clean()


def test_asset_bindings_require_matching_site_and_accessible_image_metadata(media_asset):
    content_type = definition(status="published")
    record = ContentRecord.objects.create(
        site_id="site-a",
        content_type="article",
        slug="asset",
        title="Asset",
        definition=content_type,
    )
    binding = AssetBinding(
        site_id="site-a",
        record=record,
        asset=media_asset,
        field_key="hero",
        alt_text="A synthetic test image",
        order=0,
    )
    binding.full_clean()
    binding.alt_text = ""
    with pytest.raises(ValidationError, match="asset_alt_text_required"):
        binding.full_clean()


@pytest.fixture
def media_asset():
    from sitecontent.models import MediaAsset

    return MediaAsset.objects.create(
        site_id="site-a",
        storage_key="sha256/aa/test.png",
        original_name="test.png",
        media_type="image/png",
        byte_size=32,
        sha256="a" * 64,
        status="validated",
        owner_ref="user:test",
    )


def test_job_idempotency_binds_request_digest_and_terminal_state():
    content_type = definition(status="published")
    imported = ImportJob.objects.create(
        site_id="site-a",
        definition=content_type,
        requester_ref="user:test",
        source_sha256="b" * 64,
        request_digest="c" * 64,
        idempotency_key="import-001",
        schema_version=1,
    )
    exported = ExportJob.objects.create(
        site_id="site-a",
        definition=content_type,
        requester_ref="user:test",
        request_digest="d" * 64,
        idempotency_key="export-001",
        schema_version=1,
        expires_at=timezone.now() + timedelta(hours=1),
    )
    assert imported.status == "uploaded"
    assert exported.status == "queued"
    with pytest.raises(IntegrityError), transaction.atomic():
        ImportJob.objects.create(
            site_id="site-a",
            definition=content_type,
            requester_ref="user:test",
            source_sha256="e" * 64,
            request_digest="f" * 64,
            idempotency_key="import-001",
            schema_version=1,
        )


def test_workspace_audit_metadata_rejects_sensitive_keys():
    event = WorkspaceAuditEvent(
        site_id="site-a",
        actor_ref="user:test",
        object_type="content_record",
        object_ref="record:test",
        action="content.create",
        outcome="accepted",
        metadata={"count": 1, "sha256": "a" * 64},
    )
    event.full_clean()
    event.metadata = {"token": "not-allowed"}
    with pytest.raises(ValidationError, match="audit_metadata_key_invalid"):
        event.full_clean()
