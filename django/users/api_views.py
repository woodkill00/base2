import json
import base64
import hashlib
import hmac
import os
import secrets
import time
from urllib.parse import urlencode
from urllib.request import Request as UrlRequest, urlopen

from django.contrib.auth import authenticate, get_user_model, login, logout
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.csrf import csrf_exempt, csrf_protect

from users.models import AuditEvent, OAuthAccount, UserProfile

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


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def _b64url_decode(raw: str) -> bytes:
    pad = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(raw + pad)


def _oauth_config():
    client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "")
    client_secret = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "")
    redirect_uri = os.environ.get("GOOGLE_OAUTH_REDIRECT_URI", "")
    state_secret = os.environ.get("OAUTH_STATE_SECRET", "")
    if not client_id or not client_secret or not redirect_uri or not state_secret:
        raise ValueError("OAuth is not configured")
    return client_id, client_secret, redirect_uri, state_secret


def _oauth_next_allowlisted(next_path: str) -> bool:
    # Keep allowlist strict to avoid open redirects.
    return next_path in {"/dashboard"}


def _oauth_state_sign(payload_json: bytes, *, state_secret: str) -> str:
    sig = hmac.new(state_secret.encode("utf-8"), payload_json, hashlib.sha256).digest()
    return _b64url_encode(sig)


def _oauth_state_mint(request, *, next_path: str, state_secret: str) -> str:
    nonce = secrets.token_urlsafe(24)
    issued_at = int(time.time())
    payload = {"n": nonce, "t": issued_at, "next": next_path}
    payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    sig = _oauth_state_sign(payload_json, state_secret=state_secret)

    # Bind to this browser session as an extra CSRF/replay mitigation.
    request.session["oauth_state_nonce"] = nonce
    request.session["oauth_state_issued_at"] = issued_at

    return f"{_b64url_encode(payload_json)}.{sig}"


def _oauth_state_validate(request, *, state: str, state_secret: str) -> dict:
    try:
        payload_b64, sig_b64 = state.split(".", 1)
    except ValueError:
        raise ValueError("Invalid state")

    payload_json = _b64url_decode(payload_b64)
    expected_sig = _oauth_state_sign(payload_json, state_secret=state_secret)
    if not hmac.compare_digest(expected_sig, sig_b64):
        raise ValueError("Invalid state")

    try:
        payload = json.loads(payload_json.decode("utf-8"))
    except Exception:
        raise ValueError("Invalid state")

    nonce = payload.get("n")
    issued_at = int(payload.get("t") or 0)
    next_path = payload.get("next") or "/dashboard"

    if not nonce or not issued_at:
        raise ValueError("Invalid state")

    # 10 minute expiry
    if int(time.time()) - issued_at > 600:
        raise ValueError("State expired")

    session_nonce = request.session.get("oauth_state_nonce")
    if not session_nonce or session_nonce != nonce:
        raise ValueError("Invalid state")

    if not _oauth_next_allowlisted(next_path):
        raise ValueError("Invalid redirect")

    return {"next": next_path, "issued_at": issued_at}


