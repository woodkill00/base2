"""Canonical notification header contract; runtime public identities are separate."""

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from common.models import NotificationPreferenceSet as CanonicalNotificationPreferenceSet
from users.models import NotificationPreference, NotificationPreferenceSet, Organization

pytestmark = pytest.mark.django_db


def owner(name="notification-header"):
    return get_user_model().objects.create_user(username=name)


def test_header_is_a_canonical_abstract_primitive_with_operator_identity_adapter():
    assert CanonicalNotificationPreferenceSet._meta.abstract
    assert issubclass(NotificationPreferenceSet, CanonicalNotificationPreferenceSet)
    assert NotificationPreferenceSet._meta.get_field("user").remote_field.model is get_user_model()
    assert (
        NotificationPreferenceSet._meta.get_field("organization").remote_field.model is Organization
    )


def test_absent_header_stays_absent_and_new_header_does_not_create_choices():
    user = owner()
    assert not NotificationPreferenceSet.objects.filter(user=user).exists()
    header = NotificationPreferenceSet.objects.create(user=user)
    assert header.schema_version == header.version == 1
    assert header.uuid is not None
    assert header.created is not None and header.updated is not None
    assert not NotificationPreference.objects.filter(user=user).exists()


def test_header_scope_is_unique_including_null_organization_and_isolated():
    user = owner()
    other = owner("other-header")
    organizations = [Organization.objects.create(name=name, slug=name) for name in ("one", "two")]
    for organization in [None, *organizations]:
        NotificationPreferenceSet.objects.create(user=user, organization=organization)
        NotificationPreferenceSet.objects.create(user=other, organization=organization)
        with pytest.raises(IntegrityError), transaction.atomic():
            NotificationPreferenceSet.objects.create(user=user, organization=organization)
    assert NotificationPreferenceSet.objects.count() == 6


@pytest.mark.parametrize(
    "field,value", [("schema_version", 0), ("schema_version", 2), ("version", 0), ("version", -1)]
)
def test_header_rejects_unsupported_schema_and_nonpositive_versions(field, value):
    values = {"user": owner(), field: value}
    with pytest.raises(ValidationError):
        NotificationPreferenceSet(**values).full_clean()
    with pytest.raises(IntegrityError), transaction.atomic():
        NotificationPreferenceSet.objects.create(**values)


def test_header_supports_bigint_versions_and_cascades_only_its_operator_scope():
    user = owner()
    organization = Organization.objects.create(name="Scoped", slug="scoped")
    scoped = NotificationPreferenceSet.objects.create(
        user=user, organization=organization, version=2**32
    )
    default = NotificationPreferenceSet.objects.create(user=user)
    scoped.refresh_from_db()
    assert scoped.version == 2**32
    organization.delete()
    assert not NotificationPreferenceSet.objects.filter(pk=scoped.pk).exists()
    assert NotificationPreferenceSet.objects.filter(pk=default.pk).exists()
    user.delete()
    assert not NotificationPreferenceSet.objects.exists()
