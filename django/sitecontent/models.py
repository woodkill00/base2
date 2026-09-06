from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.core.exceptions import ValidationError
from django.core.validators import (
    EmailValidator,
    MaxValueValidator,
    MinValueValidator,
    RegexValidator,
    URLValidator,
)
from django.db import models, transaction
from django.utils import timezone

from common.models import content_identifier_validator, validate_closed_mapping

SITE_ID_PATTERN = r"^[a-z][a-z0-9-]{2,62}$"
SHA256_PATTERN = r"^[a-f0-9]{64}$"
site_id_validator = RegexValidator(SITE_ID_PATTERN, "Enter a canonical site identifier.")
sha256_validator = RegexValidator(SHA256_PATTERN, "Enter a lowercase SHA-256 digest.")
email_validator = EmailValidator()
url_validator = URLValidator(schemes=["http", "https"])

RICH_TEXT_NODE_TYPES = {
    "document",
    "paragraph",
    "heading",
    "text",
    "bullet_list",
    "ordered_list",
    "list_item",
    "blockquote",
    "code_block",
    "hard_break",
    "link",
}
RICH_TEXT_KEYS = {"type", "text", "children", "level", "href"}


def validate_structured_rich_text(value, *, depth: int = 0) -> None:
    """Validate a bounded document tree with no HTML or executable attributes."""
    if depth > 8 or not isinstance(value, dict) or set(value) - RICH_TEXT_KEYS:
        raise ValidationError("rich_text_invalid")
    node_type = value.get("type")
    if node_type not in RICH_TEXT_NODE_TYPES:
        raise ValidationError("rich_text_invalid")
    text = value.get("text")
    if text is not None and (not isinstance(text, str) or len(text) > 20_000):
        raise ValidationError("rich_text_invalid")
    href = value.get("href")
    if href is not None:
        try:
            url_validator(href)
        except ValidationError as exc:
            raise ValidationError("rich_text_invalid") from exc
    children = value.get("children", [])
    if not isinstance(children, list) or len(children) > 256:
        raise ValidationError("rich_text_invalid")
    for child in children:
        validate_structured_rich_text(child, depth=depth + 1)


def validate_local_path(value: str) -> None:
    if (
        not value.startswith("/")
        or value.startswith("//")
        or "\\" in value
        or "?" in value
        or "#" in value
    ):
        raise ValidationError("Path must be a canonical local path without query or fragment.")
    if ".." in value.split("/"):
        raise ValidationError("Path traversal is forbidden.")


class SiteOwnedQuerySet(models.QuerySet):
    def for_tenant(self, tenant_id: str):
        if not re.fullmatch(SITE_ID_PATTERN, str(tenant_id or "")):
            raise ValidationError("tenant_invalid")
        return self.filter(site_id=tenant_id)


class SiteOwnedModel(models.Model):
    site_id = models.CharField(max_length=63, validators=[site_id_validator], db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    objects = SiteOwnedQuerySet.as_manager()

    class Meta:
        abstract = True


class ContentTypeDefinition(SiteOwnedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        MIGRATION_PENDING = "migration_pending", "Migration pending"
        PUBLISHED = "published", "Published"
        RETIRED = "retired", "Retired"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    type_key = models.CharField(max_length=63, validators=[content_identifier_validator])
    version = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True, default="")
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.DRAFT)
    preset_id = models.CharField(
        max_length=63, blank=True, default="", validators=[content_identifier_validator]
    )
    preset_version = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    compatibility = models.CharField(max_length=24, blank=True, default="additive")
    migration_digest = models.CharField(max_length=64, blank=True, default="")
    lock_version = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    created_by = models.CharField(max_length=200, blank=True, default="")
    updated_by = models.CharField(max_length=200, blank=True, default="")
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["site_id", "type_key", "version"], name="sitecontent_type_version_uq"
            ),
        ]
        indexes = [
            models.Index(
                fields=["site_id", "type_key", "status"], name="sitecontent_type_state_idx"
            ),
        ]

    def clean(self) -> None:
        super().clean()
        if self.preset_id == "":
            self.preset_id = "custom"
        if self.migration_digest and not re.fullmatch(SHA256_PATTERN, self.migration_digest):
            raise ValidationError({"migration_digest": "migration_digest_invalid"})
        if self.status == self.Status.PUBLISHED and self.published_at is None:
            self.published_at = timezone.now()

    def save(self, *args, **kwargs):
        if not self._state.adding:
            previous = (
                type(self).objects.filter(pk=self.pk).values_list("status", flat=True).first()
            )
            if previous == self.Status.PUBLISHED:
                raise ValidationError("published_definition_immutable")
        self.full_clean()
        return super().save(*args, **kwargs)

    def preview_compatibility(self, *, previous=None) -> dict:
        previous = previous or (
            type(self)
            .objects.filter(
                site_id=self.site_id,
                type_key=self.type_key,
                status=self.Status.PUBLISHED,
                version__lt=self.version,
            )
            .order_by("-version")
            .first()
        )
        current_fields = {field.field_key: field for field in self.fields.all()}
        previous_fields = (
            {field.field_key: field for field in previous.fields.all()} if previous else {}
        )
        removed = sorted(previous_fields.keys() - current_fields.keys())
        added = sorted(current_fields.keys() - previous_fields.keys())
        changed = sorted(
            key
            for key in current_fields.keys() & previous_fields.keys()
            if (
                current_fields[key].field_kind,
                current_fields[key].required,
                current_fields[key].nullable,
                current_fields[key].validation,
            )
            != (
                previous_fields[key].field_kind,
                previous_fields[key].required,
                previous_fields[key].nullable,
                previous_fields[key].validation,
            )
        )
        backfill = (
            sorted(
                key
                for key in added
                if current_fields[key].required and current_fields[key].default_value is None
            )
            if previous
            else []
        )
        classification = (
            "lossy" if removed or changed else "backfill_required" if backfill else "additive"
        )
        payload = {
            "classification": classification,
            "addedFields": added,
            "removedFields": removed,
            "changedFields": changed,
            "backfillFields": backfill,
        }
        payload["digest"] = _snapshot_digest(payload)
        return payload

    def publish(self, *, expected_lock_version: int, confirm_lossy: bool = False) -> dict:
        with transaction.atomic():
            current = type(self).objects.select_for_update().get(pk=self.pk)
            if current.lock_version != expected_lock_version:
                raise ValidationError("definition_version_conflict")
            preview = current.preview_compatibility()
            if preview["classification"] in {"lossy", "backfill_required"} and not confirm_lossy:
                raise ValidationError("lossy_confirmation_required")
            current.status = self.Status.PUBLISHED
            current.compatibility = preview["classification"]
            current.migration_digest = preview["digest"]
            current.published_at = timezone.now()
            current.lock_version += 1
            current.save()
            self.status = current.status
            self.compatibility = current.compatibility
            self.migration_digest = current.migration_digest
            self.published_at = current.published_at
            self.lock_version = current.lock_version
            return preview


