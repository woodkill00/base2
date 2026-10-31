import re
import uuid
import zoneinfo

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_countries.fields import CountryField
from phonenumber_field.modelfields import PhoneNumberField

User = get_user_model()

CONTENT_IDENTIFIER_PATTERN = r"\A[a-z][a-z0-9_]{1,62}\Z"
content_identifier_validator = RegexValidator(
    CONTENT_IDENTIFIER_PATTERN,
    _("Use a lowercase identifier beginning with a letter."),
)

# Type keys are data values, not field/preset or SQL identifiers. Preserve legacy
# underscores while admitting public-pack hyphens; strict anchors reject newlines.
CONTENT_TYPE_KEY_PATTERN = r"\A(?=.{2,63}\Z)[a-z][a-z0-9_]*(?:-[a-z0-9][a-z0-9_]*)*\Z"
content_type_key_validator = RegexValidator(
    CONTENT_TYPE_KEY_PATTERN,
    _(
        "Use 2–63 lowercase ASCII letters, digits or underscores, "
        "with single hyphens followed by a letter or digit."
    ),
)

OPERATIONS_IDENTIFIER_PATTERN = r"^[a-z][a-z0-9_.-]{2,95}$"
operations_identifier_validator = RegexValidator(
    OPERATIONS_IDENTIFIER_PATTERN,
    _("Use a bounded lowercase operations identifier."),
)


def validate_operations_dimensions(value) -> None:
    """Keep operations dimensions bounded, scalar, and secret-free."""

    forbidden = re.compile(r"token|password|secret|credential|authorization|private.?key", re.I)
    if not isinstance(value, dict) or len(value) > 16:
        raise ValidationError("operations_dimensions_invalid")
    for key, item in value.items():
        if (
            not isinstance(key, str)
            or not re.fullmatch(OPERATIONS_IDENTIFIER_PATTERN, key)
            or forbidden.search(key)
            or not isinstance(item, str | int | float | bool)
            or isinstance(item, str)
            and len(item) > 200
        ):
            raise ValidationError("operations_dimensions_invalid")


def validate_closed_mapping(
    value,
    *,
    allowed_keys: set[str],
    error_code: str,
    maximum_keys: int = 32,
) -> None:
    """Validate a bounded JSON object without accepting executable extensions."""

    if not isinstance(value, dict) or len(value) > maximum_keys:
        raise ValidationError(error_code)
    if any(not isinstance(key, str) or key not in allowed_keys for key in value):
        raise ValidationError(error_code)
    for item in value.values():
        if isinstance(item, str) and len(item) > 2_000:
            raise ValidationError(error_code)
        if isinstance(item, dict | list):
            raise ValidationError(error_code)


def validate_safe_identifier(value: str) -> None:
    if not re.fullmatch(CONTENT_IDENTIFIER_PATTERN, str(value or "")):
        raise ValidationError("content_identifier_invalid")


# Notes / optional imports kept for future reference:
# from django.contrib.gis.db import models
# from enum import unique
# from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
# from djmoney.models.fields import MoneyField
# from django.db.models.fields import CharField
# from django.utils import timezone
# from django_countries import countries
# from django_countries import CountryTuple, countries
# from model_utils import Choices


class ID(models.Model):
    pkid = models.AutoField(
        verbose_name=_("Primary Key ID"),
        primary_key=True,
        editable=False,
        help_text=_("Internal primary key id"),
    )
    id = models.UUIDField(
        verbose_name=_("ID"),
        default=uuid.uuid4,
        editable=False,
        unique=True,
        help_text=_("Internal ID"),
    )

    class Meta:
        verbose_name = _("ID")
        verbose_name_plural = _("IDs")
        abstract = True
        # get_latest_by = ['-priority', 'order_date']
        # ordering = ['-order_date']

    def __str__(self):
        return self.pkid


class Created(models.Model):
    created = models.DateTimeField(
        auto_now_add=True,
        # default=timezone.now,
        verbose_name=_("Created On"),
        help_text=_("Date/Time created in database"),
    )

    class Meta:
        verbose_name = _("Created")
        verbose_name_plural = _("Created On")
        abstract = True

    def __str__(self):
        return self.created


class Updated(models.Model):
    updated = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Last Updated On"),
        help_text=_("Date/Time last updated in database"),
    )

    class Meta:
        verbose_name = _("Updated")
        verbose_name_plural = _("Updated On")
        abstract = True

    def __str__(self):
        return self.updated


