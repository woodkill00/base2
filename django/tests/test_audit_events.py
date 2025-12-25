import json

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from users.models import AuditEvent


@pytest.fixture()
def client_csrf() -> Client:
    return Client(enforce_csrf_checks=True)


@pytest.mark.django_db
def test_login_success_and_failure_audit_events(client_csrf: Client):
    AuthUser = get_user_model()
    AuthUser.objects.create_user(username="u3", email="u3@example.com", password="Correct123!")

    # Failure
    r_fail = client_csrf.post(
        "/internal/api/users/login",
        data=json.dumps({"email": "u3@example.com", "password": "Wrong123!"}),
        content_type="application/json",
        HTTP_USER_AGENT="pytest",
        REMOTE_ADDR="127.0.0.1",
    )
    assert r_fail.status_code == 401

    ev_fail = AuditEvent.objects.filter(action="auth.login.failure").order_by("-created").first()
    assert ev_fail is not None
    assert ev_fail.user_agent == "pytest"
    assert not (ev_fail.metadata or {}).get("password")

    # Success
    r_ok = client_csrf.post(
        "/internal/api/users/login",
        data=json.dumps({"email": "u3@example.com", "password": "Correct123!"}),
        content_type="application/json",
        HTTP_USER_AGENT="pytest",
        REMOTE_ADDR="127.0.0.1",
    )
    assert r_ok.status_code == 200

    ev_ok = AuditEvent.objects.filter(action="auth.login.success").order_by("-created").first()
    assert ev_ok is not None
    assert not (ev_ok.metadata or {}).get("password")
