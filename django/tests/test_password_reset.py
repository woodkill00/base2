import json
from datetime import timedelta

import pytest
from django.contrib.auth import authenticate, get_user_model
from django.test import Client
from django.utils import timezone

from users.models import OneTimeToken
from users.tokens import mint_one_time_token


@pytest.mark.django_db
def test_forgot_password_is_enumeration_safe(monkeypatch):
    from users import tasks

    monkeypatch.setattr(tasks.send_password_reset_email, "delay", lambda **kwargs: "queued")

    client = Client()

    r1 = client.post(
        "/internal/api/users/forgot-password",
        data=json.dumps({"email": "doesnotexist@example.com"}),
        content_type="application/json",
    )
    assert r1.status_code == 200
    assert "detail" in r1.json()

    AuthUser = get_user_model()
    user = AuthUser.objects.create_user(username="u1", email="u1@example.com", password="Test1234!")

    r2 = client.post(
        "/internal/api/users/forgot-password",
        data=json.dumps({"email": "u1@example.com"}),
        content_type="application/json",
    )
    assert r2.status_code == 200
    assert r2.json()["detail"] == r1.json()["detail"]

    token = OneTimeToken.objects.filter(user=user, purpose=OneTimeToken.Purpose.PASSWORD_RESET).first()
    assert token is not None
    assert token.email == "u1@example.com"
    assert token.consumed_at is None


@pytest.mark.django_db
def test_reset_password_sets_password_and_consumes_token():
    AuthUser = get_user_model()
    user = AuthUser.objects.create_user(username="r1", email="r1@example.com", password="OldPass123!")

    raw, token = mint_one_time_token(
        user=user,
        purpose=OneTimeToken.Purpose.PASSWORD_RESET,
        email="r1@example.com",
        ttl=timedelta(hours=1),
    )

    client = Client()
    r = client.post(
        "/internal/api/users/reset-password",
        data=json.dumps({"token": raw, "password": "NewPass123!"}),
        content_type="application/json",
    )
    assert r.status_code == 200
    assert "detail" in r.json()

    user.refresh_from_db()
    assert authenticate(username=user.username, password="NewPass123!") is not None

    consumed = OneTimeToken.objects.get(uuid=token.uuid)
    assert consumed.consumed_at is not None


@pytest.mark.django_db
def test_reset_password_rejects_invalid_or_expired_token():
    client = Client()

    r1 = client.post(
        "/internal/api/users/reset-password",
        data=json.dumps({"token": "not-a-real-token", "password": "NewPass123!"}),
        content_type="application/json",
    )
    assert r1.status_code == 400
    assert "detail" in r1.json()

    AuthUser = get_user_model()
    user = AuthUser.objects.create_user(username="r2", email="r2@example.com", password="OldPass123!")
    raw, token = mint_one_time_token(
        user=user,
        purpose=OneTimeToken.Purpose.PASSWORD_RESET,
        email="r2@example.com",
        ttl=timedelta(hours=1),
    )
    OneTimeToken.objects.filter(uuid=token.uuid).update(expires_at=timezone.now() - timedelta(minutes=1))

    r2 = client.post(
        "/internal/api/users/reset-password",
        data=json.dumps({"token": raw, "password": "NewPass123!"}),
        content_type="application/json",
    )
    assert r2.status_code == 400
    assert "detail" in r2.json()

    user.refresh_from_db()
    assert authenticate(username=user.username, password="OldPass123!") is not None
