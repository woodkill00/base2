-- Base2 FastAPI-owned auth schema (Phase 14 Option A)
-- Idempotent by design: uses IF NOT EXISTS.

CREATE TABLE IF NOT EXISTS api_schema_migrations (
  version TEXT PRIMARY KEY,
  applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

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
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_api_auth_users_email ON api_auth_users (email);

CREATE TABLE IF NOT EXISTS api_auth_refresh_tokens (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES api_auth_users(id) ON DELETE CASCADE,
  token_hash TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  expires_at TIMESTAMPTZ NOT NULL,
  revoked_at TIMESTAMPTZ NULL,
  replaced_by_token_id UUID NULL,
  user_agent TEXT NOT NULL DEFAULT '',
  ip TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_api_auth_refresh_tokens_user_id ON api_auth_refresh_tokens (user_id);
CREATE INDEX IF NOT EXISTS idx_api_auth_refresh_tokens_token_hash ON api_auth_refresh_tokens (token_hash);

CREATE TABLE IF NOT EXISTS api_auth_one_time_tokens (
  id UUID PRIMARY KEY,
  user_id UUID NULL REFERENCES api_auth_users(id) ON DELETE SET NULL,
  token_hash TEXT NOT NULL,
  type TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  expires_at TIMESTAMPTZ NOT NULL,
  consumed_at TIMESTAMPTZ NULL
);
CREATE INDEX IF NOT EXISTS idx_api_auth_one_time_tokens_type ON api_auth_one_time_tokens (type);
CREATE INDEX IF NOT EXISTS idx_api_auth_one_time_tokens_token_hash ON api_auth_one_time_tokens (token_hash);

CREATE TABLE IF NOT EXISTS api_auth_audit_events (
  id UUID PRIMARY KEY,
  user_id UUID NULL REFERENCES api_auth_users(id) ON DELETE SET NULL,
  action TEXT NOT NULL,
  ip TEXT NOT NULL DEFAULT '',
  user_agent TEXT NOT NULL DEFAULT '',
  metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_api_auth_audit_events_user_id ON api_auth_audit_events (user_id);
CREATE INDEX IF NOT EXISTS idx_api_auth_audit_events_action ON api_auth_audit_events (action);
CREATE INDEX IF NOT EXISTS idx_api_auth_audit_events_created_at ON api_auth_audit_events (created_at);

CREATE TABLE IF NOT EXISTS api_auth_oauth_accounts (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES api_auth_users(id) ON DELETE CASCADE,
  provider TEXT NOT NULL,
  provider_account_id TEXT NOT NULL,
  email TEXT NOT NULL DEFAULT '',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(provider, provider_account_id)
);
CREATE INDEX IF NOT EXISTS idx_api_auth_oauth_accounts_user_id ON api_auth_oauth_accounts (user_id);
