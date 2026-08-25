CREATE OR REPLACE FUNCTION api_reject_audit_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  RAISE EXCEPTION 'api_auth_audit_events is append-only' USING ERRCODE = '55000';
END;
$$;

DROP TRIGGER IF EXISTS api_auth_audit_events_append_only ON api_auth_audit_events;
CREATE TRIGGER api_auth_audit_events_append_only
BEFORE UPDATE OR DELETE ON api_auth_audit_events
FOR EACH ROW EXECUTE FUNCTION api_reject_audit_mutation();
