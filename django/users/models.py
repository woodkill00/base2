from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from common.models import (
    Address,
    Email,
    Phonenumber,
    TimestampedModel,
    Url,
    UUIDMixin,
)

AuthUser = get_user_model()


class Organization(UUIDMixin, TimestampedModel):
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=80, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("slug",)


class Membership(UUIDMixin, TimestampedModel):
    class Role(models.TextChoices):
        OWNER = "owner", _("Owner")
        ADMIN = "admin", _("Administrator")
        EDITOR = "editor", _("Editor")
        VIEWER = "viewer", _("Viewer")

    class Status(models.TextChoices):
        ACTIVE = "active", _("Active")
        SUSPENDED = "suspended", _("Suspended")

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="memberships"
    )
    user = models.ForeignKey(
        AuthUser, on_delete=models.CASCADE, related_name="organization_memberships"
    )
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.VIEWER)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("organization", "user"), name="users_membership_org_user_uniq"
            )
        ]
        indexes = [
            models.Index(
                fields=("organization", "role", "status"), name="users_membership_role_idx"
            )
        ]


class Invitation(UUIDMixin, TimestampedModel):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="invitations"
    )
    email = models.EmailField(max_length=255)
    role = models.CharField(max_length=16, choices=Membership.Role.choices)
    token_hash = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(
                fields=("organization", "email", "expires_at"), name="users_invite_lookup_idx"
            )
        ]


class Authenticator(UUIDMixin, TimestampedModel):
    class Kind(models.TextChoices):
        TOTP = "totp", _("TOTP")
        WEBAUTHN = "webauthn", _("WebAuthn")

    user = models.ForeignKey(AuthUser, on_delete=models.CASCADE, related_name="authenticators")
    kind = models.CharField(max_length=16, choices=Kind.choices)
    credential_id = models.CharField(max_length=512, blank=True, default="")
    secret_ciphertext = models.TextField()
    is_active = models.BooleanField(default=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("user", "kind", "credential_id"), name="users_authenticator_uniq"
            )
        ]


class UserSession(UUIDMixin, TimestampedModel):
    user = models.ForeignKey(AuthUser, on_delete=models.CASCADE, related_name="managed_sessions")
    token_hash = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default="")

    class Meta:
        indexes = [
            models.Index(
                fields=("user", "revoked_at", "expires_at"), name="users_session_active_idx"
            )
        ]


class ApiCredential(UUIDMixin, TimestampedModel):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="api_credentials"
    )
    user = models.ForeignKey(
        AuthUser, on_delete=models.CASCADE, related_name="managed_api_credentials"
    )
    label = models.CharField(max_length=120)
    prefix = models.CharField(max_length=32, unique=True)
    secret_hash = models.CharField(max_length=64, unique=True)
    scopes = models.JSONField(default=list)
    expires_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=("organization", "revoked_at"), name="users_credential_active_idx")
        ]


class UserProfile(UUIDMixin, TimestampedModel):
    user = models.OneToOneField(AuthUser, on_delete=models.CASCADE, related_name="profile")
    display_name = models.CharField(max_length=150, blank=True, default="")
    avatar_url = models.URLField(blank=True, default="")
    bio = models.TextField(blank=True, default="")

    class Meta:
        verbose_name = _("User Profile")
        verbose_name_plural = _("User Profiles")

    def __str__(self):
        return self.display_name or getattr(self.user, "username", "user")


