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
