CREATE TABLE IF NOT EXISTS api_data_rights_operations (
  id UUID PRIMARY KEY,
  tenant_id TEXT NOT NULL CHECK (tenant_id ~ '^[a-z0-9][a-z0-9-]{0,62}$'),
  user_id UUID NOT NULL REFERENCES api_auth_users(id) ON DELETE CASCADE,
  kind TEXT NOT NULL CHECK (kind IN ('export', 'correction', 'deletion')),
  status TEXT NOT NULL DEFAULT 'queued'
    CHECK (status IN ('queued', 'running', 'completed', 'failed', 'expired')),
  request_ciphertext TEXT NOT NULL,
  result_ciphertext TEXT NOT NULL DEFAULT '',
  receipt_digest TEXT NOT NULL DEFAULT '',
  error_code TEXT NOT NULL DEFAULT '',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  started_at TIMESTAMPTZ NULL,
  completed_at TIMESTAMPTZ NULL,
  retention_until TIMESTAMPTZ NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS api_data_rights_owner_idx
  ON api_data_rights_operations(tenant_id, user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS api_data_rights_retention_idx
  ON api_data_rights_operations(status, retention_until);
CREATE UNIQUE INDEX IF NOT EXISTS api_data_rights_active_kind_idx
  ON api_data_rights_operations(tenant_id, user_id, kind)
  WHERE status IN ('queued', 'running');