class TimestampedModel(models.Model):
    created = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created On"),
        help_text=_("Date/Time created in database"),
    )
    updated = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Last Updated On"),
        help_text=_("Date/Time last updated in database"),
    )

    class Meta:
        verbose_name = _("Timestamped Model")
        verbose_name_plural = _("Timestamped Models")
        abstract = True


class UUIDMixin(models.Model):
    uuid = models.UUIDField(
        verbose_name=_("UUID"),
        default=uuid.uuid4,
        editable=False,
        unique=True,
        help_text=_("Non-primary UUID identifier"),
    )

    class Meta:
        verbose_name = _("UUID Mixin")
        verbose_name_plural = _("UUID Mixins")
        abstract = True


class NotificationPreferenceSet(UUIDMixin, TimestampedModel):
    """Canonical revision header for a normalized notification preference set.

    Concrete adapters supply identity and scope relationships. An absent header is
    logically version zero; persisted headers start at one. Writers must compare
    and advance the version atomically with their choice-row replacement.
    """

    schema_version = models.PositiveSmallIntegerField(default=1)
    version = models.PositiveBigIntegerField(default=1)

    class Meta:
        abstract = True
        constraints = [
            models.CheckConstraint(
                condition=models.Q(schema_version=1),
                name="%(app_label)s_notifset_schema_v1",
            ),
            models.CheckConstraint(
                condition=models.Q(version__gte=1),
                name="%(app_label)s_notifset_ver_gte1",
            ),
        ]


# class Name(models.Model):
#     name = models.CharField(
#         verbose_name=_("Name"),
#         max_length=150,
#         blank=True,
#         unique=True,
#         help_text=_("Name"),
#     )

#     class Meta:
#         verbose_name = _("Name")
#         verbose_name_plural = _("Names")
#         abstract = True
#         # get_latest_by = ['-priority', 'order_date']
#         # ordering = ['-order_date']

#     def __str__(self):
#         return self.name


class Timezone(models.Model):
    TIMEZONE_CHOICES = ((x, x) for x in sorted(zoneinfo.available_timezones(), key=str.lower))
    timezone = models.CharField(
        verbose_name=_("IANA Time Zone"),
        choices=TIMEZONE_CHOICES,
        max_length=255,
        blank=True,
        default=_("America/New_York"),
        help_text=_("Timezone"),
    )
    # utc_offset = models.FloatField(
    #     verbose_name=_("UTC Offset"),
    #     choices=COMPANY_UTC_OFFSET_CHOICES,
    #     default=(0),
    #     # blank=True,
    #     validators=[
    #         MinValueValidator(-12),
    #         MaxValueValidator(14)
    #     ],
    #     help_text=_("UTC offset Time min=-12 / max=14"),
    # )

    class Meta:
        verbose_name = _("Timezone")
        verbose_name_plural = _("Timezones")
        abstract = True

    def __str__(self):
        return self.timezone


