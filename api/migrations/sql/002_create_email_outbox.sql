-- 002_create_email_outbox.sql
-- Idempotent: safe to run multiple times.

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
);

CREATE INDEX IF NOT EXISTS api_email_outbox_to_email_idx ON api_email_outbox(to_email);
CREATE INDEX IF NOT EXISTS api_email_outbox_status_created_idx ON api_email_outbox(status, created_at);