class ContentFieldDefinition(models.Model):
    FIELD_KINDS = (
        "short_text",
        "long_text",
        "rich_text",
        "integer",
        "decimal",
        "boolean",
        "date",
        "datetime",
        "enum",
        "slug",
        "url",
        "email",
        "location",
        "reference",
        "references",
        "image",
        "file",
        "json_object",
    )
    VALIDATION_KEYS = {
        "minLength",
        "maxLength",
        "minimum",
        "maximum",
        "decimalPlaces",
        "choices",
        "maximumItems",
        "maximumDepth",
        "targetType",
        "deletionPolicy",
    }
    PRESENTATION_KEYS = {"renderer", "width", "helpText", "placeholder", "group"}
    RENDERERS = {
        "text",
        "textarea",
        "rich_text",
        "number",
        "toggle",
        "date",
        "datetime",
        "select",
        "location",
        "relationship",
        "image",
        "file",
        "json",
    }

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    definition = models.ForeignKey(
        ContentTypeDefinition, on_delete=models.CASCADE, related_name="fields"
    )
    field_key = models.CharField(max_length=63, validators=[content_identifier_validator])
    label = models.CharField(max_length=120)
    description = models.TextField(blank=True, default="")
    field_kind = models.CharField(max_length=24, choices=[(kind, kind) for kind in FIELD_KINDS])
    order = models.PositiveSmallIntegerField(default=0)
    required = models.BooleanField(default=False)
    nullable = models.BooleanField(default=False)
    default_value = models.JSONField(null=True, blank=True)
    validation = models.JSONField(default=dict, blank=True)
    presentation = models.JSONField(default=dict, blank=True)
    indexed = models.BooleanField(default=False)
    unique = models.BooleanField(default=False)
    read_permission = models.CharField(max_length=64, default="content.read")
    write_permission = models.CharField(max_length=64, default="content.write")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["definition", "field_key"], name="sitecontent_field_key_uq"
            ),
        ]
        ordering = ["definition_id", "order", "field_key"]

    def clean(self) -> None:  # noqa: C901 - closed schema validation dispatch
        super().clean()
        if self.field_kind not in self.FIELD_KINDS:
            raise ValidationError({"field_kind": "field_kind_invalid"})
        validate_closed_mapping(
            self.validation,
            allowed_keys=self.VALIDATION_KEYS,
            error_code="field_validation_key_invalid",
        )
        validate_closed_mapping(
            self.presentation,
            allowed_keys=self.PRESENTATION_KEYS,
            error_code="field_presentation_key_invalid",
        )
        renderer = self.presentation.get("renderer")
        if renderer and renderer not in self.RENDERERS:
            raise ValidationError({"presentation": "field_renderer_invalid"})
        if self.required and self.nullable:
            raise ValidationError({"nullable": "required_field_cannot_be_nullable"})
        minimum = self.validation.get("minimum")
        maximum = self.validation.get("maximum")
        if minimum is not None and maximum is not None:
            try:
                if Decimal(str(minimum)) > Decimal(str(maximum)):
                    raise ValidationError("field_validation_bound_invalid")
            except (InvalidOperation, ValueError):
                raise ValidationError("field_validation_bound_invalid") from None
        if "minLength" in self.validation or "maxLength" in self.validation:
            min_length = self.validation.get("minLength", 0)
            max_length = self.validation.get("maxLength", 20_000)
            if (
                not isinstance(min_length, int)
                or isinstance(min_length, bool)
                or not isinstance(max_length, int)
                or isinstance(max_length, bool)
                or min_length < 0
                or max_length > 20_000
                or min_length > max_length
            ):
                raise ValidationError("field_validation_bound_invalid")
        if "maximumItems" in self.validation:
            maximum_items = self.validation["maximumItems"]
            if (
                not isinstance(maximum_items, int)
                or isinstance(maximum_items, bool)
                or not 1 <= maximum_items <= 50
            ):
                raise ValidationError("field_validation_bound_invalid")
        if "maximumDepth" in self.validation:
            maximum_depth = self.validation["maximumDepth"]
            allowed_maximum = 2 if self.field_kind in {"reference", "references"} else 8
            if (
                not isinstance(maximum_depth, int)
                or isinstance(maximum_depth, bool)
                or not 1 <= maximum_depth <= allowed_maximum
            ):
                raise ValidationError("field_validation_bound_invalid")
        relationship_keys = {"targetType", "deletionPolicy"}
        if relationship_keys & set(self.validation):
            if self.field_kind not in {"reference", "references"}:
                raise ValidationError("field_relationship_invalid")
            target_type = self.validation.get("targetType")
            deletion_policy = self.validation.get("deletionPolicy", "restrict")
            maximum_depth = self.validation.get("maximumDepth", 2)
            if (
                not isinstance(target_type, str)
                or not re.fullmatch(r"[a-z][a-z0-9_]{1,62}", target_type)
                or deletion_policy not in {"restrict", "detach", "cascade_soft"}
                or not isinstance(maximum_depth, int)
                or isinstance(maximum_depth, bool)
                or not 1 <= maximum_depth <= 2
            ):
                raise ValidationError("field_relationship_invalid")
        if self.default_value is not None:
            self.validate_value(self.default_value)

    def save(self, *args, **kwargs):
        if self.definition_id:
            status_value = (
                ContentTypeDefinition.objects.filter(pk=self.definition_id)
                .values_list("status", flat=True)
                .first()
            )
            if status_value == ContentTypeDefinition.Status.PUBLISHED:
                raise ValidationError("published_definition_immutable")
        self.full_clean()
        return super().save(*args, **kwargs)

    def validate_value(self, value) -> None:  # noqa: C901 - closed field-kind dispatch
        if value is None:
            if self.required and not self.nullable:
                raise ValidationError({self.field_key: "required_value_missing"})
            return
        kind = self.field_kind
        if kind in {"short_text", "long_text", "slug", "url", "email", "enum"}:
            if not isinstance(value, str):
                raise ValidationError({self.field_key: "field_value_type_invalid"})
            maximum = int(self.validation.get("maxLength", 20_000 if kind == "long_text" else 500))
            minimum = int(self.validation.get("minLength", 0))
            if not minimum <= len(value) <= maximum:
                raise ValidationError({self.field_key: "field_value_length_invalid"})
            if kind == "slug" and not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value):
                raise ValidationError({self.field_key: "field_value_slug_invalid"})
            if kind == "url":
                url_validator(value)
            if kind == "email":
                email_validator(value)
            if kind == "enum" and value not in self.validation.get("choices", []):
                raise ValidationError({self.field_key: "field_value_choice_invalid"})
        elif kind == "rich_text":
            validate_structured_rich_text(value)
        elif kind == "integer":
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValidationError({self.field_key: "field_value_type_invalid"})
        elif kind == "decimal":
            try:
                Decimal(str(value))
            except (InvalidOperation, ValueError):
                raise ValidationError({self.field_key: "field_value_type_invalid"}) from None
        elif kind == "boolean" and not isinstance(value, bool):
            raise ValidationError({self.field_key: "field_value_type_invalid"})
        elif kind == "date":
            try:
                date.fromisoformat(value) if isinstance(value, str) else value.isoformat()
            except (AttributeError, ValueError):
                raise ValidationError({self.field_key: "field_value_type_invalid"}) from None
        elif kind == "datetime":
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                if parsed.tzinfo is None:
                    raise ValueError
            except (AttributeError, ValueError):
                raise ValidationError({self.field_key: "field_value_type_invalid"}) from None
        elif kind in {"reference", "image", "file"}:
            try:
                uuid.UUID(str(value))
            except (TypeError, ValueError):
                raise ValidationError({self.field_key: "field_value_type_invalid"}) from None
        elif kind == "references":
            maximum_items = int(self.validation.get("maximumItems", 50))
            if not isinstance(value, list) or len(value) > maximum_items:
                raise ValidationError({self.field_key: "field_value_type_invalid"})
            for item in value:
                try:
                    uuid.UUID(str(item))
                except (TypeError, ValueError):
                    raise ValidationError({self.field_key: "field_value_type_invalid"}) from None
        elif kind in {"location", "json_object"} and not isinstance(value, dict):
            raise ValidationError({self.field_key: "field_value_type_invalid"})

        if kind in {"integer", "decimal"}:
            numeric = Decimal(str(value))
            if "minimum" in self.validation and numeric < Decimal(str(self.validation["minimum"])):
                raise ValidationError({self.field_key: "field_value_minimum_invalid"})
            if "maximum" in self.validation and numeric > Decimal(str(self.validation["maximum"])):
                raise ValidationError({self.field_key: "field_value_maximum_invalid"})


class WorkflowDefinition(models.Model):
    ALLOWED_STATES = {"draft", "in_review", "scheduled", "published", "archived", "deleted"}
    ALLOWED_ACTIONS = {
        "submit_review",
        "return_draft",
        "schedule",
        "publish",
        "archive",
        "restore",
        "delete",
    }
    TRANSITION_KEYS = {"action", "from", "to", "permission", "schedulable"}

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    definition = models.OneToOneField(
        ContentTypeDefinition, on_delete=models.CASCADE, related_name="workflow"
    )
    states = models.JSONField(default=list)
    initial_state = models.CharField(max_length=24, default="draft")
    transitions = models.JSONField(default=list)

    def clean(self) -> None:
        super().clean()
        if (
            not isinstance(self.states, list)
            or not self.states
            or len(self.states) > len(self.ALLOWED_STATES)
            or len(self.states) != len(set(self.states))
            or any(state not in self.ALLOWED_STATES for state in self.states)
            or self.initial_state not in self.states
        ):
            raise ValidationError({"states": "workflow_state_invalid"})
        if not isinstance(self.transitions, list) or len(self.transitions) > 32:
            raise ValidationError({"transitions": "workflow_transition_invalid"})
        action_sources: set[tuple[str, str]] = set()
        for item in self.transitions:
            if not isinstance(item, dict) or set(item) - self.TRANSITION_KEYS:
                raise ValidationError({"transitions": "workflow_transition_invalid"})
            sources = item.get("from")
            if (
                item.get("action") not in self.ALLOWED_ACTIONS
                or not isinstance(sources, list)
                or not sources
                or any(source not in self.states for source in sources)
                or item.get("to") not in self.states
                or not re.fullmatch(r"content\.[a-z_]{2,48}", str(item.get("permission", "")))
            ):
                raise ValidationError({"transitions": "workflow_state_invalid"})
            action = item["action"]
            schedulable = item.get("schedulable", False)
            if not isinstance(schedulable, bool) or (
                (action == "schedule" or item["to"] == "scheduled") != schedulable
            ):
                raise ValidationError({"transitions": "workflow_schedule_invalid"})
            for source in sources:
                key = (source, action)
                if key in action_sources:
                    raise ValidationError({"transitions": "workflow_transition_conflict"})
                action_sources.add(key)


