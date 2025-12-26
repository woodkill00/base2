import json
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from users.models import EmailAddress, OneTimeToken
from users.tokens import mint_one_time_token


@pytest.mark.django_db
def test_signup_issues_email_verification_token(monkeypatch):
    # Avoid needing a real broker during unit tests.
    from users import tasks

    monkeypatch.setattr(tasks.send_verification_email, "delay", lambda **kwargs: "queued")

    client = Client()
    payload = {"email": "verifyme@example.com", "password": "Test1234!"}
    r = client.post(
        "/internal/api/users/signup",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert r.status_code == 201

    token = OneTimeToken.objects.filter(purpose=OneTimeToken.Purpose.EMAIL_VERIFICATION).first()
    assert token is not None
    assert token.email == "verifyme@example.com"
    assert token.token_hash
    assert len(token.token_hash) == 64
    assert token.consumed_at is None

    email_obj = EmailAddress.objects.filter(user=token.user, email=token.email).first()
    assert email_obj is not None
    assert email_obj.is_verified is False


@pytest.mark.django_db
def test_verify_email_marks_email_address_verified():
    AuthUser = get_user_model()
    user = AuthUser.objects.create_user(username="v1", email="v1@example.com", password="Test1234!")
    EmailAddress.objects.create(user=user, email="v1@example.com", is_primary=True, is_verified=False)

    raw, _token = mint_one_time_token(
        user=user,
        purpose=OneTimeToken.Purpose.EMAIL_VERIFICATION,
        email="v1@example.com",
        ttl=timedelta(hours=24),
    )

    client = Client()
    r = client.post(
        "/internal/api/users/verify-email",
        data=json.dumps({"token": raw}),
        content_type="application/json",
    )
    assert r.status_code == 200
    assert "detail" in r.json()

    email_obj = EmailAddress.objects.get(user=user, email="v1@example.com")
    assert email_obj.is_verified is True
    assert email_obj.verified_at is not None

    consumed = OneTimeToken.objects.get(uuid=_token.uuid)
    assert consumed.consumed_at is not None


@pytest.mark.django_db
def test_verify_email_rejects_invalid_token_is_generic():
    client = Client()
    r = client.post(
        "/internal/api/users/verify-email",
        data=json.dumps({"token": "not-a-real-token"}),
        content_type="application/json",
    )
    assert r.status_code == 400
    assert "detail" in r.json()
