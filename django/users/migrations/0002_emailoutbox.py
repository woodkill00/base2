import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="EmailOutbox",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
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
                ("to", models.EmailField(max_length=255)),
                ("subject", models.CharField(max_length=255)),
                ("body", models.TextField()),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
                (
                    "provider_message_id",
                    models.CharField(blank=True, default="", max_length=255),
                ),
            ],
            options={
                "verbose_name": "Email Outbox",
                "verbose_name_plural": "Email Outbox",
                "indexes": [models.Index(fields=["to", "sent_at"], name="users_to_sent_at_idx")],
            },
        ),
    ]
