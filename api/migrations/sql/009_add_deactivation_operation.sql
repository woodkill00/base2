ALTER TABLE api_data_rights_operations
  DROP CONSTRAINT IF EXISTS api_data_rights_operations_kind_check;
ALTER TABLE api_data_rights_operations
  ADD CONSTRAINT api_data_rights_operations_kind_check
  CHECK (kind IN ('export', 'correction', 'deactivation', 'deletion'));
