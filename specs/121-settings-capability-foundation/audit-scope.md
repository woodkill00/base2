# Organization audit boundary repair

## User acceptance — AC9

An authorized organization administrator sees only events explicitly recorded for
that organization and its tenant, even when the actor belongs to multiple
organizations. Personal security activity and historical events lacking a complete
organization scope are not disclosed or reassigned to an organization. Correctly
scoped organization history remains visible after an actor leaves. A user's own
account-wide security history retains its existing behavior.

## Technical plan

Reuse the existing append-only audit entity and redacted metadata; no new domain
model or database migration is required. Organization mutation routes record
`tenant_id` from the validated tenant context and `organization_id` from authorized
membership or the successful organization/invitation repository result. Never use
an organization ID submitted in the body to establish audit scope. The overview
requires exact equality of both metadata fields, rather than inferring event
ownership from present-day actor memberships. Shared audit insertion retains
recursive sensitive-value redaction. No historical audit rows are rewritten.

Existing response schemas remain unchanged. Legacy unscoped rows intentionally
disappear from organization views; they remain intact and retain existing
account-level visibility. Reverting this security boundary would reintroduce the
privacy defect and is not a safe functional rollback.

## Tasks and issue ledger

- [x] **AUD-01 / privacy boundary:** Reproduce current cross-organization and
      personal-event disclosure using SQL-executing fixtures. Same root cause also
      loses valid historical events after member removal. Initial run: 11 expected
      failures in `api/tests/test_identity_admin_audit_scope.py` on unmodified code.
- [x] **AUD-02:** Add trusted complete scope at all organization mutation audit
      writers; regress exact scope, untrusted IDs, failed mutations and account events.
- [x] **AUD-03:** Replace overview membership-based inference with exact scope;
      regress dual membership, mixed scope, legacy rows, member removal and redaction.
- [x] **AUD-04:** Extend the existing real PostgreSQL identity acceptance runner
      with the same tenant/privacy boundary and retained-history assertions.
- [x] **AUD-05:** Run targeted tests and review changed-line coverage. Final local
      targeted run: 72 passed, including existing identity/MFA/session/navigation
      coverage; modified repository and route modules each have 91% statement coverage.
      All enclosing statements for the modified query and audit metadata calls execute.
      Focused Ruff, Python compilation, and whitespace checks pass. Initial 11 SQL
      fixture failures and six missing-scope writer failures are retained as evidence.
- [ ] **AUD-06 / release blocker:** Run real PostgreSQL and full Compose acceptance.
      Docker is unavailable locally. The original `identity-postgres-contract` gate
      checks source markers only. A new dedicated `identity-postgres-acceptance` CI job
      now invokes the real checks against an isolated PostgreSQL service; execution
      is pending. A passing unit or SQLite fixture run is not PostgreSQL acceptance.

## Evidence boundary

The SQLite fixture executes the production SELECT predicates with only placeholder
and insertion-cast adaptation; it is not proof of PostgreSQL JSONB, RLS, or triggers.
The supported `scripts/python/run_identity_postgres_acceptance.py` runner remains
the PostgreSQL integration evidence path. No deployment or paid resources are used.
That runner uses a disposable schema-owner connection; it does not establish
restricted-runtime-role RLS or full production-topology acceptance.

Local diagnostic artifacts are in the task scratch directory
`base2-settings-planning/audit-evidence/`: `scope-before.txt`, `writers-before.txt`,
`targeted-final.txt`, `coverage.json`, `changed-line-coverage.json`, and
`lint-final.txt`. These are diagnostic evidence, not release pass receipts.
