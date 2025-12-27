-- Add lockout/throttling fields to users
-- Idempotent by design.

ALTER TABLE api_auth_users
  ADD COLUMN IF NOT EXISTS failed_login_attempts INTEGER NOT NULL DEFAULT 0;

ALTER TABLE api_auth_users
  ADD COLUMN IF NOT EXISTS locked_until TIMESTAMPTZ NULL;

CREATE INDEX IF NOT EXISTS idx_api_auth_users_locked_until ON api_auth_users (locked_until);
