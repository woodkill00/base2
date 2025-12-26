import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0002_emailoutbox"),
    ]

    operations = [
        migrations.CreateModel(
            name="OneTimeToken",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
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
                (
                    "purpose",
                    models.CharField(
                        choices=[("email_verification", "Email verification"), ("password_reset", "Password reset")],
                        max_length=50,
                    ),
                ),
                ("email", models.EmailField(max_length=255)),
                ("token_hash", models.CharField(max_length=64, unique=True)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("consumed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="one_time_tokens",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "One Time Token",
                "verbose_name_plural": "One Time Tokens",
            },
        ),
        migrations.AddIndex(
            model_name="onetimetoken",
            index=models.Index(fields=["purpose", "email"], name="users_oneti_purpose_3e0793_idx"),
        ),
        migrations.AddIndex(
            model_name="onetimetoken",
            index=models.Index(fields=["user", "purpose"], name="users_oneti_user_id_1b532f_idx"),
        ),
        migrations.AddIndex(
            model_name="onetimetoken",
            index=models.Index(fields=["purpose", "consumed_at"], name="users_oneti_purpose_9c3d98_idx"),
        ),
    ]
