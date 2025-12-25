import json

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client


@pytest.fixture()
def client_csrf() -> Client:
    return Client(enforce_csrf_checks=True)


def _csrf_bootstrap(client: Client) -> str:
    r = client.get("/internal/api/csrf")
    assert r.status_code == 200
    assert settings.CSRF_COOKIE_NAME in client.cookies
    return client.cookies[settings.CSRF_COOKIE_NAME].value


@pytest.mark.django_db
def test_me_requires_auth(client_csrf: Client):
    r = client_csrf.get("/internal/api/users/me")
    assert r.status_code == 401
    assert "detail" in r.json()


@pytest.mark.django_db
def test_signup_creates_account_and_signs_in(client_csrf: Client):
    payload = {"email": "newuser@example.com", "password": "Test1234!"}
    r = client_csrf.post(
        "/internal/api/users/signup",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert r.status_code == 201
    j = r.json()
    assert j["email"] == "newuser@example.com"

    r2 = client_csrf.get("/internal/api/users/me")
    assert r2.status_code == 200
    assert r2.json()["email"] == "newuser@example.com"


@pytest.mark.django_db
def test_login_logout_flow_with_csrf(client_csrf: Client):
    AuthUser = get_user_model()
    AuthUser.objects.create_user(username="u1", email="u1@example.com", password="Test1234!")

    login_payload = {"email": "u1@example.com", "password": "Test1234!"}
    r = client_csrf.post(
        "/internal/api/users/login",
        data=json.dumps(login_payload),
        content_type="application/json",
    )
    assert r.status_code == 200
    assert r.json()["email"] == "u1@example.com"

    # logout without CSRF must be rejected
    r_no_csrf = client_csrf.post("/internal/api/users/logout")
    assert r_no_csrf.status_code == 403

    token = _csrf_bootstrap(client_csrf)
    r_logout = client_csrf.post(
        "/internal/api/users/logout",
        HTTP_X_CSRF_TOKEN=token,
    )
    assert r_logout.status_code == 204

    r_me = client_csrf.get("/internal/api/users/me")
    assert r_me.status_code == 401


@pytest.mark.django_db
def test_login_invalid_credentials_is_generic(client_csrf: Client):
    AuthUser = get_user_model()
    AuthUser.objects.create_user(username="u2", email="u2@example.com", password="Correct123!")

    r = client_csrf.post(
        "/internal/api/users/login",
        data=json.dumps({"email": "u2@example.com", "password": "Wrong123!"}),
        content_type="application/json",
    )
    assert r.status_code == 401
    j = r.json()
    assert "detail" in j


@pytest.mark.django_db
def test_signup_duplicate_email_is_generic(client_csrf: Client):
    payload = {"email": "dup@example.com", "password": "Test1234!"}

    r1 = client_csrf.post(
        "/internal/api/users/signup",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert r1.status_code == 201

    r2 = client_csrf.post(
        "/internal/api/users/signup",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert r2.status_code == 400
    j = r2.json()
    assert "detail" in j