class ContentRecord(SiteOwnedModel):
    class State(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        SCHEDULED = "scheduled", "Scheduled"
        ARCHIVED = "archived", "Archived"
        IN_REVIEW = "in_review", "In review"
        DELETED = "deleted", "Deleted"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    content_type = models.SlugField(max_length=64)
    slug = models.SlugField(max_length=160)
    title = models.CharField(max_length=240)
    excerpt = models.TextField(blank=True, default="")
    body = models.TextField(blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    state = models.CharField(max_length=16, choices=State.choices, default=State.DRAFT)
    publish_at = models.DateTimeField(null=True, blank=True)
    schedule_timezone = models.CharField(max_length=64, blank=True, default="")
    published_at = models.DateTimeField(null=True, blank=True)
    sitemap_include = models.BooleanField(default=True)
    search_visible = models.BooleanField(default=True)
    version = models.PositiveIntegerField(default=1)
    definition = models.ForeignKey(
        ContentTypeDefinition,
        on_delete=models.PROTECT,
        related_name="records",
        null=True,
        blank=True,
    )
    schema_version = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    values = models.JSONField(default=dict, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["site_id", "content_type", "slug"], name="sitecontent_record_slug_uq"
            ),
        ]
        indexes = [
            models.Index(fields=["site_id", "state", "publish_at"], name="sitecontent_publish_idx"),
            models.Index(
                fields=["site_id", "content_type", "updated_at"], name="sitecontent_type_idx"
            ),
        ]

    ALLOWED_TRANSITIONS = {
        State.DRAFT: {State.PUBLISHED, State.SCHEDULED, State.ARCHIVED},
        State.SCHEDULED: {State.DRAFT, State.PUBLISHED, State.ARCHIVED},
        State.PUBLISHED: {State.DRAFT, State.ARCHIVED},
        State.ARCHIVED: {State.DRAFT},
    }

    def clean(self) -> None:  # noqa: C901 - canonical record invariant aggregation
        super().clean()
        if self.definition_id:
            if (
                self.definition.site_id != self.site_id
                or self.definition.type_key != self.content_type
            ):
                raise ValidationError({"definition": "record_definition_scope_invalid"})
            if self.definition.status != ContentTypeDefinition.Status.PUBLISHED:
                raise ValidationError({"definition": "record_definition_not_published"})
            if self.schema_version != self.definition.version:
                raise ValidationError({"schema_version": "record_schema_version_invalid"})
        if not isinstance(self.values, dict) or len(self.values) > 128:
            raise ValidationError({"values": "record_values_invalid"})
        if self.definition_id:
            fields = list(self.definition.fields.all())
            declared = {field.field_key: field for field in fields}
            unknown = set(self.values) - set(declared)
            if unknown:
                raise ValidationError({"values": "record_unknown_field"})
            for field in fields:
                if field.field_key not in self.values:
                    if field.required and field.default_value is None:
                        raise ValidationError({field.field_key: "required_value_missing"})
                    continue
                field.validate_value(self.values[field.field_key])
        if self.state == self.State.SCHEDULED:
            if self.publish_at is None or self.publish_at <= timezone.now():
                raise ValidationError(
                    {"publish_at": "Scheduled content requires a future publication time."}
                )
            try:
                ZoneInfo(self.schedule_timezone)
            except (ZoneInfoNotFoundError, ValueError):
                raise ValidationError("schedule_timezone_invalid") from None
        elif self.schedule_timezone:
            raise ValidationError("schedule_timezone_without_schedule")

    def create_revision(self, actor_ref: str = "") -> ContentRevision:
        if self._state.adding:
            raise ValidationError("Content must be saved before creating a revision.")
        revision = (
            self.revisions.order_by("-revision").values_list("revision", flat=True).first() or 0
        ) + 1
        snapshot = {
            "title": self.title,
            "excerpt": self.excerpt,
            "body": self.body,
            "metadata": self.metadata,
            "values": self.values,
            "state": self.state,
            "publishAt": self.publish_at.isoformat() if self.publish_at else None,
            "scheduleTimezone": self.schedule_timezone or None,
            "sitemapInclude": self.sitemap_include,
            "searchVisible": self.search_visible,
            "version": self.version,
        }
        return ContentRevision.objects.create(
            content=self,
            revision=revision,
            actor_ref=actor_ref,
            snapshot=snapshot,
            snapshot_sha256=_snapshot_digest(snapshot),
            schema_version=self.schema_version,
            action="transition",
        )

    def transition_to(
        self, state: str, *, actor_ref: str = "", publish_at=None, timezone_name: str = ""
    ) -> ContentRevision | None:
        if state == self.state:
            return None
        if state not in self.ALLOWED_TRANSITIONS.get(self.state, set()):
            raise ValidationError(
                {"state": f"Transition from {self.state} to {state} is not allowed."}
            )
        revision = self.create_revision(actor_ref=actor_ref)
        self.state = state
        self.publish_at = publish_at if state == self.State.SCHEDULED else None
        self.schedule_timezone = timezone_name if state == self.State.SCHEDULED else ""
        self.published_at = timezone.now() if state == self.State.PUBLISHED else self.published_at
        self.version += 1
        self.full_clean()
        self.save(
            update_fields=[
                "state",
                "publish_at",
                "schedule_timezone",
                "published_at",
                "version",
                "updated_at",
            ]
        )
        return revision

    def update_values(self, values: dict, *, expected_version: int, actor_ref: str = "") -> None:
        if not isinstance(values, dict) or len(values) > 128:
            raise ValidationError({"values": "record_values_invalid"})
        with transaction.atomic():
            current = type(self).objects.select_for_update().get(pk=self.pk)
            if current.version != expected_version:
                raise ValidationError("content_version_conflict")
            ContentRecordVersion.objects.create(
                record=current,
                version=current.version,
                schema_version=current.schema_version,
                snapshot=current.values,
                snapshot_sha256=_snapshot_digest(current.values),
                actor_ref=actor_ref,
                action="update",
            )
            current.values = values
            current.version += 1
            current.full_clean()
            current.save(update_fields=["values", "version", "updated_at"])
            self.values = current.values
            self.version = current.version

    def transition_action(
        self,
        action: str,
        *,
        expected_version: int,
        actor_ref: str = "",
        publish_at=None,
        timezone_name: str = "",
    ) -> None:
        with transaction.atomic():
            # PostgreSQL rejects FOR UPDATE when an outer join reaches the
            # nullable definition relation. Lock only the record row, then
            # resolve the immutable definition inside the same transaction.
            current = type(self).objects.select_for_update().get(pk=self.pk)
            if current.version != expected_version:
                raise ValidationError("content_version_conflict")
            if not current.definition_id:
                raise ValidationError("record_definition_required")
            workflow = WorkflowDefinition.objects.filter(definition=current.definition).first()
            if workflow is None:
                raise ValidationError("workflow_unavailable")
            transition_spec = next(
                (
                    item
                    for item in workflow.transitions
                    if item.get("action") == action and current.state in item.get("from", [])
                ),
                None,
            )
            if transition_spec is None:
                raise ValidationError("content_transition_invalid")
            destination = transition_spec["to"]
            if destination == self.State.DELETED:
                current._apply_incoming_deletion_policies(actor_ref=actor_ref)
            ContentRecordVersion.objects.create(
                record=current,
                version=current.version,
                schema_version=current.schema_version,
                snapshot=current.values,
                snapshot_sha256=_snapshot_digest(current.values),
                actor_ref=actor_ref,
                action=action,
            )
            current.state = destination
            current.publish_at = publish_at if destination == self.State.SCHEDULED else None
            current.schedule_timezone = timezone_name if destination == self.State.SCHEDULED else ""
            if destination == self.State.PUBLISHED:
                current.published_at = timezone.now()
            if destination == self.State.DELETED:
                current.deleted_at = timezone.now()
            current.version += 1
            current.full_clean()
            current.save(
                update_fields=[
                    "state",
                    "publish_at",
                    "schedule_timezone",
                    "published_at",
                    "deleted_at",
                    "version",
                    "updated_at",
                ]
            )
            self.state = current.state
            self.version = current.version
            self.deleted_at = current.deleted_at

    def _apply_incoming_deletion_policies(
        self,
        *,
        actor_ref: str,
        visited: set[uuid.UUID] | None = None,
        depth: int = 0,
    ) -> None:
        visited = set(visited or ())
        if self.pk in visited or depth > 2:
            raise ValidationError("relationship_delete_depth_invalid")
        visited.add(self.pk)
        incoming = ContentRelationship.objects.select_for_update().filter(target=self)
        if incoming.filter(deletion_policy="restrict").exists():
            raise ValidationError("relationship_delete_restricted")
        incoming.filter(deletion_policy="detach").delete()
        cascading = list(
            incoming.filter(deletion_policy="cascade_soft")
            .select_related("source")
            .order_by("source_id")[:51]
        )
        if len(cascading) > 50:
            raise ValidationError("relationship_cardinality_invalid")
        for relationship in cascading:
            if depth >= relationship.maximum_depth:
                raise ValidationError("relationship_delete_depth_invalid")
            source = type(self).objects.select_for_update().get(pk=relationship.source_id)
            if source.state == self.State.DELETED:
                continue
            source._apply_incoming_deletion_policies(
                actor_ref=actor_ref,
                visited=visited,
                depth=depth + 1,
            )
            ContentRecordVersion.objects.create(
                record=source,
                version=source.version,
                schema_version=source.schema_version,
                snapshot=source.values,
                snapshot_sha256=_snapshot_digest(source.values),
                actor_ref=actor_ref,
                action="cascade_delete",
            )
            source.state = self.State.DELETED
            source.deleted_at = timezone.now()
            source.publish_at = None
            source.schedule_timezone = ""
            source.version += 1
            source.full_clean()
            source.save(
                update_fields=[
                    "state",
                    "deleted_at",
                    "publish_at",
                    "schedule_timezone",
                    "version",
                    "updated_at",
                ]
            )

    def restore_version(
        self, version: int, *, expected_version: int, actor_ref: str = ""
    ) -> ContentRecord:
        with transaction.atomic():
            current = type(self).objects.select_for_update().get(pk=self.pk)
            if current.version != expected_version:
                raise ValidationError("content_version_conflict")
            restored = ContentRecordVersion.objects.get(record=current, version=version)
            ContentRecordVersion.objects.create(
                record=current,
                version=current.version,
                schema_version=current.schema_version,
                snapshot=current.values,
                snapshot_sha256=_snapshot_digest(current.values),
                actor_ref=actor_ref,
                action="restore",
                restored_from_version=version,
            )
            snapshot = restored.snapshot
            current.values = snapshot.get("values", snapshot)
            current.version += 1
            current.full_clean()
            current.save(update_fields=["values", "version", "updated_at"])
            self.values = current.values
            self.version = current.version
            return self

    def soft_delete(self, *, expected_version: int, actor_ref: str = "") -> None:
        self.transition_action("delete", expected_version=expected_version, actor_ref=actor_ref)


class ContentRevision(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    content = models.ForeignKey(ContentRecord, on_delete=models.CASCADE, related_name="revisions")
    revision = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    snapshot = models.JSONField(default=dict)
    actor_ref = models.CharField(max_length=200, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    schema_version = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    snapshot_sha256 = models.CharField(
        max_length=64, blank=True, default="", validators=[sha256_validator]
    )
    action = models.CharField(max_length=32, blank=True, default="update")
    restored_from_version = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["content", "revision"], name="sitecontent_revision_uq"),
        ]
        ordering = ["content_id", "revision"]

    def clean(self) -> None:
        super().clean()
        if not isinstance(self.snapshot, dict) or len(self.snapshot) > 128:
            raise ValidationError("content_version_snapshot_invalid")
        try:
            encoded = json.dumps(
                self.snapshot, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            ).encode()
        except (TypeError, ValueError):
            raise ValidationError("content_version_snapshot_invalid") from None
        if len(encoded) > 1024 * 1024:
            raise ValidationError("content_version_snapshot_invalid")
        digest = hashlib.sha256(encoded).hexdigest()
        if self.snapshot_sha256 and self.snapshot_sha256 != digest:
            raise ValidationError("content_version_digest_invalid")
        self.snapshot_sha256 = digest

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError("content_version_immutable")
        # Empty legacy snapshots are valid JSON; leave uniqueness/constraint races to
        # PostgreSQL so concurrent revision inserts preserve their IntegrityError contract.
        self.full_clean(exclude={"snapshot"}, validate_unique=False, validate_constraints=False)
        return super().save(*args, **kwargs)

    def diff_values(self, other: dict) -> dict[str, list[str]]:
        current = self.snapshot.get("values", self.snapshot)
        if (
            not isinstance(current, dict)
            or not isinstance(other, dict)
            or len(current) > 128
            or len(other) > 128
        ):
            raise ValidationError("content_version_diff_invalid")
        current_keys = set(current)
        other_keys = set(other)
        return {
            "added": sorted(other_keys - current_keys),
            "removed": sorted(current_keys - other_keys),
            "changed": sorted(
                key for key in current_keys & other_keys if current[key] != other[key]
            ),
        }


def _snapshot_digest(snapshot: dict) -> str:
    encoded = json.dumps(
        snapshot, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


class ContentRecordVersionManager(models.Manager):
    @staticmethod
    def _translate(kwargs):
        kwargs = dict(kwargs)
        if "record" in kwargs:
            kwargs["content"] = kwargs.pop("record")
        if "version" in kwargs:
            kwargs["revision"] = kwargs.pop("version")
        return kwargs

    def create(self, **kwargs):
        return super().create(**self._translate(kwargs))

    def get(self, *args, **kwargs):
        return super().get(*args, **self._translate(kwargs))

    def filter(self, *args, **kwargs):
        return super().filter(*args, **self._translate(kwargs))


class ContentRecordVersion(ContentRevision):
    objects = ContentRecordVersionManager()

    class Meta:
        proxy = True

    @property
    def record(self):
        return self.content

    @property
    def record_id(self):
        return self.content_id


class ContentRelationship(SiteOwnedModel):
    DELETION_POLICIES = ("restrict", "detach", "cascade_soft")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source = models.ForeignKey(
        ContentRecord, on_delete=models.CASCADE, related_name="outgoing_relationships"
    )
    target = models.ForeignKey(
        ContentRecord, on_delete=models.PROTECT, related_name="incoming_relationships"
    )
    field_key = models.CharField(max_length=63, validators=[content_identifier_validator])
    order = models.PositiveSmallIntegerField(default=0)
    deletion_policy = models.CharField(
        max_length=16, choices=[(item, item) for item in DELETION_POLICIES], default="restrict"
    )
    target_type = models.CharField(
        max_length=63, blank=True, default="", validators=[content_identifier_validator]
    )
    maximum_items = models.PositiveSmallIntegerField(
        default=50, validators=[MinValueValidator(1), MaxValueValidator(50)]
    )
    maximum_depth = models.PositiveSmallIntegerField(
        default=2, validators=[MinValueValidator(1), MaxValueValidator(2)]
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["source", "field_key", "target"], name="sitecontent_relationship_uq"
            ),
            models.CheckConstraint(
                condition=~models.Q(source=models.F("target")), name="sitecontent_no_self_rel"
            ),
        ]
        ordering = ["source_id", "field_key", "order", "target_id"]

    def _would_create_cycle(self) -> bool:
        frontier = {self.target_id}
        visited: set[uuid.UUID] = set()
        for _depth in range(self.maximum_depth):
            if self.source_id in frontier:
                return True
            visited.update(frontier)
            next_ids = ContentRelationship.objects.filter(
                site_id=self.site_id,
                source_id__in=frontier,
            )
            if self.pk:
                next_ids = next_ids.exclude(pk=self.pk)
            frontier = set(next_ids.values_list("target_id", flat=True)) - visited
            if not frontier:
                return False
        return self.source_id in frontier

    def clean(self) -> None:
        super().clean()
        if self.source_id and self.target_id:
            if (
                self.source_id == self.target_id
                or self.site_id != self.source.site_id
                or self.site_id != self.target.site_id
            ):
                raise ValidationError("relationship_scope_invalid")
            if self.target.deleted_at is not None:
                raise ValidationError("relationship_target_deleted")
            if self.target_type and self.target.content_type != self.target_type:
                raise ValidationError("relationship_target_type_invalid")
            existing = ContentRelationship.objects.filter(
                source=self.source, field_key=self.field_key
            )
            if self.pk:
                existing = existing.exclude(pk=self.pk)
            if existing.count() >= self.maximum_items:
                raise ValidationError("relationship_cardinality_invalid")
            if self._would_create_cycle():
                raise ValidationError("relationship_cycle_invalid")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class SavedView(SiteOwnedModel):
    VISIBILITIES = ("private", "role_shared")
    QUERY_KEYS = {"filters", "sort", "fields", "expand", "limit"}
    FILTER_KEYS = {"field", "operator", "value"}
    OPERATORS = {"eq", "ne", "contains", "starts_with", "in", "lt", "lte", "gt", "gte", "is_null"}
    SHARED_ROLES = {"owner", "admin", "editor", "viewer"}
    BUILTIN_FIELDS = {"id", "slug", "title", "state", "created_at", "updated_at", "published_at"}

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    definition = models.ForeignKey(
        ContentTypeDefinition, on_delete=models.CASCADE, related_name="saved_views"
    )
    owner_ref = models.CharField(max_length=200)
    title = models.CharField(max_length=120)
    query = models.JSONField(default=dict)
    visibility = models.CharField(
        max_length=16, choices=[(item, item) for item in VISIBILITIES], default="private"
    )
    shared_roles = models.JSONField(default=list, blank=True)
    schema_version = models.PositiveIntegerField(default=1)
    lock_version = models.PositiveIntegerField(default=1)

    def clean(self) -> None:
        super().clean()
        if self.definition_id and self.definition.site_id != self.site_id:
            raise ValidationError("saved_view_scope_invalid")
        if self.definition_id and self.schema_version != self.definition.version:
            raise ValidationError("saved_view_schema_invalid")
        if not isinstance(self.query, dict) or set(self.query) - self.QUERY_KEYS:
            raise ValidationError("saved_view_query_invalid")
        declared = (
            {field.field_key: field.field_kind for field in self.definition.fields.all()}
            if self.definition_id
            else {}
        )
        allowed_fields = self.BUILTIN_FIELDS | set(declared)
        filters = self.query.get("filters", [])
        if not isinstance(filters, list) or len(filters) > 16:
            raise ValidationError("saved_view_query_invalid")
        for item in filters:
            if (
                not isinstance(item, dict)
                or set(item) != self.FILTER_KEYS
                or item.get("operator") not in self.OPERATORS
                or item.get("field") not in allowed_fields
            ):
                raise ValidationError("saved_view_query_invalid")
        sorts = self.query.get("sort", [])
        fields = self.query.get("fields", [])
        expands = self.query.get("expand", [])
        limit = self.query.get("limit", 25)
        if (
            not isinstance(sorts, list)
            or len(sorts) > 4
            or any(
                not isinstance(item, str) or item.removeprefix("-") not in allowed_fields
                for item in sorts
            )
            or not isinstance(fields, list)
            or len(fields) > 64
            or len(fields) != len(set(fields))
            or any(item not in allowed_fields for item in fields)
            or not isinstance(expands, list)
            or len(expands) > 4
            or len(expands) != len(set(expands))
            or any(declared.get(item) not in {"reference", "references"} for item in expands)
            or not isinstance(limit, int)
            or isinstance(limit, bool)
            or not 1 <= limit <= 100
        ):
            raise ValidationError("saved_view_query_invalid")
        if (
            not isinstance(self.shared_roles, list)
            or len(self.shared_roles) > len(self.SHARED_ROLES)
            or len(self.shared_roles) != len(set(self.shared_roles))
            or any(role not in self.SHARED_ROLES for role in self.shared_roles)
            or (self.visibility == "private" and self.shared_roles)
            or (self.visibility == "role_shared" and not self.shared_roles)
        ):
            raise ValidationError("saved_view_roles_invalid")


class AssetBinding(SiteOwnedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    record = models.ForeignKey(
        ContentRecord, on_delete=models.CASCADE, related_name="asset_bindings"
    )
    asset = models.ForeignKey(
        "MediaAsset", on_delete=models.PROTECT, related_name="content_bindings"
    )
    field_key = models.CharField(max_length=63, validators=[content_identifier_validator])
    order = models.PositiveSmallIntegerField(default=0)
    alt_text = models.CharField(max_length=500, blank=True, default="")
    caption = models.TextField(blank=True, default="")
    credit = models.CharField(max_length=500, blank=True, default="")
    focal_x = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    focal_y = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["record", "field_key", "asset"], name="sitecontent_asset_binding_uq"
            ),
        ]
        ordering = ["record_id", "field_key", "order"]

    def clean(self) -> None:
        super().clean()
        if self.record_id and self.asset_id:
            if self.site_id != self.record.site_id or self.site_id != self.asset.site_id:
                raise ValidationError("asset_binding_scope_invalid")
            if self.asset.media_type.startswith("image/") and not self.alt_text.strip():
                raise ValidationError("asset_alt_text_required")


