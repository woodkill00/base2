-- Contract phase after runner-managed bounded delivery-key backfill.
ALTER TABLE api_email_outbox
  DROP CONSTRAINT IF EXISTS api_email_outbox_delivery_key_present;
ALTER TABLE api_email_outbox
  ADD CONSTRAINT api_email_outbox_delivery_key_present
  CHECK (delivery_key IS NOT NULL) NOT VALID;
ALTER TABLE api_email_outbox VALIDATE CONSTRAINT api_email_outbox_delivery_key_present;
ALTER TABLE api_email_outbox ALTER COLUMN delivery_key SET NOT NULL;
CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS api_email_outbox_delivery_key_uidx
  ON api_email_outbox(delivery_key);
