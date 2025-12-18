from django.urls import path
from django.http import JsonResponse


def internal_me(request):
    return JsonResponse({"ok": True, "user": "internal-placeholder"})

urlpatterns = [
    path("internal/users/me", internal_me),
]
