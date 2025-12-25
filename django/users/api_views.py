import json

from django.contrib.auth import authenticate, get_user_model, login, logout
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.csrf import csrf_exempt, csrf_protect

from users.models import AuditEvent, UserProfile

AuthUser = get_user_model()


def _request_ip(request) -> str | None:
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _audit(request, *, action: str, actor_user=None, target_type: str = "", target_id: str = "", metadata=None):
    AuditEvent.objects.create(
        actor_user=actor_user,
        action=action,
        target_type=target_type,
        target_id=target_id,
        ip=_request_ip(request),
        user_agent=request.META.get("HTTP_USER_AGENT", ""),
        metadata=metadata or {},
    )


def csrf_bootstrap(request):
    # Ensure CSRF cookie is set
    get_token(request)
    return JsonResponse({"detail": "ok"})


def _user_me_payload(user):
    profile = getattr(user, "profile", None)
    return {
        "id": str(getattr(user, "id", "")),
        "email": getattr(user, "email", ""),
        "display_name": getattr(profile, "display_name", "") if profile else "",
        "avatar_url": getattr(profile, "avatar_url", "") if profile else "",
        "bio": getattr(profile, "bio", "") if profile else "",
    }


@csrf_exempt
def signup(request):
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        payload = {}

    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password")
    username = (payload.get("username") or email).strip()

    if not email or not password:
        return JsonResponse({"detail": "Invalid signup"}, status=400)

    if AuthUser.objects.filter(email=email).exists():
        return JsonResponse({"detail": "Invalid signup"}, status=400)

    try:
        user = AuthUser.objects.create_user(username=username, email=email, password=password)
    except Exception:
        return JsonResponse({"detail": "Invalid signup"}, status=400)

    UserProfile.objects.get_or_create(user=user)

    login(request, user)
    get_token(request)
    _audit(request, action="auth.signup", actor_user=user, target_type="user", target_id=str(user.id), metadata={"email": email})

    return JsonResponse(_user_me_payload(user), status=201)


@csrf_exempt
def login_view(request):
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        payload = {}

    email = (payload.get("email") or "").strip().lower()
    username = (payload.get("username") or "").strip()
    password = payload.get("password")

    # Support login by email or username, but keep errors generic.
    if email and not username:
        user_obj = AuthUser.objects.filter(email=email).first()
        username = getattr(user_obj, "username", "") if user_obj else ""

    if not username or not password:
        return JsonResponse({"detail": "Invalid credentials"}, status=400)

    user = authenticate(request, username=username, password=password)
    if user is None:
        _audit(request, action="auth.login.failure", actor_user=None, target_type="user", target_id="", metadata={"email": email or None})
        return JsonResponse({"detail": "Invalid credentials"}, status=401)

    login(request, user)
    get_token(request)
    _audit(request, action="auth.login.success", actor_user=user, target_type="user", target_id=str(user.id), metadata={"email": getattr(user, "email", "")})

    return JsonResponse(_user_me_payload(user), status=200)


@csrf_protect
def logout_view(request):
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    if not request.user.is_authenticated:
        return JsonResponse({"detail": "Not authenticated"}, status=401)

    actor = request.user
    logout(request)
    _audit(request, action="auth.logout", actor_user=actor, target_type="user", target_id=str(getattr(actor, "id", "")))

    return JsonResponse({}, status=204)


@csrf_protect
def me(request):
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "Not authenticated"}, status=401)

    user = request.user
    UserProfile.objects.get_or_create(user=user)

    if request.method == "GET":
        return JsonResponse(_user_me_payload(user), status=200)

    if request.method != "PATCH":
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        payload = {}

    profile = user.profile
    for field in ("display_name", "avatar_url", "bio"):
        if field in payload:
            setattr(profile, field, payload.get(field) or "")
    profile.save()

    _audit(request, action="profile.updated", actor_user=user, target_type="user", target_id=str(user.id), metadata={"fields": list(payload.keys())})

    return JsonResponse(_user_me_payload(user), status=200)
