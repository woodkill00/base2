import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def backfill_notification_headers(apps, schema_editor):
    Preference = apps.get_model("users", "NotificationPreference")
    Header = apps.get_model("users", "NotificationPreferenceSet")
    database = schema_editor.connection.alias
    scopes = (
        Preference.objects.using(database)
        .order_by()
        .values_list("user_id", "organization_id")
        .distinct()
    )
    for user_id, organization_id in scopes.iterator():
        Header.objects.using(database).get_or_create(
            user_id=user_id,
            organization_id=organization_id,
            defaults={"schema_version": 1, "version": 1},
        )


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0008_notificationpreference_userpreferenceset"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="NotificationPreferenceSet",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "created",
                    models.DateTimeField(
                        auto_now_add=True,
                        help_text="Date/Time created in database",
                        verbose_name="Created On",
                    ),
                ),
                (
                    "updated",
                    models.DateTimeField(
                        auto_now=True,
                        help_text="Date/Time last updated in database",
                        verbose_name="Last Updated On",
                    ),
                ),
                (
                    "uuid",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        help_text="Non-primary UUID identifier",
                        unique=True,
                        verbose_name="UUID",
                    ),
                ),
                ("schema_version", models.PositiveSmallIntegerField(default=1)),
                ("version", models.PositiveBigIntegerField(default=1)),
                (
                    "organization",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="notification_preference_sets",
                        to="users.organization",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="notification_preference_sets",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "abstract": False,
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(schema_version=1), name="users_notifset_schema_v1"
                    ),
                    models.CheckConstraint(
                        condition=models.Q(version__gte=1), name="users_notifset_ver_gte1"
                    ),
                    models.UniqueConstraint(
                        fields=("user",),
                        condition=models.Q(organization__isnull=True),
                        name="users_notifset_default_uniq",
                    ),
                    models.UniqueConstraint(
                        fields=("user", "organization"),
                        condition=models.Q(organization__isnull=False),
                        name="users_notifset_owner_uniq",
                    ),
                ],
            },
        ),
        # Reverse drops only the additive header table; legacy choices are untouched.
        migrations.RunPython(backfill_notification_headers, migrations.RunPython.noop),
    ]