class WorkspaceJob(SiteOwnedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    definition = models.ForeignKey(ContentTypeDefinition, on_delete=models.PROTECT)
    requester_ref = models.CharField(max_length=200)
    request_digest = models.CharField(max_length=64, validators=[sha256_validator])
    idempotency_key = models.CharField(max_length=128)
    schema_version = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    error_code = models.CharField(max_length=64, blank=True, default="")
    counters = models.JSONField(default=dict, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    def clean(self) -> None:
        super().clean()
        if self.definition_id and self.definition.site_id != self.site_id:
            raise ValidationError("workspace_job_scope_invalid")
        validate_closed_mapping(
            self.counters,
            allowed_keys={"total", "valid", "invalid", "created", "updated", "skipped", "review"},
            error_code="job_counters_invalid",
        )


class ImportJob(WorkspaceJob):
    STATUSES = (
        "uploaded",
        "parsing",
        "mapped",
        "validated",
        "review_required",
        "committing",
        "completed",
        "failed",
        "cancelled",
    )
    source_sha256 = models.CharField(max_length=64, validators=[sha256_validator])
    source_format = models.CharField(
        max_length=8, choices=(("json", "JSON"), ("csv", "CSV")), default="json"
    )
    source_object_key = models.CharField(max_length=500, blank=True, default="")
    status = models.CharField(
        max_length=24, choices=[(item, item) for item in STATUSES], default="uploaded"
    )
    mapping = models.JSONField(default=dict, blank=True)
    duplicate_policy = models.CharField(max_length=16, default="review")
    atomic_policy = models.CharField(max_length=16, default="all_or_nothing")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["site_id", "idempotency_key"], name="sitecontent_import_replay_uq"
            ),
        ]

    TRANSITIONS = {
        "uploaded": {"parsing", "cancelled", "failed"},
        "parsing": {"mapped", "failed", "cancelled"},
        "mapped": {"validated", "review_required", "failed", "cancelled"},
        "validated": {"committing", "cancelled", "failed"},
        "review_required": {"validated", "cancelled", "failed"},
        "committing": {"completed", "failed"},
        "completed": set(),
        "failed": set(),
        "cancelled": set(),
    }

    def transition_status(self, destination: str) -> None:
        if destination not in self.TRANSITIONS.get(self.status, set()):
            if self.status in {"completed", "failed", "cancelled"}:
                raise ValidationError("content_job_terminal")
            raise ValidationError("content_job_transition_invalid")
        self.status = destination
        if destination in {"completed", "failed", "cancelled"}:
            self.completed_at = timezone.now()
        self.full_clean()
        self.save(update_fields=["status", "completed_at", "updated_at"])


