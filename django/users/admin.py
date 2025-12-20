from django.contrib import admin
from .models import UserProfile, EmailAddress, PhoneNumber, UserAddress, UserUrl, ApiToken, OAuthAccount, RecoveryCode, AuditEvent

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
    list_display = ("actor_user", "action", "target_type", "created")
