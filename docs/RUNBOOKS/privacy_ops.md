# Privacy Operations Runbook

This runbook documents the procedures for per-tenant data export and deletion.

- Export endpoint: POST /privacy/export
  - Required: header X-Tenant-Id
  - Returns: { accepted: true, operation: "export", tenant_id }
  - Implementation notes: enqueue export job for tenant, stream result to secure location, audit the request.

- Delete endpoint: POST /privacy/delete
  - Required: header X-Tenant-Id
  - Returns: { accepted: true, operation: "delete", tenant_id }
  - Implementation notes: enqueue deletion with irreversible semantics, soft-delete window optional, audit thoroughly.

Validation Checklist:

- Tenant header required and verified for all operations.
- Exports include all user- and tenant-scoped records.
- Deletion covers all PII; irreversible and auditable.
- Access to artifacts restricted; links expire.