class Address(models.Model):
    # pkid = models.AutoField(
    #     verbose_name=_("Primary Key ID"),
    #     primary_key=True,
    #     editable=False,
    #     help_text=_("Internal primary key id for base address"),
    # )
    # id = models.UUIDField(
    #     verbose_name=_("ID"),
    #     default=uuid.uuid4,
    #     editable=False,
    #     unique=True,
    #     help_text=_("Internal ID for address"),
    # )
    # name = models.CharField(
    #     verbose_name=_("Name"),
    #     max_length=150,
    #     blank=True,
    #     unique=True,
    #     help_text=_("Name"),
    # )
    line1 = models.CharField(
        verbose_name=_("Address Line 1"),
        max_length=255,
        # blank=True,
        # default='',
        help_text=_("Street Line 1"),
    )
    line2 = models.CharField(
        verbose_name=_("Address Line 2"),
        max_length=255,
        blank=True,
        default="",
        help_text=_("Address Line 2"),
    )
    city = models.CharField(
        verbose_name=_("City"),
        max_length=150,
        # blank=True,
        # default='',
        help_text=_("City Name"),
    )
    state = models.CharField(
        verbose_name=_("State"),
        max_length=150,
        blank=True,
        null=True,
        # default='',
        help_text=_("State Name"),
    )
    state_code = models.CharField(
        verbose_name=_("State Code"),
        max_length=5,
        blank=True,
        null=True,
        # default='',
        help_text=_("State Code"),
    )
    postal_code = models.PositiveIntegerField(
        verbose_name=_("Postal Zip Code"),
        blank=True,
        null=True,
        # default='',
        validators=[MinValueValidator(0), MaxValueValidator(999999999)],
        help_text=_("Postal Zip Code"),
    )
    country = CountryField(
        blank_label=_("Select Country"),
        verbose_name=_("Country"),
        max_length=150,
        # default='',
        help_text=_("Country Name"),
    )
    latitude = models.DecimalField(
        verbose_name=_("Latitude"),
        blank=True,
        null=True,
        default="",
        max_digits=18,
        decimal_places=15,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
        help_text=_("Latitude"),
    )
    longitude = models.DecimalField(
        verbose_name=_("Longitude"),
        blank=True,
        null=True,
        default="",
        max_digits=18,
        decimal_places=15,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
        help_text=_("Longitude"),
    )
    # location = models.PointField(
    #     verbose_name=_("Lat and Lon"),
    #     help_text=_("Lat/Lon"),
    # )
    street_number = models.PositiveIntegerField(
        verbose_name=_("Street Number"),
        blank=True,
        null=True,
        # default="",
        validators=[MinValueValidator(0), MaxValueValidator(99999)],
        help_text=_("Street Number"),
    )
    street_number_before_name = models.BooleanField(
        verbose_name=_("Street Number Before Name"),
        default=False,
        help_text=_("Street Number > Street Name"),
    )
    street_name = models.CharField(
        verbose_name=_("Street Name"),
        max_length=150,
        blank=True,
        # default="",
        help_text=_("Street Name"),
    )
    sub_premise = models.PositiveIntegerField(
        verbose_name=_("Suite Number"),
        blank=True,
        null=True,
        # default="",
        validators=[MinValueValidator(0), MaxValueValidator(9999)],
        help_text=_("Suite Number"),
    )
    sub_premise_name = models.CharField(
        verbose_name=_("Sub Premise Name"),
        max_length=150,
        blank=True,
        # default="",
        help_text=_("Sub Premise Name"),
    )

    class Meta:
        verbose_name = _("Address")
        verbose_name_plural = _("Addresses")
        abstract = True

    # def __str__(self):
    #     return self.name

    # def __str__(self):
    #     return self.name

    # def get_geo_location(self):
    #     return f"lat: {self.latitude}, lat: {self.longitude}"

    # def get_country_name(self):
    #     return self.country.name

    # def get_country_code(self):
    #     return self.country.code

    # def get_country_alpha3(self):
    #     return self.country.alpha3

    # def get_country_numeric(self):
    #     return self.country.numeric

    # def get_country_numeric_padded(self):
    #     return self.country.numeric_padded

    # def get_country_ioc_code(self):
    #     return self.country.ioc_code


class Category(models.Model):
    name = models.CharField(
        # default=_("UNKNOWN"),
        verbose_name=_("Category Name"),
        unique=True,
        blank=True,
        default="",
        max_length=255,
        help_text=_("Category name"),
    )

    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")
        abstract = True

    def __str__(self):
        return self.name


class Domain(models.Model):
    name = models.CharField(
        verbose_name=_("Domain Name"),
        max_length=255,
        help_text=_("Domain Name"),
    )

    class Meta:
        verbose_name = _("Domain Name")
        verbose_name_plural = _("Domain Names")
        abstract = True

    def __str__(self):
        return self.name


class Email(models.Model):
    email = models.EmailField(
        verbose_name=_("Email Address"),
        max_length=255,
        unique=True,
        help_text=_("Email Address"),
    )

    class Meta:
        verbose_name = _("Email Address")
        verbose_name_plural = _("Email Addresses")
        abstract = True

    def __str__(self):
        return self.email


class IpAddress(models.Model):
    address = models.GenericIPAddressField(
        verbose_name=_("Ip Address"),
        max_length=255,
        blank=True,
        null=True,
        default="",
        help_text=_("Ip Address"),
    )

    class Meta:
        verbose_name = _("Ip Address")
        verbose_name_plural = _("Ip Addresses")
        abstract = True

    def __str__(self):
        return self.address


class Phonenumber(models.Model):
    phonenumber = PhoneNumberField(
        verbose_name=_("Phonenumber"),
        help_text=_("Phonenumber"),
    )

    class Meta:
        verbose_name = _("Phonenumber")
        verbose_name_plural = _("Phonenumbers")
        abstract = True

    def __str__(self):
        return self.phonenumber


