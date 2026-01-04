from __future__ import annotations

from django.db import migrations, models


def _execute_postgres_statements(schema_editor, statements: list[str]) -> None:
    if schema_editor.connection.vendor != "postgresql":
        return

    with schema_editor.connection.cursor() as cursor:
        for stmt in statements:
            s = (stmt or "").strip()
            if not s:
                continue
            cursor.execute(s)


def create_tables(apps, schema_editor) -> None:
    statements: list[str] = [
        """
        CREATE TABLE IF NOT EXISTS api_auth_users (
          id UUID PRIMARY KEY,
          email TEXT NOT NULL UNIQUE,
          password_hash TEXT NOT NULL,
          is_active BOOLEAN NOT NULL DEFAULT TRUE,
          is_email_verified BOOLEAN NOT NULL DEFAULT FALSE,
          display_name TEXT NOT NULL DEFAULT '',
          avatar_url TEXT NOT NULL DEFAULT '',
          bio TEXT NOT NULL DEFAULT '',
          created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          failed_login_attempts INTEGER NOT NULL DEFAULT 0,
          locked_until TIMESTAMPTZ NULL
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_api_auth_users_email ON api_auth_users (email)",
        "CREATE INDEX IF NOT EXISTS idx_api_auth_users_locked_until ON api_auth_users (locked_until)",

        """
        CREATE TABLE IF NOT EXISTS api_auth_refresh_tokens (
          id UUID PRIMARY KEY,
          user_id UUID NOT NULL REFERENCES api_auth_users(id) ON DELETE CASCADE,
          token_hash TEXT NOT NULL,
          created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          expires_at TIMESTAMPTZ NOT NULL,
          revoked_at TIMESTAMPTZ NULL,
          replaced_by_token_id UUID NULL,
          user_agent TEXT NOT NULL DEFAULT '',
          ip TEXT NOT NULL DEFAULT '',
          last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_api_auth_refresh_tokens_user_id ON api_auth_refresh_tokens (user_id)",
        "CREATE INDEX IF NOT EXISTS idx_api_auth_refresh_tokens_token_hash ON api_auth_refresh_tokens (token_hash)",
        "CREATE INDEX IF NOT EXISTS idx_api_auth_refresh_tokens_last_seen_at ON api_auth_refresh_tokens (last_seen_at)",

        """
        CREATE TABLE IF NOT EXISTS api_auth_one_time_tokens (
          id UUID PRIMARY KEY,
          user_id UUID NULL REFERENCES api_auth_users(id) ON DELETE SET NULL,
          token_hash TEXT NOT NULL,
          type TEXT NOT NULL,
          created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          expires_at TIMESTAMPTZ NOT NULL,
          consumed_at TIMESTAMPTZ NULL
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_api_auth_one_time_tokens_type ON api_auth_one_time_tokens (type)",
        "CREATE INDEX IF NOT EXISTS idx_api_auth_one_time_tokens_token_hash ON api_auth_one_time_tokens (token_hash)",

        """
        CREATE TABLE IF NOT EXISTS api_auth_audit_events (
          id UUID PRIMARY KEY,
          user_id UUID NULL REFERENCES api_auth_users(id) ON DELETE SET NULL,
          action TEXT NOT NULL,
          ip TEXT NOT NULL DEFAULT '',
          user_agent TEXT NOT NULL DEFAULT '',
          metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
          created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_api_auth_audit_events_user_id ON api_auth_audit_events (user_id)",
        "CREATE INDEX IF NOT EXISTS idx_api_auth_audit_events_action ON api_auth_audit_events (action)",
        "CREATE INDEX IF NOT EXISTS idx_api_auth_audit_events_created_at ON api_auth_audit_events (created_at)",

        """
        CREATE TABLE IF NOT EXISTS api_auth_oauth_accounts (
          id UUID PRIMARY KEY,
          user_id UUID NOT NULL REFERENCES api_auth_users(id) ON DELETE CASCADE,
          provider TEXT NOT NULL,
          provider_account_id TEXT NOT NULL,
          email TEXT NOT NULL DEFAULT '',
          created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          UNIQUE(provider, provider_account_id)
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_api_auth_oauth_accounts_user_id ON api_auth_oauth_accounts (user_id)",

        """
        CREATE TABLE IF NOT EXISTS api_email_outbox (
          id UUID PRIMARY KEY,
          to_email TEXT NOT NULL,
          subject TEXT NOT NULL,
          body_text TEXT NOT NULL,
          body_html TEXT NOT NULL DEFAULT '',
          status TEXT NOT NULL DEFAULT 'queued',
          provider TEXT NOT NULL DEFAULT 'local_outbox',
          provider_message_id TEXT NOT NULL DEFAULT '',
          error TEXT NOT NULL DEFAULT '',
          created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          sent_at TIMESTAMPTZ NULL
        )
        """,
        "CREATE INDEX IF NOT EXISTS api_email_outbox_to_email_idx ON api_email_outbox(to_email)",
        "CREATE INDEX IF NOT EXISTS api_email_outbox_status_created_idx ON api_email_outbox(status, created_at)",
    ]

    _execute_postgres_statements(schema_editor, statements)


def drop_tables(apps, schema_editor) -> None:
    if schema_editor.connection.vendor != "postgresql":
        return

    # Best-effort reverse for developer environments.
    statements = [
        "DROP TABLE IF EXISTS api_email_outbox",
        "DROP TABLE IF EXISTS api_auth_oauth_accounts",
        "DROP TABLE IF EXISTS api_auth_audit_events",
        "DROP TABLE IF EXISTS api_auth_one_time_tokens",
        "DROP TABLE IF EXISTS api_auth_refresh_tokens",
        "DROP TABLE IF EXISTS api_auth_users",
    ]
    _execute_postgres_statements(schema_editor, statements)


class Migration(migrations.Migration):
    initial = True

    dependencies: list[tuple[str, str]] = []

    operations = [
        migrations.RunPython(create_tables, reverse_code=drop_tables),
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name="ApiAuthUser",
                    fields=[
                        ("id", models.UUIDField(primary_key=True, serialize=False)),
                        ("email", models.TextField(unique=True)),
                        ("password_hash", models.TextField()),
                        ("is_active", models.BooleanField(default=True)),
                        ("is_email_verified", models.BooleanField(default=False)),
                        ("display_name", models.TextField(blank=True, default="")),
                        ("avatar_url", models.TextField(blank=True, default="")),
                        ("bio", models.TextField(blank=True, default="")),
                        ("created_at", models.DateTimeField()),
                        ("updated_at", models.DateTimeField()),
                        ("failed_login_attempts", models.IntegerField(default=0)),
                        ("locked_until", models.DateTimeField(blank=True, null=True)),
                    ],
                    options={
                        "managed": False,
                        "db_table": "api_auth_users",
                    },
                ),
                migrations.CreateModel(
                    name="ApiAuthRefreshToken",
                    fields=[
                        ("id", models.UUIDField(primary_key=True, serialize=False)),
                        ("token_hash", models.TextField()),
                        ("created_at", models.DateTimeField()),
                        ("expires_at", models.DateTimeField()),
                        ("revoked_at", models.DateTimeField(blank=True, null=True)),
                        ("replaced_by_token_id", models.UUIDField(blank=True, null=True)),
                        ("user_agent", models.TextField(blank=True, default="")),
                        ("ip", models.TextField(blank=True, default="")),
                        ("last_seen_at", models.DateTimeField()),
                        (
                            "user",
                            models.ForeignKey(
                                db_column="user_id",
                                on_delete=models.deletion.CASCADE,
                                related_name="refresh_tokens",
                                to="api_schema.apiauthuser",
                                to_field="id",
                            ),
                        ),
                    ],
                    options={
                        "managed": False,
                        "db_table": "api_auth_refresh_tokens",
                    },
                ),
                migrations.CreateModel(
                    name="ApiAuthOneTimeToken",
                    fields=[
                        ("id", models.UUIDField(primary_key=True, serialize=False)),
                        ("token_hash", models.TextField()),
                        ("type", models.TextField()),
                        ("created_at", models.DateTimeField()),
                        ("expires_at", models.DateTimeField()),
                        ("consumed_at", models.DateTimeField(blank=True, null=True)),
                        (
                            "user",
                            models.ForeignKey(
                                blank=True,
                                db_column="user_id",
                                null=True,
                                on_delete=models.deletion.SET_NULL,
                                related_name="one_time_tokens",
                                to="api_schema.apiauthuser",
                                to_field="id",
                            ),
                        ),
                    ],
                    options={
                        "managed": False,
                        "db_table": "api_auth_one_time_tokens",
                    },
                ),
                migrations.CreateModel(
                    name="ApiAuthAuditEvent",
                    fields=[
                        ("id", models.UUIDField(primary_key=True, serialize=False)),
                        ("action", models.TextField()),
                        ("ip", models.TextField(blank=True, default="")),
                        ("user_agent", models.TextField(blank=True, default="")),
                        ("metadata_json", models.JSONField(default=dict)),
                        ("created_at", models.DateTimeField()),
                        (
                            "user",
                            models.ForeignKey(
                                blank=True,
                                db_column="user_id",
                                null=True,
                                on_delete=models.deletion.SET_NULL,
                                related_name="audit_events",
                                to="api_schema.apiauthuser",
                                to_field="id",
                            ),
                        ),
                    ],
                    options={
                        "managed": False,
                        "db_table": "api_auth_audit_events",
                    },
                ),
                migrations.CreateModel(
                    name="ApiAuthOAuthAccount",
                    fields=[
                        ("id", models.UUIDField(primary_key=True, serialize=False)),
                        ("provider", models.TextField()),
                        ("provider_account_id", models.TextField()),
                        ("email", models.TextField(blank=True, default="")),
                        ("created_at", models.DateTimeField()),
                        (
                            "user",
                            models.ForeignKey(
                                db_column="user_id",
                                on_delete=models.deletion.CASCADE,
                                related_name="oauth_accounts",
                                to="api_schema.apiauthuser",
                                to_field="id",
                            ),
                        ),
                    ],
                    options={
                        "managed": False,
                        "db_table": "api_auth_oauth_accounts",
                    },
                ),
                migrations.CreateModel(
                    name="ApiEmailOutbox",
                    fields=[
                        ("id", models.UUIDField(primary_key=True, serialize=False)),
                        ("to_email", models.TextField()),
                        ("subject", models.TextField()),
                        ("body_text", models.TextField()),
                        ("body_html", models.TextField(blank=True, default="")),
                        ("status", models.TextField(default="queued")),
                        ("provider", models.TextField(default="local_outbox")),
                        ("provider_message_id", models.TextField(blank=True, default="")),
                        ("error", models.TextField(blank=True, default="")),
                        ("created_at", models.DateTimeField()),
                        ("sent_at", models.DateTimeField(blank=True, null=True)),
                    ],
                    options={
                        "managed": False,
                        "db_table": "api_email_outbox",
                    },
                ),
            ],
        ),
    ]
