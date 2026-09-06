from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from sitecontent.models import (
    MediaAsset,
    MediaAuditEvent,
    MediaCollection,
    MediaCollectionMembership,
    MediaDeliveryGrant,
    MediaDerivativeRecipe,
    MediaExportPackage,
    MediaInspectionResult,
    MediaJob,
    MediaMetadataRevision,
    MediaObjectVersion,
    MediaOutboxEvent,
    MediaPurgePlan,
    MediaReference,
    MediaRetentionHold,
    MediaUploadPart,
    MediaUploadSession,
    MediaVariant,
)

pytestmark = pytest.mark.django_db


def asset(*, site_id="site-a", media_type="image/png"):
    return MediaAsset.objects.create(
        site_id=site_id,
        storage_key=f"media/{site_id}/opaque.bin",
        original_name="safe.png",
        media_type=media_type,
        byte_size=8,
        sha256="a" * 64,
        status=MediaAsset.Status.QUARANTINED,
        owner_ref="user:test",
    )


def test_object_versions_metadata_and_variants_require_safe_scope_and_shape():
    value = asset()
    version = MediaObjectVersion(
        site_id="site-a",
        asset=value,
        version=1,
        storage_key="opaque",
        sha256="a" * 64,
        byte_size=8,
        detected_type="image/png",
    )
    version.full_clean()
    version.site_id = "site-b"
    with pytest.raises(ValidationError, match="media_object_scope_invalid"):
        version.full_clean()

    metadata = MediaMetadataRevision(
        site_id="site-a",
        asset=value,
        revision=1,
        locale="en",
        alt_text="",
        decorative=False,
        actor_ref="user:test",
    )
    with pytest.raises(ValidationError, match="media_alt_or_decorative_required"):
        metadata.full_clean()
    metadata.decorative = True
    metadata.full_clean()

    variant = MediaVariant(
        asset=value,
        name="audio",
        storage_key="opaque-preview",
        media_type="audio/mpeg",
        byte_size=8,
        sha256="b" * 64,
        source_sha256="a" * 64,
        inline_safe=True,
    )
    with pytest.raises(ValidationError, match="media_inline_type_invalid"):
        variant.full_clean()


def test_upload_collection_job_and_hold_contracts_fail_closed():
    value = asset()
    upload = MediaUploadSession(
        site_id="site-a",
        actor_ref="user:test",
        idempotency_key="request-1",
        expected_sha256="a" * 64,
        expected_bytes=8,
        received_bytes=9,
        expires_at=timezone.now() + timedelta(minutes=5),
    )
    with pytest.raises(ValidationError, match="media_upload_length_invalid"):
        upload.full_clean()

    collection = MediaCollection(
        site_id="site-a",
        title="Private",
        owner_ref="user:test",
        visibility="private",
        shared_roles=["viewer"],
    )
    with pytest.raises(ValidationError, match="media_collection_roles_invalid"):
        collection.full_clean()
    collection.shared_roles = []
    collection.full_clean()

    other = MediaCollection.objects.create(
        site_id="site-b",
        title="Other",
        owner_ref="user:test",
    )
    membership = MediaCollectionMembership(site_id="site-a", collection=other, asset=value)
    with pytest.raises(ValidationError, match="media_collection_scope_invalid"):
        membership.full_clean()

    job = MediaJob(
        site_id="site-a",
        asset=value,
        kind="inspect",
        idempotency_key="job-1",
        request_digest="c" * 64,
        attempt=4,
        maximum_attempts=3,
    )
    with pytest.raises(ValidationError, match="media_job_attempt_invalid"):
        job.full_clean()

    hold = MediaRetentionHold(
        site_id="site-a",
        asset=value,
        reason_code="unsafe value",
        owner_ref="user:test",
    )
    with pytest.raises(ValidationError, match="media_hold_reason_invalid"):
        hold.full_clean()


def test_deleted_legacy_asset_cannot_return_to_quarantine():
    value = asset()
    value.status = MediaAsset.Status.DELETED
    value.save(update_fields=["status"])
    with pytest.raises(ValidationError, match="Deleted media"):
        value.quarantine("scanner_retry")


