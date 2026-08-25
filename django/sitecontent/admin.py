from django.contrib import admin
from django.core.exceptions import PermissionDenied

from .models import (
    ContentRecord,
    ContentRevision,
    FormDeliveryOutbox,
    FormSubmission,
    MediaAsset,
    MediaVariant,
    RedirectRule,
    SearchDocument,
)


class TenantScopedAdmin(admin.ModelAdmin):
    tenant_filter = "site_id"

    def _allowed_sites(self, request):
        if not request.user.is_authenticated:
            return []
        return list(
            request.user.organization_memberships.filter(
                status="active", organization__is_active=True
            ).values_list("organization__slug", flat=True)
        )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.is_superuser:
            return queryset
        return queryset.filter(**{f"{self.tenant_filter}__in": self._allowed_sites(request)})

    def _site_id(self, obj):
        current = obj
        for part in self.tenant_filter.split("__"):
            current = getattr(current, part)
        return str(current)

    def has_view_permission(self, request, obj=None):
        base = super().has_view_permission(request, obj)
        return base and (
            obj is None
            or request.user.is_superuser
            or self._site_id(obj) in self._allowed_sites(request)
        )

    def has_change_permission(self, request, obj=None):
        base = super().has_change_permission(request, obj)
        return base and (
            obj is None
            or request.user.is_superuser
            or self._site_id(obj) in self._allowed_sites(request)
        )

    def has_delete_permission(self, request, obj=None):
        base = super().has_delete_permission(request, obj)
        return base and (
            obj is None
            or request.user.is_superuser
            or self._site_id(obj) in self._allowed_sites(request)
        )

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser and self._site_id(obj) not in self._allowed_sites(request):
            raise PermissionDenied("cross_tenant_forbidden")
        return super().save_model(request, obj, form, change)


class ContentRevisionAdmin(TenantScopedAdmin):
    tenant_filter = "content__site_id"


class FormDeliveryOutboxAdmin(TenantScopedAdmin):
    tenant_filter = "submission__site_id"


class MediaVariantAdmin(TenantScopedAdmin):
    tenant_filter = "asset__site_id"


admin.site.register(ContentRecord, TenantScopedAdmin)
admin.site.register(ContentRevision, ContentRevisionAdmin)
admin.site.register(FormSubmission, TenantScopedAdmin)
admin.site.register(FormDeliveryOutbox, FormDeliveryOutboxAdmin)
admin.site.register(MediaAsset, TenantScopedAdmin)
admin.site.register(MediaVariant, MediaVariantAdmin)
admin.site.register(RedirectRule, TenantScopedAdmin)
admin.site.register(SearchDocument, TenantScopedAdmin)
