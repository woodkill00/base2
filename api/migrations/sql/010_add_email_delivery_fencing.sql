-- 010_add_email_delivery_fencing.sql
-- Durable claim fencing and stable delivery identity for the transactional outbox.

ALTER TABLE api_email_outbox
  ADD COLUMN IF NOT EXISTS claim_token UUID NULL,
  ADD COLUMN IF NOT EXISTS claim_expires_at TIMESTAMPTZ NULL,
  ADD COLUMN IF NOT EXISTS delivery_key TEXT NULL;

UPDATE api_email_outbox SET delivery_key = id::text WHERE delivery_key IS NULL;
ALTER TABLE api_email_outbox ALTER COLUMN delivery_key SET NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS api_email_outbox_delivery_key_uidx
  ON api_email_outbox(delivery_key);
CREATE INDEX IF NOT EXISTS api_email_outbox_claim_expiry_idx
  ON api_email_outbox(status, claim_expires_at);