def test_processing_records_are_tenant_scoped_bounded_and_safe():
    value = asset()
    session = MediaUploadSession.objects.create(
        site_id="site-a",
        actor_ref="user:test",
        idempotency_key="request-processing",
        expected_sha256="a" * 64,
        expected_bytes=8,
        expires_at=timezone.now() + timedelta(minutes=5),
    )
    part = MediaUploadPart(
        site_id="site-b",
        session=session,
        part_number=1,
        byte_size=8,
        sha256="a" * 64,
        storage_key="opaque-part",
        completed_at=timezone.now(),
    )
    with pytest.raises(ValidationError, match="media_upload_part_scope_invalid"):
        part.full_clean()

    object_version = MediaObjectVersion.objects.create(
        site_id="site-a",
        asset=value,
        version=1,
        storage_key="opaque-version",
        sha256="a" * 64,
        byte_size=8,
        detected_type="image/png",
    )
    inspection = MediaInspectionResult(
        site_id="site-a",
        object_version=object_version,
        attempt=1,
        decision="accepted",
        safe_code="unsafe raw detail",
        scanner_ref="clamav:1.4",
        decoder_ref="pillow:11",
        definitions_at=timezone.now(),
        observed_media_type="image/png",
        measurements={"pixels": 64},
        result_sha256="b" * 64,
    )
    with pytest.raises(ValidationError, match="media_inspection_code_invalid"):
        inspection.full_clean()

    recipe = MediaDerivativeRecipe(
        recipe_id="thumbnail",
        version=1,
        output_media_type="image/webp",
        processor_ref="pillow:11",
        parameters={"noUpscale": False, "stripMetadata": True},
        recipe_sha256="c" * 64,
    )
    with pytest.raises(ValidationError, match="media_recipe_upscale_policy_invalid"):
        recipe.full_clean()

    purge = MediaPurgePlan(
        site_id="site-a",
        asset=value,
        requested_by="user:test",
        reason_code="retention_expired",
        expected_version=1,
        object_manifest=[],
        reference_preview=[],
        status="scheduled",
    )
    with pytest.raises(ValidationError, match="media_purge_schedule_invalid"):
        purge.full_clean()


def test_reference_grant_export_audit_and_outbox_contracts_fail_closed():
    value = asset()
    reference = MediaReference(
        site_id="site-a",
        asset=value,
        owner_type="record",
        owner_id=value.id,
        field_key="hero",
        owner_state="published",
        owner_visibility="public",
        required=True,
    )
    with pytest.raises(ValidationError, match="media_reference_visibility_invalid"):
        reference.full_clean()

    grant = MediaDeliveryGrant(
        site_id="site-b",
        asset=value,
        object_version=1,
        method="GET",
        audience_ref="user:test",
        token_digest="d" * 64,
        expires_at=timezone.now() + timedelta(minutes=5),
    )
    with pytest.raises(ValidationError, match="media_grant_scope_invalid"):
        grant.full_clean()

    export = MediaExportPackage(
        site_id="site-a",
        requested_by="user:test",
        output_format="json",
        projection=[],
        status="ready",
        request_digest="e" * 64,
        expires_at=timezone.now() + timedelta(minutes=5),
    )
    with pytest.raises(ValidationError, match="media_export_artifact_missing"):
        export.full_clean()

    event = MediaAuditEvent.objects.create(
        site_id="site-a",
        sequence=1,
        event_type="media.asset.read",
        actor_ref="user:test",
        subject_ref=f"asset:{value.id}",
        detail={"status": "ready"},
        previous_hash="0" * 64,
        event_hash="f" * 64,
    )
    event.detail = {"status": "changed"}
    with pytest.raises(ValidationError, match="media_audit_immutable"):
        event.save()
    with pytest.raises(ValidationError, match="media_audit_immutable"):
        event.delete()

    outbox = MediaOutboxEvent(
        site_id="site-a",
        aggregate_ref=f"asset:{value.id}",
        event_kind="storage.delete",
        idempotency_key="delete-1",
        payload_digest="a" * 64,
        attempt=6,
        maximum_attempts=5,
    )
    with pytest.raises(ValidationError, match="media_outbox_attempt_invalid"):
        outbox.full_clean()