class ImportRowOutcome(SiteOwnedModel):
    ACTIONS = ("create", "update", "skip", "review", "reject")
    ISSUE_KEYS = {"field", "code"}

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey(ImportJob, on_delete=models.CASCADE, related_name="row_outcomes")
    ordinal = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    source_row_sha256 = models.CharField(max_length=64, validators=[sha256_validator])
    proposed_action = models.CharField(max_length=16, choices=[(item, item) for item in ACTIONS])
    field_issues = models.JSONField(default=list, blank=True)
    exact_match_id = models.UUIDField(null=True, blank=True)
    candidate_ids = models.JSONField(default=list, blank=True)
    result_record_id = models.UUIDField(null=True, blank=True)
    result_version = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["job", "ordinal"], name="sitecontent_import_row_ordinal_uq"
            )
        ]
        ordering = ["job_id", "ordinal"]

    def clean(self) -> None:
        super().clean()
        if self.job_id and self.job.site_id != self.site_id:
            raise ValidationError("workspace_job_scope_invalid")
        if (
            not isinstance(self.field_issues, list)
            or len(self.field_issues) > 128
            or any(
                not isinstance(item, dict)
                or set(item) != self.ISSUE_KEYS
                or not re.fullmatch(r"[a-z][a-z0-9_]{1,62}", str(item.get("field", "")))
                or not re.fullmatch(r"[a-z][a-z0-9_]{1,62}", str(item.get("code", "")))
                for item in self.field_issues
            )
        ):
            raise ValidationError("import_row_issue_invalid")
        if not isinstance(self.candidate_ids, list) or len(self.candidate_ids) > 10:
            raise ValidationError("import_row_candidate_invalid")


class ExportJob(WorkspaceJob):
    STATUSES = ("queued", "running", "completed", "failed", "cancelled", "expired")
    status = models.CharField(
        max_length=16, choices=[(item, item) for item in STATUSES], default="queued"
    )
    format = models.CharField(
        max_length=8, choices=(("json", "JSON"), ("csv", "CSV")), default="json"
    )
    projection_digest = models.CharField(
        max_length=64, blank=True, default="", validators=[sha256_validator]
    )
    projection_fields = models.JSONField(default=list, blank=True)
    output_sha256 = models.CharField(
        max_length=64, blank=True, default="", validators=[sha256_validator]
    )
    encrypted_object_key = models.CharField(max_length=500, blank=True, default="")
    expires_at = models.DateTimeField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["site_id", "idempotency_key"], name="sitecontent_export_replay_uq"
            ),
        ]

    def clean(self) -> None:
        super().clean()
        if (
            not isinstance(self.projection_fields, list)
            or not 1 <= len(self.projection_fields) <= 64
            or len(self.projection_fields) != len(set(self.projection_fields))
            or any(
                not isinstance(item, str) or not content_identifier_validator.regex.fullmatch(item)
                for item in self.projection_fields
            )
        ):
            raise ValidationError("export_projection_invalid")


