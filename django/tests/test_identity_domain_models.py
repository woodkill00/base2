from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from users.models import (
    ApiCredential,
    AuditEvent,
    Authenticator,
    Invitation,
    Membership,
    Organization,
    UserSession,
)

pytestmark = pytest.mark.django_db


def user(name):
    return get_user_model().objects.create_user(username=name, email=f"{name}@example.test")


def test_organization_membership_role_and_uniqueness_contract():
    owner = user("owner")
    organization = Organization.objects.create(name="North Star", slug="north-star")
    membership = Membership.objects.create(
        organization=organization, user=owner, role=Membership.Role.OWNER
    )
    assert membership.status == Membership.Status.ACTIVE
    with pytest.raises(IntegrityError), transaction.atomic():
        Membership.objects.create(organization=organization, user=owner)
    with pytest.raises(IntegrityError), transaction.atomic():
        Organization.objects.create(name="Other", slug="north-star")


def test_invitation_authenticator_session_and_credential_store_only_protected_values():
    owner = user("security-owner")
    organization = Organization.objects.create(name="Secure Org", slug="secure-org")
    invitation = Invitation.objects.create(
        organization=organization,
        email="invitee@example.test",
        role=Membership.Role.EDITOR,
        token_hash="a" * 64,
        expires_at=timezone.now() + timedelta(days=1),
    )
    authenticator = Authenticator.objects.create(
        user=owner,
        kind=Authenticator.Kind.WEBAUTHN,
        credential_id="credential-public-id",
        secret_ciphertext="encrypted-envelope",
    )
    session = UserSession.objects.create(
        user=owner,
        token_hash="b" * 64,
        expires_at=timezone.now() + timedelta(hours=1),
    )
    credential = ApiCredential.objects.create(
        organization=organization,
        user=owner,
        label="automation",
        prefix="b2_test",
        secret_hash="c" * 64,
        scopes=["content:read"],
    )
    assert invitation.accepted_at is None
    assert authenticator.is_active
    assert session.revoked_at is None
    assert credential.revoked_at is None
    for model in (Invitation, Authenticator, UserSession, ApiCredential):
        names = {field.name for field in model._meta.fields}
        assert "token" not in names and "secret" not in names


def test_audit_events_are_append_only():
    actor = user("auditor")
    event = AuditEvent.objects.create(actor_user=actor, action="identity.created")
    event.action = "identity.tampered"
    with pytest.raises(ValidationError, match="append_only"):
        event.save()
    with pytest.raises(ValidationError, match="append_only"):
        event.delete()
