from __future__ import annotations

from django.db import models


class ApiAuthUser(models.Model):
    id = models.UUIDField(primary_key=True)
    email = models.TextField(unique=True)
    password_hash = models.TextField()
    is_active = models.BooleanField(default=True)
    is_email_verified = models.BooleanField(default=False)
    display_name = models.TextField(default="", blank=True)
    avatar_url = models.TextField(default="", blank=True)
    bio = models.TextField(default="", blank=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    failed_login_attempts = models.IntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = "api_auth_users"

    def __str__(self) -> str:
        return self.email


class ApiAuthRefreshToken(models.Model):
    id = models.UUIDField(primary_key=True)
    user = models.ForeignKey(
        ApiAuthUser,
        to_field="id",
        db_column="user_id",
        on_delete=models.CASCADE,
        related_name="refresh_tokens",
    )
    token_hash = models.TextField()
    created_at = models.DateTimeField()
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    replaced_by_token_id = models.UUIDField(null=True, blank=True)
    user_agent = models.TextField(default="", blank=True)
    ip = models.TextField(default="", blank=True)
    last_seen_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "api_auth_refresh_tokens"


class ApiAuthOneTimeToken(models.Model):
    id = models.UUIDField(primary_key=True)
    user = models.ForeignKey(
        ApiAuthUser,
        to_field="id",
        db_column="user_id",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="one_time_tokens",
    )
    token_hash = models.TextField()
    type = models.TextField()
    created_at = models.DateTimeField()
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = "api_auth_one_time_tokens"


class ApiAuthAuditEvent(models.Model):
    id = models.UUIDField(primary_key=True)
    user = models.ForeignKey(
        ApiAuthUser,
        to_field="id",
        db_column="user_id",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_events",
    )
    action = models.TextField()
    ip = models.TextField(default="", blank=True)
    user_agent = models.TextField(default="", blank=True)
    metadata_json = models.JSONField(default=dict)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "api_auth_audit_events"


class ApiAuthOAuthAccount(models.Model):
    id = models.UUIDField(primary_key=True)
    user = models.ForeignKey(
        ApiAuthUser,
        to_field="id",
        db_column="user_id",
        on_delete=models.CASCADE,
        related_name="oauth_accounts",
    )
    provider = models.TextField()
    provider_account_id = models.TextField()
    email = models.TextField(default="", blank=True)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "api_auth_oauth_accounts"


class ApiEmailOutbox(models.Model):
    id = models.UUIDField(primary_key=True)
    to_email = models.TextField()
    subject = models.TextField()
    body_text = models.TextField()
    body_html = models.TextField(default="", blank=True)
    status = models.TextField(default="queued")
    provider = models.TextField(default="local_outbox")
    provider_message_id = models.TextField(default="", blank=True)
    error = models.TextField(default="", blank=True)
    created_at = models.DateTimeField()
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = "api_email_outbox"