def _google_exchange_code_for_tokens(*, code: str, redirect_uri: str, client_id: str, client_secret: str) -> dict:
    # Separate helper so tests can monkeypatch without real network.
    url = "https://oauth2.googleapis.com/token"
    body = urlencode(
        {
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }
    ).encode("utf-8")

    req = UrlRequest(url, data=body, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urlopen(req, timeout=10) as resp:
            raw = resp.read().decode("utf-8")
    except Exception:
        raise ValueError("Token exchange failed")

    try:
        return json.loads(raw)
    except Exception:
        raise ValueError("Token exchange failed")


def _google_fetch_userinfo(*, access_token: str) -> dict:
    # Separate helper so tests can monkeypatch without real network.
    url = "https://openidconnect.googleapis.com/v1/userinfo"
    req = UrlRequest(url, method="GET")
    req.add_header("Authorization", f"Bearer {access_token}")
    try:
        with urlopen(req, timeout=10) as resp:
            raw = resp.read().decode("utf-8")
    except Exception:
        raise ValueError("Userinfo fetch failed")

    try:
        return json.loads(raw)
    except Exception:
        raise ValueError("Userinfo fetch failed")


@csrf_exempt
def oauth_google_start(request):
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        payload = {}

    next_path = (payload.get("next") or "/dashboard").strip()
    if not _oauth_next_allowlisted(next_path):
        return JsonResponse({"detail": "Invalid redirect"}, status=400)

    try:
        client_id, client_secret, redirect_uri, state_secret = _oauth_config()
    except ValueError as e:
        return JsonResponse({"detail": str(e)}, status=500)

    state = _oauth_state_mint(request, next_path=next_path, state_secret=state_secret)
    # See: https://developers.google.com/identity/protocols/oauth2/web-server
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(
        {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "offline",
            "include_granted_scopes": "true",
            "prompt": "consent",
        }
    )

    _audit(request, action="auth.oauth.google.start", actor_user=None, target_type="", target_id="", metadata={"next": next_path})
    return JsonResponse({"authorization_url": auth_url}, status=200)


@csrf_exempt
def oauth_google_callback(request):
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        payload = {}

    code = (payload.get("code") or "").strip()
    state = (payload.get("state") or "").strip()
    if not code or not state:
        return JsonResponse({"detail": "Invalid request"}, status=400)

    try:
        client_id, client_secret, redirect_uri, state_secret = _oauth_config()
    except ValueError as e:
        return JsonResponse({"detail": str(e)}, status=500)

    try:
        _oauth_state_validate(request, state=state, state_secret=state_secret)
    except ValueError as e:
        _audit(request, action="auth.oauth.google.failure", actor_user=None, target_type="", target_id="", metadata={"reason": str(e)})
        return JsonResponse({"detail": str(e)}, status=400)

    try:
        token_payload = _google_exchange_code_for_tokens(
            code=code,
            redirect_uri=redirect_uri,
            client_id=client_id,
            client_secret=client_secret,
        )
        access_token = (token_payload.get("access_token") or "").strip()
        if not access_token:
            raise ValueError("Token exchange failed")

        userinfo = _google_fetch_userinfo(access_token=access_token)
        provider_user_id = (userinfo.get("sub") or "").strip()
        email = (userinfo.get("email") or "").strip().lower()
        if not provider_user_id or not email:
            raise ValueError("Userinfo fetch failed")
    except ValueError as e:
        _audit(request, action="auth.oauth.google.failure", actor_user=None, target_type="", target_id="", metadata={"reason": str(e)})
        return JsonResponse({"detail": "OAuth failed"}, status=400)

    account = OAuthAccount.objects.filter(provider="google", provider_user_id=provider_user_id).select_related("user").first()
    user = None
    if account:
        user = account.user
    else:
        user = AuthUser.objects.filter(email=email).first()
        if user is None:
            base_username = email.split("@", 1)[0] or "user"
            base_username = "".join(ch for ch in base_username if ch.isalnum() or ch in {"_", ".", "-"})[:30] or "user"
            candidate = base_username
            suffix = 0
            while AuthUser.objects.filter(username=candidate).exists():
                suffix += 1
                candidate = f"{base_username}{suffix}"
            user = AuthUser.objects.create_user(username=candidate, email=email)
            user.set_unusable_password()
            user.save()

        UserProfile.objects.get_or_create(user=user)

        account = OAuthAccount.objects.create(
            user=user,
            provider="google",
            provider_user_id=provider_user_id,
            access_token=token_payload.get("access_token") or "",
            refresh_token=token_payload.get("refresh_token") or "",
        )

    login(request, user)
    get_token(request)
    _audit(
        request,
        action="auth.oauth.google.success",
        actor_user=user,
        target_type="user",
        target_id=str(getattr(user, "id", "")),
        metadata={"provider": "google", "email": email},
    )
    return JsonResponse(_user_me_payload(user), status=200)


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
