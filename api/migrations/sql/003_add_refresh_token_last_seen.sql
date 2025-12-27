-- Add last_seen_at to refresh tokens for session listing
-- Idempotent by design.

ALTER TABLE api_auth_refresh_tokens
  ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

CREATE INDEX IF NOT EXISTS idx_api_auth_refresh_tokens_last_seen_at
  ON api_auth_refresh_tokens (last_seen_at);
