-- Durable, replay-safe ownership for data-rights work.
ALTER TABLE api_data_rights_operations
  ADD COLUMN IF NOT EXISTS claim_token UUID NULL,
  ADD COLUMN IF NOT EXISTS claim_expires_at TIMESTAMPTZ NULL;

ALTER TABLE api_data_rights_operations
  DROP CONSTRAINT IF EXISTS api_data_rights_claim_pair;
ALTER TABLE api_data_rights_operations
  ADD CONSTRAINT api_data_rights_claim_pair CHECK (
    (status = 'running' AND claim_token IS NOT NULL AND claim_expires_at IS NOT NULL)
    OR
    (status <> 'running' AND claim_token IS NULL AND claim_expires_at IS NULL)
  ) NOT VALID;

-- Legacy running rows have no trustworthy owner. Make them replayable before
-- validating the fence; their request ciphertext and retention deadline remain.
UPDATE api_data_rights_operations
   SET status='queued', claim_token=NULL, claim_expires_at=NULL,
       error_code='worker_claim_recovered', updated_at=NOW()
 WHERE status='running' AND (claim_token IS NULL OR claim_expires_at IS NULL);

ALTER TABLE api_data_rights_operations
  VALIDATE CONSTRAINT api_data_rights_claim_pair;
CREATE INDEX IF NOT EXISTS api_data_rights_claim_expiry_idx
  ON api_data_rights_operations(status, claim_expires_at);