class UserPreferenceSet(UUIDMixin, TimestampedModel):
    class Theme(models.TextChoices):
        SYSTEM = "system", _("System")
        LIGHT = "light", _("Light")
        DARK = "dark", _("Dark")

    class Contrast(models.TextChoices):
        SYSTEM = "system", _("System")
        STANDARD = "standard", _("Standard")
        HIGH = "high", _("High contrast")

    class Motion(models.TextChoices):
        SYSTEM = "system", _("System")
        FULL = "full", _("Full motion")
        REDUCED = "reduced", _("Reduced motion")

    class Density(models.TextChoices):
        COMFORTABLE = "comfortable", _("Comfortable")
        COMPACT = "compact", _("Compact")

    class WeekStart(models.TextChoices):
        SYSTEM = "system", _("System")
        MONDAY = "monday", _("Monday")
        SUNDAY = "sunday", _("Sunday")
        SATURDAY = "saturday", _("Saturday")

    user = models.ForeignKey(AuthUser, on_delete=models.CASCADE, related_name="preference_sets")
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="user_preference_sets",
        null=True,
        blank=True,
    )
    schema_version = models.PositiveSmallIntegerField(default=1)
    version = models.PositiveIntegerField(default=1)
    theme = models.CharField(max_length=16, choices=Theme.choices, default=Theme.SYSTEM)
    contrast = models.CharField(max_length=16, choices=Contrast.choices, default=Contrast.SYSTEM)
    motion = models.CharField(max_length=16, choices=Motion.choices, default=Motion.SYSTEM)
    density = models.CharField(
        max_length=16, choices=Density.choices, default=Density.COMFORTABLE
    )
    locale = models.CharField(max_length=32, default="en")
    timezone = models.CharField(max_length=255, default="UTC")
    week_start = models.CharField(
        max_length=16, choices=WeekStart.choices, default=WeekStart.SYSTEM
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("user",),
                condition=models.Q(organization__isnull=True),
                name="users_preferences_user_default_uniq",
            ),
            models.UniqueConstraint(
                fields=("user", "organization"),
                condition=models.Q(organization__isnull=False),
                name="users_preferences_owner_uniq",
            ),
            models.CheckConstraint(
                condition=models.Q(schema_version=1), name="users_preferences_schema_v1"
            ),
            models.CheckConstraint(condition=models.Q(version__gte=1), name="users_preferences_ver_gte1"),
        ]
        indexes = [models.Index(fields=("user", "organization"), name="users_preferences_owner_idx")]


class NotificationPreference(UUIDMixin, TimestampedModel):
    class EventFamily(models.TextChoices):
        SECURITY = "security", _("Security")
        TRANSACTIONAL = "transactional", _("Transactional")
        PRODUCT = "product", _("Product")
        MARKETING = "marketing", _("Marketing")

    class Channel(models.TextChoices):
        EMAIL = "email", _("Email")
        IN_APP = "in_app", _("In app")
        BROWSER = "browser", _("Browser")

    class Delivery(models.TextChoices):
        IMMEDIATE = "immediate", _("Immediate")
        DIGEST = "digest", _("Digest")
        DISABLED = "disabled", _("Disabled")

    user = models.ForeignKey(
        AuthUser, on_delete=models.CASCADE, related_name="notification_preferences"
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="notification_preferences",
        null=True,
        blank=True,
    )
    event_family = models.CharField(max_length=24, choices=EventFamily.choices)
    channel = models.CharField(max_length=16, choices=Channel.choices)
    delivery = models.CharField(max_length=16, choices=Delivery.choices)
    mandatory = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("user", "event_family", "channel"),
                condition=models.Q(organization__isnull=True),
                name="users_notification_user_default_uniq",
            ),
            models.UniqueConstraint(
                fields=("user", "organization", "event_family", "channel"),
                condition=models.Q(organization__isnull=False),
                name="users_notification_owner_family_channel_uniq",
            ),
            models.CheckConstraint(
                condition=models.Q(mandatory=False) | ~models.Q(delivery="disabled"),
                name="users_notification_mandatory_delivery",
            ),
        ]
        indexes = [
            models.Index(
                fields=("user", "organization", "event_family"),
                name="users_notification_owner_idx",
            )
        ]


class EmailAddress(Email, TimestampedModel):
    user = models.ForeignKey(AuthUser, on_delete=models.CASCADE, related_name="emails")
    is_primary = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    verification_token = models.CharField(max_length=255, blank=True, default="")
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _("Email Address")
        verbose_name_plural = _("Email Addresses")
        indexes = [models.Index(fields=["email", "user"])]


class PhoneNumber(Phonenumber, TimestampedModel):
    class Type(models.TextChoices):
        MOBILE = "mobile", _("Mobile")
        HOME = "home", _("Home")
        WORK = "work", _("Work")

    user = models.ForeignKey(AuthUser, on_delete=models.CASCADE, related_name="phones")
    type = models.CharField(max_length=20, choices=Type.choices, default=Type.MOBILE)
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _("Phone Number")
        verbose_name_plural = _("Phone Numbers")


