# Data-rights operations

Base2 implements export, correction, and deletion as durable asynchronous
operations. They are account-owned and tenant-bound. Enqueue and export
download require recent reauthentication; status reads require the same
authenticated account and tenant. Administrators may view bounded status only
when current server-side membership grants `audit.read`.

## Lifecycle

1. The API validates the fixed operation payload and encrypts it using
   `IDENTITY_ENCRYPTION_KEY` before inserting a `queued` row.
2. A partial unique index allows only one queued/running operation of each kind
   for an account and tenant. Repeated requests return the existing operation
   and do not dispatch duplicate work.
3. Celery claims a row with a guarded `queued` to `running` transition. Broker
   failure is returned as `dispatch=deferred`; a bounded five-minute scanner
   redispatches durable queued rows.
4. Completion encrypts the result and binds its canonical JSON to operation,
   tenant, account, and schema version with an HMAC-SHA256 receipt.
5. Export download decrypts and verifies that receipt, emits `Cache-Control:
no-store`, and fails closed on corruption or wrong ownership.
6. A daily retention task clears request ciphertext, result ciphertext, and
   receipt material, then marks the operation `expired`.

Correction is restricted to `display_name`, `avatar_url`, and `bio`. Deletion
removes the current tenant membership, revokes sessions and API credentials,
deletes MFA/recovery/challenge material, and anonymizes/deactivates the account.
It requires the exact confirmation `DELETE`. Operation failures store only the
generic code `processing_failed`; details belong in redacted server telemetry.

## Restore boundary

Exports support integrity-checked isolated preview only. The restore helper
rejects live or production targets and does not write data. Any future live
restore requires a separately reviewed workflow with target identity,
migration preflight, authorization, backup, rollback, and audit evidence.

## Operator checks

- Monitor queued operations older than the replay interval and failed
  operations by generic error code.
- Confirm the Celery worker and beat scheduler are both healthy.
- Rotate `IDENTITY_ENCRYPTION_KEY` only through a separately planned migration;
  replacing it without re-encryption makes retained ciphertext unreadable.
- Never log request/result ciphertext, plaintext exports, MFA secrets, recovery
  codes, or API credential secrets.
