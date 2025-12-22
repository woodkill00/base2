import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django_countries.fields
import phonenumber_field.modelfields


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ApiToken",
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
                ("token_hash", models.CharField(max_length=255, unique=True)),
                ("scope", models.CharField(blank=True, default="", max_length=255)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="api_tokens",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "API Token",
                "verbose_name_plural": "API Tokens",
            },
        ),
        migrations.CreateModel(
            name="AuditEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
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
                ("action", models.CharField(max_length=100)),
                ("target_type", models.CharField(blank=True, default="", max_length=100)),
                ("target_id", models.CharField(blank=True, default="", max_length=100)),
                ("ip", models.GenericIPAddressField(blank=True, null=True)),
                ("user_agent", models.TextField(blank=True, default="")),
                ("metadata", models.JSONField(blank=True, null=True)),
                (
                    "actor_user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="audit_events",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Audit Event",
                "verbose_name_plural": "Audit Events",
            },
        ),
        migrations.CreateModel(
            name="EmailAddress",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
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
                    "email",
                    models.EmailField(
                        help_text="Email Address",
                        max_length=255,
                        unique=True,
                        verbose_name="Email Address",
                    ),
                ),
                ("is_primary", models.BooleanField(default=False)),
                ("is_verified", models.BooleanField(default=False)),
                ("verification_token", models.CharField(blank=True, default="", max_length=255)),
                ("verified_at", models.DateTimeField(blank=True, null=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="emails",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Email Address",
                "verbose_name_plural": "Email Addresses",
                "indexes": [models.Index(fields=["email", "user"], name="users_email_user_idx")],
            },
        ),
        migrations.CreateModel(
            name="OAuthAccount",
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
                ("provider", models.CharField(max_length=50)),
                ("provider_user_id", models.CharField(max_length=255)),
                ("access_token", models.TextField(blank=True, default="")),
                ("refresh_token", models.TextField(blank=True, default="")),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="oauth_accounts",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "OAuth Account",
                "verbose_name_plural": "OAuth Accounts",
                "unique_together": {("provider", "provider_user_id")},
            },
        ),
        migrations.CreateModel(
            name="PhoneNumber",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
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
                    "phonenumber",
                    phonenumber_field.modelfields.PhoneNumberField(
                        help_text="Phonenumber",
                        max_length=128,
                        region=None,
                        verbose_name="Phonenumber",
                    ),
                ),
                (
                    "type",
                    models.CharField(
                        choices=[("mobile", "Mobile"), ("home", "Home"), ("work", "Work")],
                        default="mobile",
                        max_length=20,
                    ),
                ),
                ("is_verified", models.BooleanField(default=False)),
                ("verified_at", models.DateTimeField(blank=True, null=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="phones",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Phone Number",
                "verbose_name_plural": "Phone Numbers",
            },
        ),
        migrations.CreateModel(
            name="RecoveryCode",
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
                ("code_hash", models.CharField(max_length=255, unique=True)),
                ("used_at", models.DateTimeField(blank=True, null=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="recovery_codes",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Recovery Code",
                "verbose_name_plural": "Recovery Codes",
            },
        ),
        migrations.CreateModel(
            name="UserAddress",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
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
                ("line1", models.CharField(help_text="Street Line 1", max_length=255, verbose_name="Address Line 1")),
                (
                    "line2",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text="Address Line 2",
                        max_length=255,
                        verbose_name="Address Line 2",
                    ),
                ),
                ("city", models.CharField(help_text="City Name", max_length=150, verbose_name="City")),
                (
                    "state",
                    models.CharField(blank=True, help_text="State Name", max_length=150, null=True, verbose_name="State"),
                ),
                (
                    "state_code",
                    models.CharField(blank=True, help_text="State Code", max_length=5, null=True, verbose_name="State Code"),
                ),
                (
                    "postal_code",
                    models.PositiveIntegerField(
                        blank=True,
                        help_text="Postal Zip Code",
                        null=True,
                        verbose_name="Postal Zip Code",
                    ),
                ),
                (
                    "country",
                    django_countries.fields.CountryField(
                        help_text="Country Name",
                        max_length=150,
                        verbose_name="Country",
                    ),
                ),
                (
                    "latitude",
                    models.DecimalField(
                        blank=True,
                        decimal_places=15,
                        default="",
                        help_text="Latitude",
                        max_digits=18,
                        null=True,
                        verbose_name="Latitude",
                    ),
                ),
                (
                    "longitude",
                    models.DecimalField(
                        blank=True,
                        decimal_places=15,
                        default="",
                        help_text="Longitude",
                        max_digits=18,
                        null=True,
                        verbose_name="Longitude",
                    ),
                ),
                (
                    "street_number",
                    models.PositiveIntegerField(
                        blank=True,
                        help_text="Street Number",
                        null=True,
                        verbose_name="Street Number",
                    ),
                ),
                (
                    "street_number_before_name",
                    models.BooleanField(
                        default=False,
                        help_text="Street Number > Street Name",
                        verbose_name="Street Number Before Name",
                    ),
                ),
                (
                    "street_name",
                    models.CharField(
                        blank=True,
                        help_text="Street Name",
                        max_length=150,
                        verbose_name="Street Name",
                    ),
                ),
                (
                    "sub_premise",
                    models.PositiveIntegerField(
                        blank=True,
                        help_text="Suite Number",
                        null=True,
                        verbose_name="Suite Number",
                    ),
                ),
                (
                    "sub_premise_name",
                    models.CharField(
                        blank=True,
                        help_text="Sub Premise Name",
                        max_length=150,
                        verbose_name="Sub Premise Name",
                    ),
                ),
                (
                    "type",
                    models.CharField(
                        choices=[
                            ("billing", "Billing"),
                            ("shipping", "Shipping"),
                            ("home", "Home"),
                            ("other", "Other"),
                        ],
                        default="home",
                        max_length=20,
                    ),
                ),
                ("is_primary", models.BooleanField(default=False)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="addresses",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "User Address",
                "verbose_name_plural": "User Addresses",
            },
        ),
        migrations.CreateModel(
            name="UserProfile",
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
                ("display_name", models.CharField(blank=True, default="", max_length=150)),
                ("avatar_url", models.URLField(blank=True, default="")),
                ("bio", models.TextField(blank=True, default="")),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="profile",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "User Profile",
                "verbose_name_plural": "User Profiles",
            },
        ),
        migrations.CreateModel(
            name="UserUrl",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
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
                    "address",
                    models.URLField(
                        help_text="Url Address",
                        max_length=255,
                        unique=True,
                        verbose_name="Url Address",
                    ),
                ),
                (
                    "type",
                    models.CharField(
                        choices=[
                            ("website", "Website"),
                            ("linkedin", "LinkedIn"),
                            ("github", "GitHub"),
                            ("other", "Other"),
                        ],
                        default="website",
                        max_length=20,
                    ),
                ),
                ("is_public", models.BooleanField(default=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="urls",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "User URL",
                "verbose_name_plural": "User URLs",
            },
        ),
        migrations.AddIndex(
            model_name="apitoken",
            index=models.Index(fields=["user", "is_active"], name="users_token_active_idx"),
        ),
        migrations.AddIndex(
            model_name="auditevent",
            index=models.Index(fields=["action", "actor_user"], name="users_audit_action_idx"),
        ),
    ]
