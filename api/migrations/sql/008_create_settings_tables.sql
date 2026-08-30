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
