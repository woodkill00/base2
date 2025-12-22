from django.contrib import admin
from django.http import JsonResponse
from django.urls import path, include


def health_view(_request):
    return JsonResponse({"ok": True, "service": "django"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("internal/users/", include("users.urls")),
    path("internal/catalog/", include("catalog.urls")),
    path("health", health_view),
]
