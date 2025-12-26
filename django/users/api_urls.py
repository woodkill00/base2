from django.urls import path

from . import api_views


urlpatterns = [
    path("csrf", api_views.csrf_bootstrap),
    path("users/signup", api_views.signup),
    path("users/verify-email", api_views.verify_email),
    path("verify-email", api_views.verify_email),
    path("users/login", api_views.login_view),
    path("users/logout", api_views.logout_view),
    path("users/me", api_views.me),
    path("oauth/google/start", api_views.oauth_google_start),
    path("oauth/google/callback", api_views.oauth_google_callback),
]
