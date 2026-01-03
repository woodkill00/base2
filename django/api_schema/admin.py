from django.contrib import admin

from .models import (
    ApiAuthAuditEvent,
    ApiAuthOAuthAccount,
    ApiAuthOneTimeToken,
    ApiAuthRefreshToken,
    ApiAuthUser,
    ApiEmailOutbox,
)


@admin.register(ApiAuthUser)
class ApiAuthUserAdmin(admin.ModelAdmin):
    list_display = ("email", "is_active", "is_email_verified", "failed_login_attempts", "locked_until", "created_at")
    search_fields = ("email",)
    list_filter = ("is_active", "is_email_verified")


@admin.register(ApiAuthRefreshToken)
class ApiAuthRefreshTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "expires_at", "revoked_at", "last_seen_at", "created_at")
    search_fields = ("token_hash", "user__email")
    list_filter = ("revoked_at",)


@admin.register(ApiAuthOneTimeToken)
class ApiAuthOneTimeTokenAdmin(admin.ModelAdmin):
    list_display = ("type", "user", "expires_at", "consumed_at", "created_at")
    search_fields = ("token_hash", "user__email")
    list_filter = ("type", "consumed_at")


@admin.register(ApiAuthAuditEvent)
class ApiAuthAuditEventAdmin(admin.ModelAdmin):
    list_display = ("action", "user", "ip", "created_at")
    search_fields = ("action", "user__email", "ip")
    list_filter = ("action", "created_at")
    ordering = ("-created_at",)


@admin.register(ApiAuthOAuthAccount)
class ApiAuthOAuthAccountAdmin(admin.ModelAdmin):
    list_display = ("provider", "provider_account_id", "user", "email", "created_at")
    search_fields = ("provider", "provider_account_id", "user__email", "email")
    list_filter = ("provider",)


@admin.register(ApiEmailOutbox)
class ApiEmailOutboxAdmin(admin.ModelAdmin):
    list_display = ("to_email", "subject", "status", "provider", "created_at", "sent_at")
    search_fields = ("to_email", "subject", "provider_message_id")
    list_filter = ("status", "provider")
    ordering = ("-created_at",)
