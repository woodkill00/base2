import pytest


@pytest.mark.django_db
@pytest.mark.parametrize(
    "path",
    [
        # Legacy internal API surface (should never be reintroduced).
        "/internal/api/users/login",
        "/internal/api/users/logout",
        "/internal/api/users/signup",
        "/internal/api/users/verify-email",
        "/internal/api/users/forgot-password",
        "/internal/api/users/reset-password",
        "/internal/api/users/me",
        "/internal/api/oauth/google/start",
        "/internal/api/oauth/google/callback",
        # Old internal Django endpoints (Django is admin/schema-only).
        "/internal/users/login/",
        "/internal/users/logout/",
    ],
)
def test_internal_auth_routes_not_mounted(client, path):
    # Django should not expose auth endpoints (even internally);
    # FastAPI owns the /api/auth/* public surface end-to-end.
    r_get = client.get(path)
    assert r_get.status_code == 404

    r_post = client.post(path, data={})
    assert r_post.status_code == 404
