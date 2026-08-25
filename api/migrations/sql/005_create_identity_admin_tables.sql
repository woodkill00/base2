-- Public-account tenant administration. Django operator identities are a
-- separate realm and are intentionally not referenced here.

CREATE TABLE IF NOT EXISTS api_identity_organizations (
  id UUID PRIMARY KEY,
  tenant_id TEXT NOT NULL UNIQUE CHECK (tenant_id ~ '^[a-z0-9][a-z0-9-]{0,62}$'),
  name TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS api_identity_memberships (
  organization_id UUID NOT NULL REFERENCES api_identity_organizations(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES api_auth_users(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('owner', 'admin', 'editor', 'viewer')),
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'suspended')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (organization_id, user_id)
);
CREATE INDEX IF NOT EXISTS api_identity_memberships_user_idx
  ON api_identity_memberships(user_id, status);

CREATE TABLE IF NOT EXISTS api_identity_invitations (
  id UUID PRIMARY KEY,
  organization_id UUID NOT NULL REFERENCES api_identity_organizations(id) ON DELETE CASCADE,
  email TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('admin', 'editor', 'viewer')),
  token_hash TEXT NOT NULL UNIQUE,
  expires_at TIMESTAMPTZ NOT NULL,
  accepted_at TIMESTAMPTZ NULL,
  revoked_at TIMESTAMPTZ NULL,
  created_by UUID NOT NULL REFERENCES api_auth_users(id) ON DELETE RESTRICT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS api_identity_invitations_org_idx
  ON api_identity_invitations(organization_id, expires_at, revoked_at);

CREATE TABLE IF NOT EXISTS api_identity_authenticators (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES api_auth_users(id) ON DELETE CASCADE,
  kind TEXT NOT NULL CHECK (kind IN ('totp', 'webauthn')),
  credential_id TEXT NOT NULL DEFAULT '',
  secret_ciphertext TEXT NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_used_at TIMESTAMPTZ NULL,
  UNIQUE (user_id, kind, credential_id)
);

CREATE TABLE IF NOT EXISTS api_identity_recovery_codes (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES api_auth_users(id) ON DELETE CASCADE,
  code_hash TEXT NOT NULL UNIQUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  used_at TIMESTAMPTZ NULL
);
CREATE INDEX IF NOT EXISTS api_identity_recovery_user_idx
  ON api_identity_recovery_codes(user_id, used_at);

CREATE TABLE IF NOT EXISTS api_identity_login_challenges (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES api_auth_users(id) ON DELETE CASCADE,
  token_hash TEXT NOT NULL UNIQUE,
  expires_at TIMESTAMPTZ NOT NULL,
  consumed_at TIMESTAMPTZ NULL,
  ip TEXT NOT NULL DEFAULT '',
  user_agent TEXT NOT NULL DEFAULT '',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS api_identity_login_challenges_user_idx
  ON api_identity_login_challenges(user_id, expires_at, consumed_at);

CREATE TABLE IF NOT EXISTS api_identity_credentials (
  id UUID PRIMARY KEY,
  organization_id UUID NOT NULL REFERENCES api_identity_organizations(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES api_auth_users(id) ON DELETE RESTRICT,
  label TEXT NOT NULL,
  prefix TEXT NOT NULL UNIQUE,
  secret_hash TEXT NOT NULL UNIQUE,
  scopes JSONB NOT NULL DEFAULT '[]'::jsonb,
  expires_at TIMESTAMPTZ NULL,
  revoked_at TIMESTAMPTZ NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_used_at TIMESTAMPTZ NULL
);
CREATE INDEX IF NOT EXISTS api_identity_credentials_org_idx
  ON api_identity_credentials(organization_id, revoked_at);
