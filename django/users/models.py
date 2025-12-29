from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from common.models import (
    TimestampedModel,
    UUIDMixin,
    Email,
    Phonenumber,
    Address,
    Url,
)

AuthUser = get_user_model()

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
        indexes = [models.Index(fields=["user", "is_active"]) ]


class OAuthAccount(UUIDMixin, TimestampedModel):
    user = models.ForeignKey(AuthUser, on_delete=models.CASCADE, related_name="oauth_accounts")
    provider = models.CharField(max_length=50)
    provider_user_id = models.CharField(max_length=255)
    access_token = models.TextField(blank=True, default="")
    refresh_token = models.TextField(blank=True, default="")
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
    actor_user = models.ForeignKey(AuthUser, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_events")
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