class WorkspaceAuditEvent(models.Model):
    ALLOWED_METADATA_KEYS = {
        "count",
        "sha256",
        "durationMs",
        "status",
        "errorCode",
        "version",
        "jobId",
    }

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    site_id = models.CharField(max_length=63, validators=[site_id_validator], db_index=True)
    actor_ref = models.CharField(max_length=200)
    object_type = models.CharField(max_length=64)
    object_ref = models.CharField(max_length=200)
    action = models.CharField(max_length=64)
    outcome = models.CharField(max_length=32)
    correlation_id = models.CharField(max_length=128, blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "id"]

    def clean(self) -> None:
        super().clean()
        validate_closed_mapping(
            self.metadata,
            allowed_keys=self.ALLOWED_METADATA_KEYS,
            error_code="audit_metadata_key_invalid",
        )

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError("audit_event_immutable")
        self.full_clean()
        return super().save(*args, **kwargs)


class RedirectRule(SiteOwnedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source_path = models.CharField(max_length=500, validators=[validate_local_path])
    target_path = models.CharField(max_length=500, validators=[validate_local_path])
    status_code = models.PositiveSmallIntegerField(
        choices=((301, "Permanent"), (302, "Temporary")), default=301
    )
    active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["site_id", "source_path"], name="sitecontent_redirect_uq"
            )
        ]


class MediaAsset(SiteOwnedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        UPLOADED = "uploaded", "Uploaded"
        INSPECTING = "inspecting", "Inspecting"
        ACCEPTED = "accepted", "Accepted"
        PROCESSING = "processing", "Processing"
        READY = "ready", "Ready"
        FAILED = "failed", "Failed"
        VALIDATED = "validated", "Validated"
        QUARANTINED = "quarantined", "Quarantined"
        REJECTED = "rejected", "Rejected"
        ARCHIVED = "archived", "Archived"
        DELETED = "deleted", "Deleted"
        SOFT_DELETED = "soft_deleted", "Soft deleted"
        PURGE_PLANNED = "purge_planned", "Purge planned"
        PURGED = "purged", "Purged"

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
    visibility = models.CharField(
        max_length=16,
        choices=(("private", "Private"), ("authenticated", "Authenticated"), ("public", "Public")),
        default="private",
    )
    lock_version = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    current_object_version = models.PositiveIntegerField(
        default=1, validators=[MinValueValidator(1)]
    )
    archived_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["site_id", "storage_key"], name="sitecontent_media_key_uq"
            )
        ]
        indexes = [
            models.Index(fields=["site_id", "status", "created_at"], name="sitecontent_media_idx")
        ]

    def quarantine(self, reason_code: str) -> None:
        if self.status == self.Status.DELETED:
            raise ValidationError({"status": "Deleted media cannot return to quarantine."})
        if not re.fullmatch(r"[a-z][a-z0-9_]{2,63}", reason_code or ""):
            raise ValidationError(
                {"metadata": "A bounded machine-readable quarantine reason is required."}
            )
        self.status = self.Status.QUARANTINED
        self.metadata = {"metadataPolicy": "stripped", "quarantineReason": reason_code}
        self.save(update_fields=["status", "metadata", "updated_at"])

    def validate_variants(self, variants: list[dict], *, scanner_ref: str) -> list[MediaVariant]:
        if self.status != self.Status.QUARANTINED:
            raise ValidationError({"status": "Only quarantined media can be validated."})
        if not re.fullmatch(r"[A-Za-z0-9._:-]{3,128}", scanner_ref or ""):
            raise ValidationError({"metadata": "A valid scanner receipt is required."})
        if not 1 <= len(variants) <= 10:
            raise ValidationError(
                {"variants": "Between one and ten validated variants are required."}
            )
        with transaction.atomic():
            created = []
            for item in variants:
                variant = MediaVariant(asset=self, **item)
                variant.full_clean()
                variant.save()
                created.append(variant)
            self.status = self.Status.VALIDATED
            self.metadata = {
                "metadataPolicy": "stripped",
                "scanStatus": "clean",
                "scannerRef": scanner_ref,
            }
            self.save(update_fields=["status", "metadata", "updated_at"])
        return created


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
    recipe_id = models.CharField(max_length=64, blank=True, default="legacy-safe-v1")
    recipe_version = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    source_sha256 = models.CharField(max_length=64, blank=True, default="")
    processor_ref = models.CharField(max_length=128, blank=True, default="")
    inline_safe = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["asset", "name"], name="sitecontent_variant_uq")
        ]

    def clean(self) -> None:
        super().clean()
        if self.source_sha256 and not re.fullmatch(SHA256_PATTERN, self.source_sha256):
            raise ValidationError({"source_sha256": "media_source_digest_invalid"})
        if self.inline_safe and not self.media_type.startswith("image/"):
            raise ValidationError({"inline_safe": "media_inline_type_invalid"})


class MediaObjectVersion(SiteOwnedModel):
    class InspectionState(models.TextChoices):
        UPLOADED = "uploaded", "Uploaded"
        INSPECTING = "inspecting", "Inspecting"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asset = models.ForeignKey(MediaAsset, on_delete=models.PROTECT, related_name="object_versions")
    version = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    storage_key = models.CharField(max_length=500)
    sha256 = models.CharField(max_length=64, validators=[sha256_validator])
    byte_size = models.PositiveBigIntegerField(validators=[MinValueValidator(1)])
    detected_type = models.CharField(max_length=127)
    inspection_state = models.CharField(
        max_length=16, choices=InspectionState.choices, default=InspectionState.UPLOADED
    )
    scanner_ref = models.CharField(max_length=128, blank=True, default="")
    scanner_definitions_at = models.DateTimeField(null=True, blank=True)
    source_upload_ref = models.UUIDField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["asset", "version"], name="sitecontent_media_object_version_uq"
            ),
            models.UniqueConstraint(
                fields=["site_id", "storage_key"], name="sitecontent_media_object_key_uq"
            ),
        ]

    def clean(self) -> None:
        super().clean()
        if self.asset_id and self.asset.site_id != self.site_id:
            raise ValidationError("media_object_scope_invalid")


class MediaUploadSession(SiteOwnedModel):
    class Status(models.TextChoices):
        CREATED = "created", "Created"
        RECEIVING = "receiving", "Receiving"
        UPLOADED = "uploaded", "Uploaded"
        COMPLETED = "completed", "Completed"
        EXPIRED = "expired", "Expired"
        CANCELLED = "cancelled", "Cancelled"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor_ref = models.CharField(max_length=200)
    idempotency_key = models.CharField(max_length=128)
    expected_sha256 = models.CharField(max_length=64, validators=[sha256_validator])
    expected_bytes = models.PositiveBigIntegerField(validators=[MinValueValidator(1)])
    received_bytes = models.PositiveBigIntegerField(default=0)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.CREATED)
    lock_version = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    expires_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["site_id", "actor_ref", "idempotency_key"],
                name="sitecontent_media_upload_replay_uq",
            )
        ]
        indexes = [
            models.Index(fields=["site_id", "status", "expires_at"], name="media_upload_due_idx")
        ]

    def clean(self) -> None:
        super().clean()
        if self.received_bytes > self.expected_bytes:
            raise ValidationError("media_upload_length_invalid")


class MediaUploadPart(SiteOwnedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(MediaUploadSession, on_delete=models.CASCADE, related_name="parts")
    part_number = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10_000)]
    )
    byte_size = models.PositiveBigIntegerField(validators=[MinValueValidator(1)])
    sha256 = models.CharField(max_length=64, validators=[sha256_validator])
    storage_key = models.CharField(max_length=500)
    completed_at = models.DateTimeField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["session", "part_number"], name="sitecontent_media_upload_part_uq"
            ),
            models.UniqueConstraint(
                fields=["site_id", "storage_key"], name="sitecontent_media_part_key_uq"
            ),
        ]
        indexes = [
            models.Index(fields=["site_id", "session", "part_number"], name="media_part_idx")
        ]

    def clean(self) -> None:
        super().clean()
        if self.session_id and self.session.site_id != self.site_id:
            raise ValidationError("media_upload_part_scope_invalid")
        if self.session_id and self.byte_size > self.session.expected_bytes:
            raise ValidationError("media_upload_part_length_invalid")


