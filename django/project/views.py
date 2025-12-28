from django.db import connections
from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def internal_health(_request):
    db_ok = True
    try:
        connections["default"].ensure_connection()
    except Exception:
        db_ok = False

    return JsonResponse({"ok": bool(db_ok), "service": "django", "db_ok": bool(db_ok)})
