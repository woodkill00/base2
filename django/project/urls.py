from django.contrib import admin
from django.http import JsonResponse
from django.urls import path
from django.views.generic import RedirectView

from project.views import internal_health


def health_view(_request):
    return JsonResponse({"ok": True, "service": "django"})


urlpatterns = [
    path("", RedirectView.as_view(url="/admin/", permanent=False)),
    path("admin/", admin.site.urls),
    path("internal/health", internal_health),
    path("health", health_view),
]
