from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from sitecontent.models import (
    MediaAsset,
    MediaCollection,
    MediaCollectionMembership,
    MediaJob,
    MediaMetadataRevision,
    MediaObjectVersion,
    MediaRetentionHold,
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
        site_id="site-a", asset=value, version=1, storage_key="opaque",
        sha256="a" * 64, byte_size=8, detected_type="image/png",
    )
    version.full_clean()
    version.site_id = "site-b"
    with pytest.raises(ValidationError, match="media_object_scope_invalid"):
        version.full_clean()

    metadata = MediaMetadataRevision(
        site_id="site-a", asset=value, revision=1, locale="en", alt_text="",
        decorative=False, actor_ref="user:test",
    )
    with pytest.raises(ValidationError, match="media_alt_or_decorative_required"):
        metadata.full_clean()
    metadata.decorative = True
    metadata.full_clean()

    variant = MediaVariant(
        asset=value, name="audio", storage_key="opaque-preview", media_type="audio/mpeg",
        byte_size=8, sha256="b" * 64, source_sha256="a" * 64, inline_safe=True,
    )
    with pytest.raises(ValidationError, match="media_inline_type_invalid"):
        variant.full_clean()


def test_upload_collection_job_and_hold_contracts_fail_closed():
    value = asset()
    upload = MediaUploadSession(
        site_id="site-a", actor_ref="user:test", idempotency_key="request-1",
        expected_sha256="a" * 64, expected_bytes=8, received_bytes=9,
        expires_at=timezone.now() + timedelta(minutes=5),
    )
    with pytest.raises(ValidationError, match="media_upload_length_invalid"):
        upload.full_clean()

    collection = MediaCollection(
        site_id="site-a", title="Private", owner_ref="user:test",
        visibility="private", shared_roles=["viewer"],
    )
    with pytest.raises(ValidationError, match="media_collection_roles_invalid"):
        collection.full_clean()
    collection.shared_roles = []
    collection.full_clean()

    other = MediaCollection.objects.create(
        site_id="site-b", title="Other", owner_ref="user:test",
    )
    membership = MediaCollectionMembership(site_id="site-a", collection=other, asset=value)
    with pytest.raises(ValidationError, match="media_collection_scope_invalid"):
        membership.full_clean()

    job = MediaJob(
        site_id="site-a", asset=value, kind="inspect", idempotency_key="job-1",
        request_digest="c" * 64, attempt=4, maximum_attempts=3,
    )
    with pytest.raises(ValidationError, match="media_job_attempt_invalid"):
        job.full_clean()

    hold = MediaRetentionHold(
        site_id="site-a", asset=value, reason_code="unsafe value", owner_ref="user:test",
    )
    with pytest.raises(ValidationError, match="media_hold_reason_invalid"):
        hold.full_clean()


def test_deleted_legacy_asset_cannot_return_to_quarantine():
    value = asset()
    value.status = MediaAsset.Status.DELETED
    value.save(update_fields=["status"])
    with pytest.raises(ValidationError, match="Deleted media"):
        value.quarantine("scanner_retry")
