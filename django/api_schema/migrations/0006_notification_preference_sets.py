"""Public-identity adapter of the canonical notification-set header."""
from django.db import migrations

LEGACY_SQL = """
CREATE TABLE IF NOT EXISTS api_user_preferences (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES api_auth_users(id) ON DELETE CASCADE,
  tenant_id TEXT NOT NULL CHECK (tenant_id ~ '^[a-z0-9][a-z0-9-]{0,62}$'),
  schema_version SMALLINT NOT NULL DEFAULT 1 CHECK (schema_version = 1),
  version INTEGER NOT NULL DEFAULT 1 CHECK (version >= 1),
  theme TEXT NOT NULL DEFAULT 'system' CHECK (theme IN ('system', 'light', 'dark')),
  contrast TEXT NOT NULL DEFAULT 'system' CHECK (contrast IN ('system', 'standard', 'high')),
  motion TEXT NOT NULL DEFAULT 'system' CHECK (motion IN ('system', 'full', 'reduced')),
  density TEXT NOT NULL DEFAULT 'comfortable' CHECK (density IN ('comfortable', 'compact')),
  locale TEXT NOT NULL DEFAULT 'en' CHECK (char_length(locale) BETWEEN 2 AND 32),
  timezone TEXT NOT NULL DEFAULT 'UTC' CHECK (char_length(timezone) BETWEEN 1 AND 255),
  week_start TEXT NOT NULL DEFAULT 'system' CHECK (week_start IN ('system', 'monday', 'sunday', 'saturday')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (user_id, tenant_id)
);
CREATE INDEX IF NOT EXISTS api_user_preferences_owner_idx
  ON api_user_preferences(user_id, tenant_id);

CREATE TABLE IF NOT EXISTS api_notification_preferences (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES api_auth_users(id) ON DELETE CASCADE,
  tenant_id TEXT NOT NULL CHECK (tenant_id ~ '^[a-z0-9][a-z0-9-]{0,62}$'),
  event_family TEXT NOT NULL CHECK (event_family IN ('security', 'transactional', 'product', 'marketing')),
  channel TEXT NOT NULL CHECK (channel IN ('email', 'in_app', 'browser')),
  delivery TEXT NOT NULL CHECK (delivery IN ('immediate', 'digest', 'disabled')),
  mandatory BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (user_id, tenant_id, event_family, channel),
  CHECK (NOT mandatory OR delivery <> 'disabled')
);
CREATE INDEX IF NOT EXISTS api_notification_preferences_owner_idx
  ON api_notification_preferences(user_id, tenant_id, event_family);
"""

FORWARD_SQL = """
-- Runtime-public identity adapter for common.NotificationPreferenceSet.
-- Django operator users/organizations are deliberately not referenced here.
CREATE TABLE IF NOT EXISTS api_notification_preference_sets (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES api_auth_users(id) ON DELETE CASCADE,
  tenant_id TEXT NOT NULL CHECK (tenant_id ~ '^[a-z0-9][a-z0-9-]{0,62}$'),
  schema_version SMALLINT NOT NULL DEFAULT 1 CHECK (schema_version = 1),
  version BIGINT NOT NULL DEFAULT 1 CHECK (version >= 1),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (user_id, tenant_id)
);
-- Stable additive backfill; legacy choices and delivery modes remain untouched.
-- Guard supports the Django-first installation order; API migration reruns this
-- after the legacy choice table exists. Existing headers are never reset.
DO $$ BEGIN
  IF to_regclass('public.api_notification_preferences') IS NOT NULL THEN
    INSERT INTO api_notification_preference_sets(id,user_id,tenant_id)
      SELECT md5('notification-set:' || user_id::text || ':' || tenant_id)::uuid,
             user_id,tenant_id
        FROM api_notification_preferences GROUP BY user_id,tenant_id
      ON CONFLICT (user_id, tenant_id) DO NOTHING;
  END IF;
END $$;
"""


def forward(apps, schema_editor):
    del apps
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(LEGACY_SQL)
        schema_editor.execute(FORWARD_SQL)


def reverse(apps, schema_editor):
    del apps
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute("DROP TABLE IF EXISTS api_notification_preference_sets")


class Migration(migrations.Migration):
    dependencies = [("api_schema", "0005_data_rights_claim_fencing"),
                    ("users", "0009_notificationpreferenceset")]
    operations = [migrations.RunPython(forward, reverse)]
