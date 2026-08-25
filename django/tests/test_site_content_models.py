from __future__ import annotations

from datetime import timedelta

import pytest
from django.contrib import admin
from django.core.management import call_command
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from sitecontent.models import (
    ContentRecord,
    ContentRevision,
    FormSubmission,
    MediaAsset,
    MediaVariant,
    RedirectRule,
    SearchDocument,
)


pytestmark = pytest.mark.django_db


def test_content_lifecycle_revision_and_tenant_slug_contract():
    first = ContentRecord.objects.create(site_id="site-a", content_type="page", slug="about", title="About")
    second = ContentRecord.objects.create(site_id="site-b", content_type="page", slug="about", title="About B")
    assert first.pk != second.pk
    with pytest.raises(IntegrityError), transaction.atomic():
        ContentRecord.objects.create(site_id="site-a", content_type="page", slug="about", title="Duplicate")

    revision = ContentRevision.objects.create(
        content=first,
        revision=1,
        snapshot={"title": first.title, "state": first.state},
        actor_ref="operator:test",
    )
    assert revision.content_id == first.id
    with pytest.raises(IntegrityError), transaction.atomic():
        ContentRevision.objects.create(content=first, revision=1, snapshot={})

    lifecycle_revision = first.transition_to("published", actor_ref="operator:test")
    first.refresh_from_db()
    assert lifecycle_revision.snapshot["state"] == "draft"
    assert first.state == "published"
    assert first.published_at is not None
    assert first.version == 2
    first.transition_to("archived")
    with pytest.raises(ValidationError):
        first.transition_to("published")


def test_scheduled_content_requires_a_future_publication_time():
    record = ContentRecord(site_id="site-a", content_type="page", slug="news", title="News", state="scheduled")
    with pytest.raises(ValidationError):
        record.full_clean()
    record.publish_at = timezone.now() + timedelta(hours=1)
    record.full_clean()


def test_redirect_paths_are_local_and_tenant_scoped():
    RedirectRule.objects.create(site_id="site-a", source_path="/old", target_path="/new")
    RedirectRule.objects.create(site_id="site-b", source_path="/old", target_path="/elsewhere")
    with pytest.raises(ValidationError):
        RedirectRule(site_id="site-a", source_path="https://hostile.example", target_path="/safe").full_clean()


def test_media_integrity_variants_and_quarantine_contract():
    asset = MediaAsset.objects.create(
        site_id="site-a",
        storage_key="sha256/aa/example.png",
        original_name="example.png",
        media_type="image/png",
        byte_size=128,
        sha256="a" * 64,
        status="validated",
        owner_ref="content:test",
    )
    variant = MediaVariant.objects.create(
        asset=asset,
        name="small",
        storage_key="sha256/aa/example-small.webp",
        media_type="image/webp",
        byte_size=64,
        sha256="b" * 64,
        width=320,
        height=180,
    )
    assert variant.asset_id == asset.id
    with pytest.raises(ValidationError):
        MediaAsset(
            site_id="site-a",
            storage_key="bad",
            original_name="bad.exe",
            media_type="application/octet-stream",
            byte_size=0,
            sha256="short",
        ).full_clean()


def test_form_replay_retention_and_search_publication_contract():
    retained_until = timezone.now() + timedelta(days=30)
    FormSubmission.objects.create(
        site_id="site-a",
        form_key="contact",
        replay_key="request-1",
        payload={"message": "hello"},
        consent={"essential": True},
        request_id="req-1",
        retained_until=retained_until,
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        FormSubmission.objects.create(
            site_id="site-a",
            form_key="contact",
            replay_key="request-1",
            payload={},
            retained_until=retained_until,
        )

    content = ContentRecord.objects.create(
        site_id="site-a", content_type="page", slug="public", title="Public", state="published"
    )
    SearchDocument.objects.create(
        site_id="site-a",
        content=content,
        title=content.title,
        body="Searchable text",
        url_path="/public",
        visibility="public",
        source_updated_at=content.updated_at,
    )
    with pytest.raises(ValidationError):
        SearchDocument.objects.create(
            site_id="site-b",
            content=content,
            title="Cross tenant",
            body="forbidden",
            url_path="/forbidden",
            visibility="public",
            source_updated_at=content.updated_at,
        )


def test_admin_registration_and_migrations_are_current():
    for model in (
        ContentRecord,
        ContentRevision,
        FormSubmission,
        MediaAsset,
        MediaVariant,
        RedirectRule,
        SearchDocument,
    ):
        assert admin.site.is_registered(model)
    call_command("makemigrations", "sitecontent", check=True, dry_run=True, verbosity=0)