class MediaInspectionResult(SiteOwnedModel):
    DECISIONS = tuple((value, value.title()) for value in ("accepted", "rejected", "failed"))
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    object_version = models.ForeignKey(
        MediaObjectVersion, on_delete=models.PROTECT, related_name="inspection_results"
    )
    attempt = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)]
    )
    decision = models.CharField(max_length=16, choices=DECISIONS)
    safe_code = models.CharField(max_length=64)
    scanner_ref = models.CharField(max_length=128)
    decoder_ref = models.CharField(max_length=128)
    definitions_at = models.DateTimeField()
    observed_media_type = models.CharField(max_length=127)
    measurements = models.JSONField(default=dict)
    result_sha256 = models.CharField(max_length=64, validators=[sha256_validator])

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["object_version", "attempt"], name="sitecontent_media_inspection_uq"
            )
        ]

    def clean(self) -> None:
        super().clean()
        if self.object_version_id and self.object_version.site_id != self.site_id:
            raise ValidationError("media_inspection_scope_invalid")
        if not re.fullmatch(r"media_[a-z0-9_]{3,63}", self.safe_code or ""):
            raise ValidationError("media_inspection_code_invalid")
        validate_closed_mapping(
            self.measurements,
            allowed_keys={
                "pixels",
                "frames",
                "pages",
                "durationSeconds",
                "expandedBytes",
                "streams",
            },
            error_code="media_inspection_measurements_invalid",
            maximum_keys=6,
        )


class MediaDerivativeRecipe(models.Model):
    recipe_id = models.SlugField(max_length=64)
    version = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    output_media_type = models.CharField(max_length=127)
    processor_ref = models.CharField(max_length=128)
    parameters = models.JSONField(default=dict)
    recipe_sha256 = models.CharField(max_length=64, validators=[sha256_validator])
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["recipe_id", "version"], name="sitecontent_media_recipe_uq"
            )
        ]

    def clean(self) -> None:
        super().clean()
        validate_closed_mapping(
            self.parameters,
            allowed_keys={
                "width",
                "height",
                "fit",
                "quality",
                "page",
                "durationSeconds",
                "noUpscale",
                "stripMetadata",
            },
            error_code="media_recipe_parameters_invalid",
            maximum_keys=8,
        )
        if self.parameters.get("noUpscale") is not True:
            raise ValidationError("media_recipe_upscale_policy_invalid")
        if self.parameters.get("stripMetadata") is not True:
            raise ValidationError("media_recipe_metadata_policy_invalid")


class MediaMetadataRevision(SiteOwnedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asset = models.ForeignKey(
        MediaAsset, on_delete=models.PROTECT, related_name="metadata_revisions"
    )
    revision = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    locale = models.CharField(max_length=32, default="en")
    alt_text = models.CharField(max_length=500, blank=True, default="")
    decorative = models.BooleanField(default=False)
    caption = models.TextField(blank=True, default="")
    credit = models.CharField(max_length=500, blank=True, default="")
    license_code = models.CharField(max_length=64, blank=True, default="")
    focal_x = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    focal_y = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    actor_ref = models.CharField(max_length=200)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["asset", "revision", "locale"], name="sitecontent_media_metadata_uq"
            )
        ]

    def clean(self) -> None:
        super().clean()
        if self.asset_id and self.asset.site_id != self.site_id:
            raise ValidationError("media_metadata_scope_invalid")
        if self.decorative and self.alt_text:
            raise ValidationError("media_decorative_alt_conflict")
        if (
            not self.decorative
            and self.asset_id
            and self.asset.media_type.startswith("image/")
            and not self.alt_text.strip()
        ):
            raise ValidationError("media_alt_or_decorative_required")


class MediaCollection(SiteOwnedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=120)
    owner_ref = models.CharField(max_length=200)
    visibility = models.CharField(
        max_length=16,
        choices=(("private", "Private"), ("role_shared", "Role shared")),
        default="private",
    )
    shared_roles = models.JSONField(default=list, blank=True)
    lock_version = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])

    def clean(self) -> None:
        super().clean()
        allowed = {"owner", "admin", "editor", "viewer"}
        if (
            not isinstance(self.shared_roles, list)
            or len(self.shared_roles) != len(set(self.shared_roles))
            or any(role not in allowed for role in self.shared_roles)
            or (self.visibility == "private" and self.shared_roles)
            or (self.visibility == "role_shared" and not self.shared_roles)
        ):
            raise ValidationError("media_collection_roles_invalid")


class MediaCollectionMembership(SiteOwnedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    collection = models.ForeignKey(
        MediaCollection, on_delete=models.CASCADE, related_name="memberships"
    )
    asset = models.ForeignKey(
        MediaAsset, on_delete=models.CASCADE, related_name="collection_memberships"
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["collection", "asset"], name="sitecontent_media_collection_asset_uq"
            )
        ]

    def clean(self) -> None:
        super().clean()
        if (
            self.collection_id
            and self.asset_id
            and (self.site_id != self.collection.site_id or self.site_id != self.asset.site_id)
        ):
            raise ValidationError("media_collection_scope_invalid")


class MediaJob(SiteOwnedModel):
    JOB_KINDS = tuple(
        (kind, kind.title())
        for kind in ("inspect", "derive", "reconcile", "export", "expire", "purge")
    )
    STATUSES = tuple(
        (state, state.title())
        for state in (
            "queued",
            "leased",
            "running",
            "completed",
            "retryable",
            "failed",
            "cancelled",
        )
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asset = models.ForeignKey(
        MediaAsset, null=True, blank=True, on_delete=models.PROTECT, related_name="jobs"
    )
    kind = models.CharField(max_length=16, choices=JOB_KINDS)
    status = models.CharField(max_length=16, choices=STATUSES, default="queued")
    idempotency_key = models.CharField(max_length=128)
    request_digest = models.CharField(max_length=64, validators=[sha256_validator])
    attempt = models.PositiveSmallIntegerField(default=0)
    maximum_attempts = models.PositiveSmallIntegerField(
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
    )
    error_code = models.CharField(max_length=64, blank=True, default="")
    lease_expires_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["site_id", "kind", "idempotency_key"],
                name="sitecontent_media_job_replay_uq",
            )
        ]

    def clean(self) -> None:
        super().clean()
        if self.asset_id and self.asset.site_id != self.site_id:
            raise ValidationError("media_job_scope_invalid")
        if self.attempt > self.maximum_attempts:
            raise ValidationError("media_job_attempt_invalid")
        if self.error_code and not re.fullmatch(r"media_[a-z0-9_]{3,63}", self.error_code):
            raise ValidationError("media_job_error_invalid")


class MediaRetentionHold(SiteOwnedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asset = models.ForeignKey(MediaAsset, on_delete=models.PROTECT, related_name="retention_holds")
    reason_code = models.CharField(max_length=64)
    owner_ref = models.CharField(max_length=200)
    active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    def clean(self) -> None:
        super().clean()
        if self.asset_id and self.asset.site_id != self.site_id:
            raise ValidationError("media_hold_scope_invalid")
        if not re.fullmatch(r"[a-z][a-z0-9_]{2,63}", self.reason_code or ""):
            raise ValidationError("media_hold_reason_invalid")


class MediaPurgePlan(SiteOwnedModel):
    STATUSES = tuple(
        (value, value.title())
        for value in ("draft", "approved", "scheduled", "cancelled", "completed", "failed")
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asset = models.ForeignKey(MediaAsset, on_delete=models.PROTECT, related_name="purge_plans")
    requested_by = models.CharField(max_length=200)
    reason_code = models.CharField(max_length=64)
    expected_version = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    object_manifest = models.JSONField(default=list)
    reference_preview = models.JSONField(default=list)
    status = models.CharField(max_length=16, choices=STATUSES, default="draft")
    scheduled_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    result_sha256 = models.CharField(max_length=64, blank=True, default="")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["site_id", "asset", "expected_version"],
                name="sitecontent_media_purge_plan_uq",
            )
        ]

    def clean(self) -> None:
        super().clean()
        if self.asset_id and self.asset.site_id != self.site_id:
            raise ValidationError("media_purge_scope_invalid")
        if not re.fullmatch(r"[a-z][a-z0-9_]{2,63}", self.reason_code or ""):
            raise ValidationError("media_purge_reason_invalid")
        if not isinstance(self.object_manifest, list) or len(self.object_manifest) > 128:
            raise ValidationError("media_purge_manifest_invalid")
        if not isinstance(self.reference_preview, list) or len(self.reference_preview) > 128:
            raise ValidationError("media_purge_reference_preview_invalid")
        if self.status == "scheduled" and self.scheduled_at is None:
            raise ValidationError("media_purge_schedule_invalid")
        if self.status == "completed" and not self.result_sha256:
            raise ValidationError("media_purge_result_missing")


