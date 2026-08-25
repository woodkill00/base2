from django.db import migrations


def protect_audit_events(apps, schema_editor):
    vendor = schema_editor.connection.vendor
    if vendor == "postgresql":
        schema_editor.execute(
            """
            CREATE OR REPLACE FUNCTION users_auditevent_reject_mutation()
            RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
              RAISE EXCEPTION 'audit_event_append_only';
            END;
            $$;
            DROP TRIGGER IF EXISTS users_auditevent_no_mutation ON users_auditevent;
            CREATE TRIGGER users_auditevent_no_mutation
            BEFORE UPDATE OR DELETE ON users_auditevent
            FOR EACH ROW EXECUTE FUNCTION users_auditevent_reject_mutation();
            """
        )
    elif vendor == "sqlite":
        schema_editor.execute(
            """
            CREATE TRIGGER IF NOT EXISTS users_auditevent_no_update
            BEFORE UPDATE ON users_auditevent
            BEGIN SELECT RAISE(ABORT, 'audit_event_append_only'); END;
            """
        )
        schema_editor.execute(
            """
            CREATE TRIGGER IF NOT EXISTS users_auditevent_no_delete
            BEFORE DELETE ON users_auditevent
            BEGIN SELECT RAISE(ABORT, 'audit_event_append_only'); END;
            """
        )


def unprotect_audit_events(apps, schema_editor):
    vendor = schema_editor.connection.vendor
    if vendor == "postgresql":
        schema_editor.execute(
            "DROP TRIGGER IF EXISTS users_auditevent_no_mutation ON users_auditevent;"
        )
        schema_editor.execute("DROP FUNCTION IF EXISTS users_auditevent_reject_mutation();")
    elif vendor == "sqlite":
        schema_editor.execute("DROP TRIGGER IF EXISTS users_auditevent_no_update;")
        schema_editor.execute("DROP TRIGGER IF EXISTS users_auditevent_no_delete;")


class Migration(migrations.Migration):
    dependencies = [("users", "0006_organization_authenticator_membership_invitation_and_more")]

    operations = [
        migrations.RemoveField(model_name="oauthaccount", name="access_token"),
        migrations.RemoveField(model_name="oauthaccount", name="refresh_token"),
        migrations.RunPython(protect_audit_events, unprotect_audit_events),
    ]
