"""Resilient index rename migration.

This migration was originally generated with multiple `RenameIndex` operations.
In long-lived environments, index drift can occur (e.g., old index missing or
already renamed), which makes `RenameIndex` fail hard on Postgres.

We keep the *state* rename (so Django's model state matches current index
names), but make the *database* rename conditional.
"""

import django.core.validators
from django.db import migrations, models


def _pg_rename_index_if_present(schema_editor, old_name: str, new_name: str) -> None:
    if schema_editor.connection.vendor != "postgresql":
        return

    qn = schema_editor.quote_name
    with schema_editor.connection.cursor() as cur:
        cur.execute("SELECT to_regclass(%s)", (old_name,))
        old_exists = cur.fetchone()[0] is not None
        cur.execute("SELECT to_regclass(%s)", (new_name,))
        new_exists = cur.fetchone()[0] is not None

    if not old_exists or new_exists:
        return

    schema_editor.execute(f"ALTER INDEX {qn(old_name)} RENAME TO {qn(new_name)}")


def rename_indexes_forward(apps, schema_editor):
    _pg_rename_index_if_present(schema_editor, "users_token_active_idx", "users_apito_user_id_84f205_idx")
    _pg_rename_index_if_present(schema_editor, "users_email_user_idx", "users_email_email_77c813_idx")
    _pg_rename_index_if_present(schema_editor, "users_to_sent_at_idx", "users_email_to_9f9ec7_idx")
    _pg_rename_index_if_present(schema_editor, "users_oneti_purpose_3e0793_idx", "users_oneti_purpose_44a02d_idx")
    _pg_rename_index_if_present(schema_editor, "users_oneti_user_id_1b532f_idx", "users_oneti_user_id_f63cd1_idx")
    _pg_rename_index_if_present(schema_editor, "users_oneti_purpose_9c3d98_idx", "users_oneti_purpose_14af82_idx")


def rename_indexes_backward(apps, schema_editor):
    # Best-effort reverse (also conditional).
    _pg_rename_index_if_present(schema_editor, "users_apito_user_id_84f205_idx", "users_token_active_idx")
    _pg_rename_index_if_present(schema_editor, "users_email_email_77c813_idx", "users_email_user_idx")
    _pg_rename_index_if_present(schema_editor, "users_email_to_9f9ec7_idx", "users_to_sent_at_idx")
    _pg_rename_index_if_present(schema_editor, "users_oneti_purpose_44a02d_idx", "users_oneti_purpose_3e0793_idx")
    _pg_rename_index_if_present(schema_editor, "users_oneti_user_id_f63cd1_idx", "users_oneti_user_id_1b532f_idx")
    _pg_rename_index_if_present(schema_editor, "users_oneti_purpose_14af82_idx", "users_oneti_purpose_9c3d98_idx")


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_auditevent_indexes'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(rename_indexes_forward, rename_indexes_backward),
            ],
            state_operations=[
                migrations.RenameIndex(
                    model_name='apitoken',
                    new_name='users_apito_user_id_84f205_idx',
                    old_name='users_token_active_idx',
                ),
                migrations.RenameIndex(
                    model_name='emailaddress',
                    new_name='users_email_email_77c813_idx',
                    old_name='users_email_user_idx',
                ),
                migrations.RenameIndex(
                    model_name='emailoutbox',
                    new_name='users_email_to_9f9ec7_idx',
                    old_name='users_to_sent_at_idx',
                ),
                migrations.RenameIndex(
                    model_name='onetimetoken',
                    new_name='users_oneti_purpose_44a02d_idx',
                    old_name='users_oneti_purpose_3e0793_idx',
                ),
                migrations.RenameIndex(
                    model_name='onetimetoken',
                    new_name='users_oneti_user_id_f63cd1_idx',
                    old_name='users_oneti_user_id_1b532f_idx',
                ),
                migrations.RenameIndex(
                    model_name='onetimetoken',
                    new_name='users_oneti_purpose_14af82_idx',
                    old_name='users_oneti_purpose_9c3d98_idx',
                ),
            ],
        ),
        migrations.AlterField(
            model_name='useraddress',
            name='latitude',
            field=models.DecimalField(blank=True, decimal_places=15, default='', help_text='Latitude', max_digits=18, null=True, validators=[django.core.validators.MinValueValidator(-180), django.core.validators.MaxValueValidator(180)], verbose_name='Latitude'),
        ),
        migrations.AlterField(
            model_name='useraddress',
            name='longitude',
            field=models.DecimalField(blank=True, decimal_places=15, default='', help_text='Longitude', max_digits=18, null=True, validators=[django.core.validators.MinValueValidator(-180), django.core.validators.MaxValueValidator(180)], verbose_name='Longitude'),
        ),
        migrations.AlterField(
            model_name='useraddress',
            name='postal_code',
            field=models.PositiveIntegerField(blank=True, help_text='Postal Zip Code', null=True, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(999999999)], verbose_name='Postal Zip Code'),
        ),
        migrations.AlterField(
            model_name='useraddress',
            name='street_number',
            field=models.PositiveIntegerField(blank=True, help_text='Street Number', null=True, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(99999)], verbose_name='Street Number'),
        ),
        migrations.AlterField(
            model_name='useraddress',
            name='sub_premise',
            field=models.PositiveIntegerField(blank=True, help_text='Suite Number', null=True, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(9999)], verbose_name='Suite Number'),
        ),
    ]
