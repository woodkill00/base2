from django.db import migrations

FORWARD_SQL = """
ALTER TABLE api_data_rights_operations
  ADD COLUMN IF NOT EXISTS claim_token UUID NULL,
  ADD COLUMN IF NOT EXISTS claim_expires_at TIMESTAMPTZ NULL;
UPDATE api_data_rights_operations
   SET status='queued', claim_token=NULL, claim_expires_at=NULL,
       error_code='worker_claim_recovered', updated_at=NOW()
 WHERE status='running' AND (claim_token IS NULL OR claim_expires_at IS NULL);
ALTER TABLE api_data_rights_operations
  DROP CONSTRAINT IF EXISTS api_data_rights_claim_pair;
ALTER TABLE api_data_rights_operations
  ADD CONSTRAINT api_data_rights_claim_pair CHECK (
    (status = 'running' AND claim_token IS NOT NULL AND claim_expires_at IS NOT NULL)
    OR
    (status <> 'running' AND claim_token IS NULL AND claim_expires_at IS NULL)
  );
CREATE INDEX IF NOT EXISTS api_data_rights_claim_expiry_idx
  ON api_data_rights_operations(status, claim_expires_at);
"""

REVERSE_SQL = """
DROP INDEX IF EXISTS api_data_rights_claim_expiry_idx;
ALTER TABLE api_data_rights_operations DROP CONSTRAINT IF EXISTS api_data_rights_claim_pair;
ALTER TABLE api_data_rights_operations DROP COLUMN IF EXISTS claim_expires_at;
ALTER TABLE api_data_rights_operations DROP COLUMN IF EXISTS claim_token;
"""


def forward(apps, schema_editor):
    del apps
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(FORWARD_SQL)


def reverse(apps, schema_editor):
    del apps
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(REVERSE_SQL)


class Migration(migrations.Migration):
    dependencies = [("api_schema", "0004_protect_api_audit_events")]
    operations = [migrations.RunPython(forward, reverse)]
