import pytest


@pytest.mark.django_db
def test_internal_auth_api_not_mounted(client):
    # Django should no longer expose auth endpoints (even internally);
    # FastAPI owns the /api/auth/* public surface end-to-end.
    r = client.get("/internal/api/users/login")
    assert r.status_code == 404
