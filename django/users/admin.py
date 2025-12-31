from django.contrib import admin

from .models import (
    ApiToken,
    AuditEvent,
    EmailAddress,
    OAuthAccount,
    PhoneNumber,
    RecoveryCode,
    UserAddress,
    UserProfile,
    UserUrl,
)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "display_name", "created", "updated")

@admin.register(EmailAddress)
class EmailAddressAdmin(admin.ModelAdmin):
    list_display = ("user", "email", "is_primary", "is_verified", "created")
    list_filter = ("is_primary", "is_verified")

@admin.register(PhoneNumber)
class PhoneNumberAdmin(admin.ModelAdmin):
    list_display = ("user", "phonenumber", "type", "is_verified")

@admin.register(UserAddress)
class UserAddressAdmin(admin.ModelAdmin):
    list_display = ("user", "type", "city", "state", "country")

@admin.register(UserUrl)
class UserUrlAdmin(admin.ModelAdmin):
    list_display = ("user", "address", "type", "is_public")

@admin.register(ApiToken)
class ApiTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "scope", "is_active", "expires_at")

@admin.register(OAuthAccount)
class OAuthAccountAdmin(admin.ModelAdmin):
    list_display = ("user", "provider", "provider_user_id", "expires_at")

@admin.register(RecoveryCode)
class RecoveryCodeAdmin(admin.ModelAdmin):
    list_display = ("user", "used_at")

@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = (
        "actor_email",
        "action",
        "ip",
        "short_user_agent",
        "target_type",
        "target_id",
        "created",
    )
    list_filter = ("action", "target_type", "created")
    search_fields = (
        "actor_user__email",
        "actor_user__username",
        "action",
        "target_type",
        "target_id",
        "ip",
        "user_agent",
    )
    ordering = ("-created",)
    list_select_related = ("actor_user",)

    @admin.display(description="Actor")
    def actor_email(self, obj):
        user = getattr(obj, "actor_user", None)
        if not user:
            return ""
        return (
            getattr(user, "email", "")
            or getattr(user, "username", "")
            or str(getattr(user, "id", ""))
        )

    @admin.display(description="User agent")
    def short_user_agent(self, obj):
        ua = (getattr(obj, "user_agent", "") or "").strip()
        if len(ua) <= 60:
            return ua
        return ua[:57] + "..."
