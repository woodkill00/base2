from __future__ import annotations

import uuid

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.utils import timezone

SITE_ID_PATTERN = r"^[a-z][a-z0-9-]{2,62}$"
SHA256_PATTERN = r"^[a-f0-9]{64}$"
site_id_validator = RegexValidator(SITE_ID_PATTERN, "Enter a canonical site identifier.")
sha256_validator = RegexValidator(SHA256_PATTERN, "Enter a lowercase SHA-256 digest.")


def validate_local_path(value: str) -> None:
    if not value.startswith("/") or value.startswith("//") or "\\" in value or "?" in value or "#" in value:
        raise ValidationError("Path must be a canonical local path without query or fragment.")
    if ".." in value.split("/"):
        raise ValidationError("Path traversal is forbidden.")


class SiteOwnedModel(models.Model):
    site_id = models.CharField(max_length=63, validators=[site_id_validator], db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class ContentRecord(SiteOwnedModel):
    class State(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        SCHEDULED = "scheduled", "Scheduled"
        ARCHIVED = "archived", "Archived"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    content_type = models.SlugField(max_length=64)
    slug = models.SlugField(max_length=160)
    title = models.CharField(max_length=240)
    excerpt = models.TextField(blank=True, default="")
    body = models.TextField(blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    state = models.CharField(max_length=16, choices=State.choices, default=State.DRAFT)
    publish_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    sitemap_include = models.BooleanField(default=True)
    search_visible = models.BooleanField(default=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["site_id", "content_type", "slug"], name="sitecontent_record_slug_uq"),
        ]
        indexes = [
            models.Index(fields=["site_id", "state", "publish_at"], name="sitecontent_publish_idx"),
            models.Index(fields=["site_id", "content_type", "updated_at"], name="sitecontent_type_idx"),
        ]

    ALLOWED_TRANSITIONS = {
        State.DRAFT: {State.PUBLISHED, State.SCHEDULED, State.ARCHIVED},
        State.SCHEDULED: {State.DRAFT, State.PUBLISHED, State.ARCHIVED},
        State.PUBLISHED: {State.DRAFT, State.ARCHIVED},
        State.ARCHIVED: {State.DRAFT},
    }

    def clean(self) -> None:
        super().clean()
        if self.state == self.State.SCHEDULED:
            if self.publish_at is None or self.publish_at <= timezone.now():
                raise ValidationError({"publish_at": "Scheduled content requires a future publication time."})

    def create_revision(self, actor_ref: str = "") -> "ContentRevision":
        if self._state.adding:
            raise ValidationError("Content must be saved before creating a revision.")
        revision = (self.revisions.order_by("-revision").values_list("revision", flat=True).first() or 0) + 1
        return ContentRevision.objects.create(
            content=self,
            revision=revision,
            actor_ref=actor_ref,
            snapshot={
                "title": self.title,
                "excerpt": self.excerpt,
                "body": self.body,
                "metadata": self.metadata,
                "state": self.state,
                "publishAt": self.publish_at.isoformat() if self.publish_at else None,
                "sitemapInclude": self.sitemap_include,
                "searchVisible": self.search_visible,
                "version": self.version,
            },
        )

    def transition_to(self, state: str, *, actor_ref: str = "", publish_at=None) -> "ContentRevision | None":
        if state == self.state:
            return None
        if state not in self.ALLOWED_TRANSITIONS.get(self.state, set()):
            raise ValidationError({"state": f"Transition from {self.state} to {state} is not allowed."})
        revision = self.create_revision(actor_ref=actor_ref)
        self.state = state
        self.publish_at = publish_at if state == self.State.SCHEDULED else None
        self.published_at = timezone.now() if state == self.State.PUBLISHED else self.published_at
        self.version += 1
        self.full_clean()
        self.save(update_fields=["state", "publish_at", "published_at", "version", "updated_at"])
        return revision


class ContentRevision(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    content = models.ForeignKey(ContentRecord, on_delete=models.CASCADE, related_name="revisions")
    revision = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    snapshot = models.JSONField(default=dict)
    actor_ref = models.CharField(max_length=200, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["content", "revision"], name="sitecontent_revision_uq"),
        ]
        ordering = ["content_id", "revision"]


class RedirectRule(SiteOwnedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source_path = models.CharField(max_length=500, validators=[validate_local_path])
    target_path = models.CharField(max_length=500, validators=[validate_local_path])
    status_code = models.PositiveSmallIntegerField(choices=((301, "Permanent"), (302, "Temporary")), default=301)
    active = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["site_id", "source_path"], name="sitecontent_redirect_uq")]


class MediaAsset(SiteOwnedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        VALIDATED = "validated", "Validated"
        QUARANTINED = "quarantined", "Quarantined"
        DELETED = "deleted", "Deleted"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    storage_key = models.CharField(max_length=500)
    original_name = models.CharField(max_length=255)
    media_type = models.CharField(max_length=127)
    byte_size = models.PositiveBigIntegerField(validators=[MinValueValidator(1)])
    sha256 = models.CharField(max_length=64, validators=[sha256_validator])
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    owner_ref = models.CharField(max_length=200)
    attribution = models.TextField(blank=True, default="")
    retention_until = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["site_id", "storage_key"], name="sitecontent_media_key_uq")]
        indexes = [models.Index(fields=["site_id", "status", "created_at"], name="sitecontent_media_idx")]