class UserAddress(Address, TimestampedModel):
    class Type(models.TextChoices):
        BILLING = "billing", _("Billing")
        SHIPPING = "shipping", _("Shipping")
        HOME = "home", _("Home")
        OTHER = "other", _("Other")

    user = models.ForeignKey(AuthUser, on_delete=models.CASCADE, related_name="addresses")
    type = models.CharField(max_length=20, choices=Type.choices, default=Type.HOME)
    is_primary = models.BooleanField(default=False)

    class Meta:
        verbose_name = _("User Address")
        verbose_name_plural = _("User Addresses")


class UserUrl(Url, TimestampedModel):
    class Type(models.TextChoices):
        WEBSITE = "website", _("Website")
        LINKEDIN = "linkedin", _("LinkedIn")
        GITHUB = "github", _("GitHub")
        OTHER = "other", _("Other")

    user = models.ForeignKey(AuthUser, on_delete=models.CASCADE, related_name="urls")
    type = models.CharField(max_length=20, choices=Type.choices, default=Type.WEBSITE)
    is_public = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("User URL")
        verbose_name_plural = _("User URLs")


class ApiToken(UUIDMixin, TimestampedModel):
    user = models.ForeignKey(AuthUser, on_delete=models.CASCADE, related_name="api_tokens")
    token_hash = models.CharField(max_length=255, unique=True)
    scope = models.CharField(max_length=255, blank=True, default="")
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("API Token")
        verbose_name_plural = _("API Tokens")
        indexes = [models.Index(fields=["user", "is_active"])]


class OAuthAccount(UUIDMixin, TimestampedModel):
    user = models.ForeignKey(AuthUser, on_delete=models.CASCADE, related_name="oauth_accounts")
    provider = models.CharField(max_length=50)
    provider_user_id = models.CharField(max_length=255)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _("OAuth Account")
        verbose_name_plural = _("OAuth Accounts")
        unique_together = ("provider", "provider_user_id")


class RecoveryCode(UUIDMixin, TimestampedModel):
    user = models.ForeignKey(AuthUser, on_delete=models.CASCADE, related_name="recovery_codes")
    code_hash = models.CharField(max_length=255, unique=True)
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _("Recovery Code")
        verbose_name_plural = _("Recovery Codes")


class AuditEvent(TimestampedModel):
    actor_user = models.ForeignKey(
        AuthUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_events",
    )
    action = models.CharField(max_length=100)
    target_type = models.CharField(max_length=100, blank=True, default="")
    target_id = models.CharField(max_length=100, blank=True, default="")
    ip = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, default="")
    metadata = models.JSONField(blank=True, null=True)

    class Meta:
        verbose_name = _("Audit Event")
        verbose_name_plural = _("Audit Events")
        indexes = [
            # Common query patterns: per-user audit trail, per-action filtering, and recent events.
            models.Index(fields=["action", "actor_user"], name="users_audit_action_idx"),
            models.Index(fields=["actor_user"], name="users_audit_actor_idx"),
            models.Index(fields=["action"], name="users_audit_action_only_idx"),
            models.Index(fields=["created"], name="users_audit_created_idx"),
        ]

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("audit_event_append_only")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("audit_event_append_only")


class EmailOutbox(UUIDMixin, TimestampedModel):
    to = models.EmailField(max_length=255)
    subject = models.CharField(max_length=255)
    body = models.TextField()
    sent_at = models.DateTimeField(null=True, blank=True)
    provider_message_id = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        verbose_name = _("Email Outbox")
        verbose_name_plural = _("Email Outbox")
        indexes = [models.Index(fields=["to", "sent_at"])]


class OneTimeToken(UUIDMixin, TimestampedModel):
    class Purpose(models.TextChoices):
        EMAIL_VERIFICATION = "email_verification", _("Email verification")
        PASSWORD_RESET = "password_reset", _("Password reset")

    user = models.ForeignKey(AuthUser, on_delete=models.CASCADE, related_name="one_time_tokens")
    purpose = models.CharField(max_length=50, choices=Purpose.choices)
    email = models.EmailField(max_length=255)
    token_hash = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    consumed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _("One Time Token")
        verbose_name_plural = _("One Time Tokens")
        indexes = [
            models.Index(fields=["purpose", "email"]),
            models.Index(fields=["user", "purpose"]),
            models.Index(fields=["purpose", "consumed_at"]),
        ]
