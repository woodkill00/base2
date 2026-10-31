"""Backfill headers only: never rewrite legacy notification choices or identities."""

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

pytestmark = pytest.mark.django_db(transaction=True)
BASE = ("users", "0008_notificationpreference_userpreferenceset")
LATEST = ("users", "0009_notificationpreferenceset")


def test_notification_headers_backfill_and_reverse_preserve_every_legacy_choice():
    executor = MigrationExecutor(connection)
    leaves = executor.loader.graph.leaf_nodes()
    executor.migrate([BASE])
    try:
        apps = executor.loader.project_state([BASE]).apps
        User = apps.get_model("auth", "User")
        Organization = apps.get_model("users", "Organization")
        Preference = apps.get_model("users", "NotificationPreference")
        user = User.objects.create(username="legacy-notifications")
        untouched = User.objects.create(username="without-notifications")
        organization = Organization.objects.create(name="Legacy", slug="legacy")
        for scope in [None, organization.pk]:
            for family, delivery, mandatory in [
                ("security", "immediate", True),
                ("transactional", "digest", True),
                ("product", "disabled", False),
            ]:
                Preference.objects.create(
                    user_id=user.pk,
                    organization_id=scope,
                    event_family=family,
                    channel="email",
                    delivery=delivery,
                    mandatory=mandatory,
                )
        before = list(Preference.objects.order_by("pk").values())
        executor = MigrationExecutor(connection)
        executor.migrate([LATEST])
        apps = executor.loader.project_state([LATEST]).apps
        Header = apps.get_model("users", "NotificationPreferenceSet")
        Preference = apps.get_model("users", "NotificationPreference")
        assert list(Preference.objects.order_by("pk").values()) == before
        assert set(
            Header.objects.values_list("user_id", "organization_id", "schema_version", "version")
        ) == {(user.pk, None, 1, 1), (user.pk, organization.pk, 1, 1)}
        assert not Header.objects.filter(user_id=untouched.pk).exists()
        assert all(header.created and header.updated for header in Header.objects.all())
        executor = MigrationExecutor(connection)
        executor.migrate([BASE])
        apps = executor.loader.project_state([BASE]).apps
        assert (
            list(apps.get_model("users", "NotificationPreference").objects.order_by("pk").values())
            == before
        )
    finally:
        MigrationExecutor(connection).migrate(leaves)