class MediaVariant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asset = models.ForeignKey(MediaAsset, on_delete=models.CASCADE, related_name="variants")
    name = models.SlugField(max_length=64)
    storage_key = models.CharField(max_length=500)
    media_type = models.CharField(max_length=127)
    byte_size = models.PositiveBigIntegerField(validators=[MinValueValidator(1)])
    sha256 = models.CharField(max_length=64, validators=[sha256_validator])
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["asset", "name"], name="sitecontent_variant_uq")]


class FormSubmission(SiteOwnedModel):
    class Status(models.TextChoices):
        RECEIVED = "received", "Received"
        VALIDATED = "validated", "Validated"
        QUEUED = "queued", "Queued"
        DELIVERED = "delivered", "Delivered"
        REJECTED = "rejected", "Rejected"
        EXPIRED = "expired", "Expired"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    form_key = models.SlugField(max_length=100)
    replay_key = models.CharField(max_length=128)
    request_digest = models.CharField(max_length=64, validators=[sha256_validator])
    payload = models.JSONField(default=dict)
    consent = models.JSONField(default=dict, blank=True)
    request_id = models.CharField(max_length=128, blank=True, default="")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.RECEIVED)
    retained_until = models.DateTimeField()
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["site_id", "form_key", "replay_key"], name="sitecontent_form_replay_uq")
        ]
        indexes = [models.Index(fields=["site_id", "status", "retained_until"], name="sitecontent_form_idx")]

    def clean(self) -> None:
        super().clean()
        if self.retained_until <= timezone.now():
            raise ValidationError({"retained_until": "Retention expiry must be in the future."})


class FormDeliveryOutbox(models.Model):
    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        DELIVERED = "delivered", "Delivered"
        DEAD_LETTER = "dead_letter", "Dead letter"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    submission = models.OneToOneField(FormSubmission, on_delete=models.CASCADE, related_name="delivery")
    adapter = models.SlugField(max_length=64, default="disabled")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.QUEUED)
    attempts = models.PositiveSmallIntegerField(default=0)
    next_attempt_at = models.DateTimeField(default=timezone.now)
    last_error_code = models.CharField(max_length=64, blank=True, default="")
    delivered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["status", "next_attempt_at"], name="sitecontent_outbox_idx")]


class SearchDocument(SiteOwnedModel):
    class Visibility(models.TextChoices):
        PUBLIC = "public", "Public"
        PRIVATE = "private", "Private"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    content = models.OneToOneField(ContentRecord, on_delete=models.CASCADE, related_name="search_document")
    title = models.CharField(max_length=240)
    body = models.TextField()
    url_path = models.CharField(max_length=500, validators=[validate_local_path])
    visibility = models.CharField(max_length=16, choices=Visibility.choices, default=Visibility.PUBLIC)
    source_updated_at = models.DateTimeField()
    indexed_at = models.DateTimeField(auto_now_add=True)
    tombstoned_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["site_id", "visibility", "tombstoned_at"], name="sitecontent_search_idx")]

    def clean(self) -> None:
        super().clean()
        if self.content_id and self.site_id != self.content.site_id:
            raise ValidationError({"site_id": "Search document and content must belong to the same site."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
