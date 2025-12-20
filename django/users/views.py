import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model

AuthUser = get_user_model()


def users_list(request):
    qs = AuthUser.objects.all().order_by("id")[:100]
    data = [
        {
            "id": u.id,
            "username": getattr(u, "username", None),
            "email": getattr(u, "email", None),
            "is_staff": u.is_staff,
            "is_superuser": u.is_superuser,
        }
        for u in qs
    ]
    return JsonResponse({"users": data})


def me(request):
    if request.user.is_authenticated:
        u = request.user
        return JsonResponse(
            {
                "authenticated": True,
                "user": {
                    "id": u.id,
                    "username": getattr(u, "username", None),
                    "email": getattr(u, "email", None),
                    "is_staff": u.is_staff,
                },
            }
        )
    return JsonResponse({"authenticated": False, "user": None})


@csrf_exempt
def login_view(request):
    if request.method != "POST":
        return JsonResponse({"error": "method_not_allowed"}, status=405)
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        payload = {}
    email = payload.get("email")
    username = payload.get("username")
    password = payload.get("password")

    # Support login by username or email
    if email and not username:
        try:
            user_obj = AuthUser.objects.filter(email=email).first()
            username = getattr(user_obj, "username", None)
        except Exception:
            username = None
    if not username or not password:
        return JsonResponse({"error": "missing_credentials"}, status=400)

    user = authenticate(request, username=username, password=password)
    if user is None:
        return JsonResponse({"error": "invalid_credentials"}, status=401)
    login(request, user)
    return JsonResponse({
        "success": True,
        "user": {
            "id": user.id,
            "username": getattr(user, "username", None),
            "email": getattr(user, "email", None),
            "is_staff": user.is_staff,
        }
    })


@csrf_exempt
def logout_view(request):
    if request.method != "POST":
        return JsonResponse({"error": "method_not_allowed"}, status=405)
    logout(request)
    return JsonResponse({"success": True})