class MediaReference(SiteOwnedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asset = models.ForeignKey(MediaAsset, on_delete=models.PROTECT, related_name="references")
    owner_type = models.SlugField(max_length=64)
    owner_id = models.UUIDField()
    field_key = models.SlugField(max_length=100)
    owner_state = models.CharField(max_length=32)
    owner_visibility = models.CharField(
        max_length=16,
        choices=(("private", "Private"), ("authenticated", "Authenticated"), ("public", "Public")),
    )
    required = models.BooleanField(default=False)
    lock_version = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["site_id", "asset", "owner_type", "owner_id", "field_key"],
                name="sitecontent_media_reference_uq",
            )
        ]
        indexes = [
            models.Index(fields=["site_id", "asset", "owner_state"], name="media_reference_idx")
        ]

    def clean(self) -> None:
        super().clean()
        if self.asset_id and self.asset.site_id != self.site_id:
            raise ValidationError("media_reference_scope_invalid")
        if (
            self.owner_visibility == "public"
            and self.asset_id
            and self.asset.visibility != "public"
        ):
            raise ValidationError("media_reference_visibility_invalid")
        if self.required and self.asset_id and self.asset.status != MediaAsset.Status.READY:
            raise ValidationError("media_reference_not_ready")


class MediaDeliveryGrant(SiteOwnedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asset = models.ForeignKey(MediaAsset, on_delete=models.CASCADE, related_name="delivery_grants")
    object_version = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    method = models.CharField(max_length=4, choices=(("GET", "GET"), ("HEAD", "HEAD")))
    audience_ref = models.CharField(max_length=200)
    token_digest = models.CharField(max_length=64, validators=[sha256_validator])
    authorization_epoch = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["site_id", "token_digest"], name="sitecontent_media_grant_digest_uq"
            )
        ]
        indexes = [
            models.Index(fields=["site_id", "asset", "expires_at"], name="media_grant_expiry_idx")
        ]

    def clean(self) -> None:
        super().clean()
        if self.asset_id and self.asset.site_id != self.site_id:
            raise ValidationError("media_grant_scope_invalid")
        if self.expires_at <= timezone.now():
            raise ValidationError("media_grant_expiry_invalid")
        if self.revoked_at and self.revoked_at > timezone.now():
            raise ValidationError("media_grant_revocation_invalid")


class MediaExportPackage(SiteOwnedModel):
    STATUSES = tuple(
        (value, value.title()) for value in ("queued", "running", "ready", "failed", "expired")
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    requested_by = models.CharField(max_length=200)
    output_format = models.CharField(
        max_length=8, choices=(("json", "JSON"), ("csv", "CSV"), ("binary", "Binary"))
    )
    projection = models.JSONField(default=list)
    status = models.CharField(max_length=16, choices=STATUSES, default="queued")
    artifact_key = models.CharField(max_length=500, blank=True, default="")
    artifact_sha256 = models.CharField(max_length=64, blank=True, default="")
    request_digest = models.CharField(max_length=64, validators=[sha256_validator])
    expires_at = models.DateTimeField()
    error_code = models.CharField(max_length=64, blank=True, default="")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["site_id", "requested_by", "request_digest"],
                name="sitecontent_media_export_replay_uq",
            )
        ]

    def clean(self) -> None:
        super().clean()
        if not isinstance(self.projection, list) or len(self.projection) > 64:
            raise ValidationError("media_export_projection_invalid")
        if self.artifact_sha256 and not re.fullmatch(SHA256_PATTERN, self.artifact_sha256):
            raise ValidationError("media_export_digest_invalid")
        if self.status == "ready" and (not self.artifact_key or not self.artifact_sha256):
            raise ValidationError("media_export_artifact_missing")
        if self.error_code and not re.fullmatch(r"media_[a-z0-9_]{3,63}", self.error_code):
            raise ValidationError("media_export_error_invalid")


class MediaAuditEvent(SiteOwnedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sequence = models.PositiveBigIntegerField(validators=[MinValueValidator(1)])
    event_type = models.CharField(max_length=64)
    actor_ref = models.CharField(max_length=200)
    subject_ref = models.CharField(max_length=200)
    detail = models.JSONField(default=dict)
    previous_hash = models.CharField(max_length=64, validators=[sha256_validator])
    event_hash = models.CharField(max_length=64, validators=[sha256_validator])

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["site_id", "sequence"], name="sitecontent_media_audit_seq_uq"
            ),
            models.UniqueConstraint(
                fields=["site_id", "event_hash"], name="sitecontent_media_audit_hash_uq"
            ),
        ]

    def clean(self) -> None:
        super().clean()
        validate_closed_mapping(
            self.detail,
            allowed_keys={
                "code",
                "status",
                "requestId",
                "version",
                "reason",
                "method",
                "objectVersion",
                "mediaType",
                "byteSize",
                "sha256",
                "count",
            },
            error_code="media_audit_detail_invalid",
            maximum_keys=11,
        )
        if not re.fullmatch(r"media\.[a-z0-9_.-]{2,58}", self.event_type or ""):
            raise ValidationError("media_audit_type_invalid")

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError("media_audit_immutable")
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("media_audit_immutable")


class MediaOutboxEvent(SiteOwnedModel):
    STATUSES = tuple(
        (value, value.title())
        for value in ("pending", "leased", "completed", "retryable", "failed")
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    aggregate_ref = models.CharField(max_length=200)
    event_kind = models.CharField(max_length=64)
    idempotency_key = models.CharField(max_length=128)
    payload_digest = models.CharField(max_length=64, validators=[sha256_validator])
    status = models.CharField(max_length=16, choices=STATUSES, default="pending")
    attempt = models.PositiveSmallIntegerField(default=0)
    maximum_attempts = models.PositiveSmallIntegerField(
        default=5, validators=[MinValueValidator(1), MaxValueValidator(10)]
    )
    available_at = models.DateTimeField(default=timezone.now)
    lease_expires_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_code = models.CharField(max_length=64, blank=True, default="")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["site_id", "event_kind", "idempotency_key"],
                name="sitecontent_media_outbox_replay_uq",
            )
        ]
        indexes = [
            models.Index(fields=["site_id", "status", "available_at"], name="media_outbox_due_idx")
        ]

    def clean(self) -> None:
        super().clean()
        if self.attempt > self.maximum_attempts:
            raise ValidationError("media_outbox_attempt_invalid")
        if self.error_code and not re.fullmatch(r"media_[a-z0-9_]{3,63}", self.error_code):
            raise ValidationError("media_outbox_error_invalid")


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
            models.UniqueConstraint(
                fields=["site_id", "form_key", "replay_key"], name="sitecontent_form_replay_uq"
            )
        ]
        indexes = [
            models.Index(
                fields=["site_id", "status", "retained_until"], name="sitecontent_form_idx"
            )
        ]

    def clean(self) -> None:
        super().clean()
        if self.retained_until <= timezone.now():
            raise ValidationError({"retained_until": "Retention expiry must be in the future."})

    @classmethod
    def expire_due(cls, *, at=None) -> int:
        at = at or timezone.now()
        with transaction.atomic():
            due = (
                cls.objects.select_for_update()
                .filter(
                    retained_until__lte=at,
                )
                .exclude(status=cls.Status.EXPIRED)
            )
            submission_ids = list(due.values_list("id", flat=True))
            if not submission_ids:
                return 0
            FormDeliveryOutbox.objects.filter(
                submission_id__in=submission_ids,
                status=FormDeliveryOutbox.Status.QUEUED,
            ).update(
                status=FormDeliveryOutbox.Status.DEAD_LETTER,
                last_error_code="retention_expired",
                updated_at=at,
            )
            return due.update(
                payload={},
                consent={},
                request_id="",
                status=cls.Status.EXPIRED,
                updated_at=at,
            )


class FormDeliveryOutbox(models.Model):
    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        DELIVERED = "delivered", "Delivered"
        DEAD_LETTER = "dead_letter", "Dead letter"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    submission = models.OneToOneField(
        FormSubmission, on_delete=models.CASCADE, related_name="delivery"
    )
    adapter = models.SlugField(max_length=64, default="disabled")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.QUEUED)
    attempts = models.PositiveSmallIntegerField(default=0)
    next_attempt_at = models.DateTimeField(default=timezone.now)
    last_error_code = models.CharField(max_length=64, blank=True, default="")
    delivered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["status", "next_attempt_at"], name="sitecontent_outbox_idx")
        ]


class SearchDocument(SiteOwnedModel):
    class Visibility(models.TextChoices):
        PUBLIC = "public", "Public"
        PRIVATE = "private", "Private"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    content = models.OneToOneField(
        ContentRecord, on_delete=models.CASCADE, related_name="search_document"
    )
    title = models.CharField(max_length=240)
    body = models.TextField()
    url_path = models.CharField(max_length=500, validators=[validate_local_path])
    visibility = models.CharField(
        max_length=16, choices=Visibility.choices, default=Visibility.PUBLIC
    )
    source_updated_at = models.DateTimeField()
    indexed_at = models.DateTimeField(auto_now_add=True)
    tombstoned_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["site_id", "visibility", "tombstoned_at"], name="sitecontent_search_idx"
            )
        ]

    def clean(self) -> None:
        super().clean()
        if self.content_id and self.site_id != self.content.site_id:
            raise ValidationError(
                {"site_id": "Search document and content must belong to the same site."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
