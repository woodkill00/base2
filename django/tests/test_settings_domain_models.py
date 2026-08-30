import pytest
from importlib import import_module
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction

from users.models import NotificationPreference, UserPreferenceSet

pytestmark = pytest.mark.django_db


def make_user(name="settings-owner"):
    return get_user_model().objects.create_user(username=name, email=f"{name}@example.test")


def test_preference_defaults_are_safe_and_versioned():
    preferences = UserPreferenceSet.objects.create(user=make_user())
    assert preferences.schema_version == 1
    assert preferences.version == 1
    assert preferences.theme == UserPreferenceSet.Theme.SYSTEM
    assert preferences.contrast == UserPreferenceSet.Contrast.SYSTEM
    assert preferences.motion == UserPreferenceSet.Motion.SYSTEM
    assert preferences.density == UserPreferenceSet.Density.COMFORTABLE
    assert preferences.locale == "en"
    assert preferences.timezone == "UTC"
    assert preferences.week_start == UserPreferenceSet.WeekStart.SYSTEM


def test_preference_owner_context_is_unique():
    owner = make_user("preference-unique")
    UserPreferenceSet.objects.create(user=owner)
    with pytest.raises(IntegrityError), transaction.atomic():
        UserPreferenceSet.objects.create(user=owner)


def test_mandatory_notification_cannot_be_disabled():
    owner = make_user("mandatory-notification")
    with pytest.raises(IntegrityError), transaction.atomic():
        NotificationPreference.objects.create(
            user=owner,
            event_family=NotificationPreference.EventFamily.SECURITY,
            channel=NotificationPreference.Channel.EMAIL,
            delivery=NotificationPreference.Delivery.DISABLED,
            mandatory=True,
        )


def test_notification_owner_family_and_channel_are_unique():
    owner = make_user("notification-unique")
    values = {
        "user": owner,
        "event_family": NotificationPreference.EventFamily.PRODUCT,
        "channel": NotificationPreference.Channel.EMAIL,
        "delivery": NotificationPreference.Delivery.DIGEST,
    }
    NotificationPreference.objects.create(**values)
    with pytest.raises(IntegrityError), transaction.atomic():
        NotificationPreference.objects.create(**values)


def test_settings_migration_has_reversible_model_state_operations():
    migration = import_module(
        "users.migrations.0008_notificationpreference_userpreferenceset"
    ).Migration
    created_models = {
        operation.name for operation in migration.operations
        if operation.__class__.__name__ == "CreateModel"
    }
    assert created_models == {"NotificationPreference", "UserPreferenceSet"}
    assert all(operation.reversible for operation in migration.operations)