class Staff(models.Model):
    member = models.ForeignKey(
        User,
        verbose_name=_("Staff member"),
        blank=True,
        on_delete=models.CASCADE,
        help_text=_("Staff member"),
    )

    class Meta:
        verbose_name = _("Staff")
        verbose_name_plural = _("Staffs")
        abstract = True

    def __str__(self):
        return f"{self.member}"


class Tag(models.Model):
    name = models.CharField(
        # default=_("UNKNOWN"),
        verbose_name=_("Tag Name"),
        unique=True,
        max_length=255,
        help_text=_("Tag name"),
    )

    class Meta:
        verbose_name = _("Tag")
        verbose_name_plural = _("Tags")
        abstract = True

    def __str__(self):
        return self.name


class Url(models.Model):
    address = models.URLField(
        verbose_name=_("Url Address"),
        unique=True,
        max_length=255,
        help_text=_("Url Address"),
    )

    class Meta:
        verbose_name = _("Url Address")
        verbose_name_plural = _("Url Addresses")
        abstract = True

    def __str__(self):
        return self.address


class WorkspaceScopedState(models.Model):
    """Canonical site-scoped storage, independent of operator/public identities."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    site_id = models.CharField(
        max_length=63,
        validators=[
            RegexValidator(r"^[a-z0-9][a-z0-9-]{0,62}$", "Enter a canonical site identifier.")
        ],
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        constraints = [
            models.CheckConstraint(
                condition=models.Q(site_id__regex=r"^[a-z0-9][a-z0-9-]{0,62}$"),
                name="%(app_label)s_%(class)s_scope_ck",
            )
        ]


class WorkspacePolicy(WorkspaceScopedState):
    class PublicAccess(models.TextChoices):
        PUBLIC_ALLOWED = "public_allowed", "Public eligible"
        MEMBERS_ONLY = "members_only", "Members only"

    class Provenance(models.TextChoices):
        DEFAULT = "default", "Default"
        MIGRATED = "migrated", "Migrated"
        EXPLICIT = "explicit", "Explicit"

    # This reference belongs to the public identity realm, not users.Organization.
    organization_id = models.UUIDField(null=True, blank=True)
    schema_version = models.PositiveSmallIntegerField(default=1)
    version = models.PositiveBigIntegerField(default=1)
    require_review = models.BooleanField(default=True)
    public_access = models.CharField(
        max_length=16, choices=PublicAccess.choices, default=PublicAccess.MEMBERS_ONLY
    )
    provenance = models.CharField(
        max_length=16, choices=Provenance.choices, default=Provenance.DEFAULT
    )

    class Meta:
        abstract = True
        constraints = [
            *WorkspaceScopedState.Meta.constraints,
            models.UniqueConstraint(fields=("site_id",), name="%(app_label)s_policy_site_uq"),
            models.CheckConstraint(
                condition=models.Q(schema_version=1), name="%(app_label)s_policy_schema_v1"
            ),
            models.CheckConstraint(
                condition=models.Q(version__gte=1), name="%(app_label)s_policy_ver_gte1"
            ),
            models.CheckConstraint(
                condition=models.Q(public_access__in=("public_allowed", "members_only")),
                name="%(app_label)s_policy_access_ck",
            ),
            models.CheckConstraint(
                condition=models.Q(provenance__in=("default", "migrated", "explicit")),
                name="%(app_label)s_policy_source_ck",
            ),
        ]


class ReviewSubject(WorkspaceScopedState):
    schema_version = models.PositiveSmallIntegerField(default=1)
    original_creator_id = models.UUIDField(null=True, blank=True)
    semantic_author_id = models.UUIDField(null=True, blank=True)
    submitter_id = models.UUIDField(null=True, blank=True)
    adopted_snapshot = models.BooleanField(default=False)
    semantic_revision = models.UUIDField(default=uuid.uuid4)
    semantic_generation = models.PositiveBigIntegerField(default=1)
    fingerprint = models.CharField(max_length=64, validators=[RegexValidator(r"^[a-f0-9]{64}$")])
    submission_id = models.UUIDField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    scheduled_by_id = models.UUIDField(null=True, blank=True)
    schedule_policy_version = models.PositiveBigIntegerField(null=True, blank=True)

    class Meta:
        abstract = True
        constraints = [
            *WorkspaceScopedState.Meta.constraints,
            models.CheckConstraint(
                condition=models.Q(fingerprint__regex=r"^[a-f0-9]{64}$"),
                name="%(app_label)s_subject_hash_ck",
            ),
            models.CheckConstraint(
                condition=models.Q(semantic_generation__gte=1), name="%(app_label)s_subject_gen_ck"
            ),
            models.CheckConstraint(
                condition=models.Q(schema_version=1), name="%(app_label)s_subject_schema_v1"
            ),
            models.CheckConstraint(
                condition=models.Q(schedule_policy_version__isnull=True)
                | models.Q(schedule_policy_version__gte=1),
                name="%(app_label)s_subject_sched_ver",
            ),
        ]

    def validate_reviewer(self, reviewer_id):
        if (
            not self.semantic_author_id
            or not self.submitter_id
            or (not self.original_creator_id and not self.adopted_snapshot)
        ):
            raise ValidationError("review_provenance_unresolved")
        if not reviewer_id or reviewer_id in {
            self.original_creator_id,
            self.semantic_author_id,
            self.submitter_id,
        }:
            raise ValidationError("independent_reviewer_required")


class ReviewApproval(WorkspaceScopedState):
    subject_revision = models.UUIDField()
    semantic_generation = models.PositiveBigIntegerField(default=1)
    fingerprint = models.CharField(max_length=64, validators=[RegexValidator(r"^[a-f0-9]{64}$")])
    policy_version = models.PositiveBigIntegerField()
    reviewer_id = models.UUIDField()
    approved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True
        constraints = [
            *WorkspaceScopedState.Meta.constraints,
            models.CheckConstraint(
                condition=models.Q(fingerprint__regex=r"^[a-f0-9]{64}$"),
                name="%(app_label)s_approval_hash_ck",
            ),
            models.CheckConstraint(
                condition=models.Q(semantic_generation__gte=1), name="%(app_label)s_approval_gen_ck"
            ),
            models.CheckConstraint(
                condition=models.Q(policy_version__gte=1), name="%(app_label)s_approval_policy_v"
            ),
        ]


class ReviewDigestBatch(WorkspaceScopedState):
    recipient_id = models.UUIDField()
    digest_date = models.DateField()
    status = models.CharField(
        max_length=16,
        default="open",
        choices=[(v, v) for v in ("open", "closed", "delivered", "failed")],
    )
    closed_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True
        constraints = [
            *WorkspaceScopedState.Meta.constraints,
            models.UniqueConstraint(
                fields=("site_id", "recipient_id", "digest_date"),
                name="%(app_label)s_digest_day_uq",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=("open", "closed", "delivered", "failed")),
                name="%(app_label)s_digest_state_ck",
            ),
        ]


class ReviewNotificationIntent(WorkspaceScopedState):
    submission_id = models.UUIDField()
    subject_revision = models.UUIDField()
    recipient_id = models.UUIDField()
    channel = models.CharField(max_length=16, default="email", choices=[("email", "Email")])
    event = models.CharField(
        max_length=24,
        default="review_requested",
        choices=[("review_requested", "Review requested")],
    )
    status = models.CharField(
        max_length=16,
        default="pending",
        choices=[(v, v) for v in ("pending", "digest", "delivered", "suppressed", "failed")],
    )
    attempts = models.PositiveSmallIntegerField(default=0, validators=[MaxValueValidator(8)])
    available_at = models.DateTimeField(default=timezone.now)
    delivered_at = models.DateTimeField(null=True, blank=True)
    last_error_code = models.CharField(max_length=96, default="", blank=True)

    class Meta:
        abstract = True
        constraints = [
            *WorkspaceScopedState.Meta.constraints,
            models.UniqueConstraint(
                fields=("site_id", "submission_id", "recipient_id", "channel"),
                name="%(app_label)s_review_intent_uq",
            ),
            models.CheckConstraint(
                condition=models.Q(channel="email"), name="%(app_label)s_review_email_ck"
            ),
            models.CheckConstraint(
                condition=models.Q(event="review_requested"), name="%(app_label)s_review_event_ck"
            ),
            models.CheckConstraint(
                condition=models.Q(
                    status__in=("pending", "digest", "delivered", "suppressed", "failed")
                ),
                name="%(app_label)s_intent_state_ck",
            ),
            models.CheckConstraint(
                condition=models.Q(attempts__lte=8), name="%(app_label)s_intent_attempt_ck"
            ),
        ]


class ReviewNotificationDelivery(WorkspaceScopedState):
    """Durable local-only effect receipt; contains no copied private content."""

    recipient_id = models.UUIDField()
    effect_key = models.CharField(max_length=160, unique=True)
    delivered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True
        constraints = WorkspaceScopedState.Meta.constraints
