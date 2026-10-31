# Base2 Production Activation Runbook

## Status and authority

This runbook prepares a future production activation; it does not authorize one.
Feature 106 deliberately rejects production in its repository executor. A live
activation must be a new exact-source, exact-environment operation with separate
owner approvals for publication, merge, provider spending, DNS mutation,
production certificate issuance, deployment, destructive migration, and owned
resource teardown as applicable.

Never paste credential values into a command, approval, log, issue, pull request,
or evidence artifact. Operators provide approved Vaultwarden references; the
runtime resolves values just in time through the environment-specific identity.

## Recovery roles

Roles are resolved from the private operator registry at activation time rather
than storing personal contact data in this repository.

| Role                | Responsibility                                                              |
| ------------------- | --------------------------------------------------------------------------- |
| Release owner       | Confirms exact release, environment, scope, expiry, and traffic decision    |
| Security observer   | Independently verifies approvals, secret boundaries, audit, and alerts      |
| Data recovery owner | Controls backup, isolated restore, migration compatibility, and legal holds |
| Service operator    | Observes health, synthetics, capacity, incidents, and rollback              |
| Provider owner      | Approves bounded spend, DNS/certificate work, and exact owned teardown      |

No one role implicitly grants another role's protected action.

## Required inputs

- Clean, reviewed source commit and immutable release manifest.
- Identical staging artifacts: image digests, migrations, configuration digest,
  SBOM, provenance, checksums, and signature.
- Two current complete-gate manifests tied to the candidate source.
- Fresh independent code, security, UX/accessibility, data, and operations reviews.
- Successful production-like ephemeral canary using synthetic data and staging
  certificates, followed by verified exact teardown and empty owned inventory.
- Measured capacity, cost ceiling, service objectives, error budgets, recovery
  objectives, and honest residual-risk record for the target environment.
- Current encrypted backup plus successful isolated restore and reconciliation.
- Previous compatible immutable release identifier and migration compatibility
  window.
- Exact, unexpired approvals for every protected action that will be requested.

Missing, stale, ambiguous, partial, divergent, or tampered input blocks activation.

## Preflight

1. Record the candidate commit and verify the worktree and submodules are clean.
2. Validate the release signature and every manifest member digest.
3. Confirm artifacts are the reviewed staging artifacts and were not rebuilt.
4. Validate configuration-profile differences and confirm no secret values are
   present in generated output.
5. Confirm production certificate and DNS operations are absent unless their
   exact independent approvals are attached.
6. Verify database pool limits, migration phase, mixed-version compatibility,
   backup age/integrity, restore evidence, and available capacity.
7. Confirm private surfaces remain restricted to approved role and network gates.
8. Confirm alert delivery, fallback queue, incident ownership, and the native
   operations center are healthy.
9. Confirm feature flags are typed, scoped, observable, reversible, and unexpired.
10. Re-run the exact candidate's required hosted checks. Any non-pass blocks.

## Backup and isolated restore

Production backup configuration is an owner-only JSON file outside the repository.
It names an owner-only libpq service file, an owner-only Vaultwarden-resolved
base64url encryption-key file, the local object root, private backup/receipt roots,
retention, and a bounded retained count. Database URLs and credential values are
never command arguments. Install `base2-production-backup@.service` and its timer
only after the data recovery owner approves the exact target and paths. The timer
runs daily with jitter and persistent catch-up; overlapping executions fail closed.

Use `scripts/bash/production-backup.sh verify` against the resulting HMAC-bound
receipt. Retention deletes only an exact encrypted backup whose digest matches a
valid owned receipt; unknown or tampered files are retained for review. The backup
contains the real `pg_dump` plus every inventory-bound object payload, not only a
synthetic inventory.

Restore first with `restore-isolated` into a newly provisioned marked restore root.
Database restoration additionally requires `restore-database-isolated`, a separate
owner-only libpq service file, and an exact empty database named with the
`base2_restore_`, `base2_preview_`, or `base2_test_` boundary. The tool verifies the
actual database identity and emptiness before `pg_restore`, then reconciles table
and object evidence. It cannot target a normal production database name. Promotion
or replacement of production data remains a separately approved operation outside
this entrypoint.

## Traffic sequence

1. Acquire the environment-scoped deployment lease and create the integrity-bound
   journal before any provider mutation.
2. Apply only compatible expand or migrate phases. Contract/destructive phases
   require a separate exact approval and cannot be inferred.
3. Start the immutable candidate without traffic and verify dependency health.
4. Run anonymous, member, editor, administrator, form, upload, search, logout,
   accessibility, visual, privacy, and security synthetics.
5. Move only the approved canary percentage. Observe objectives, error budget,
   database/queue pressure, and alert delivery for the predeclared bounded window.
6. Promote only when every blocking health and synthetic gate is current and green.
7. Write a sanitized exact-source receipt for each checkpoint. Lost responses use
   exact replay; altered replay or concurrent mutation fails closed.

## Halt and rollback

Any blocking health, synthetic, integrity, approval, capacity, migration, or alert
failure halts traffic movement. Select the recorded previous compatible immutable
release; do not rebuild it. Code rollback never deletes durable tenant data and
never implies reverse migration. If schema compatibility is uncertain, keep the
candidate halted, preserve evidence, and escalate to the data recovery owner.

After rollback, verify public/API health, tenant isolation, jobs, schedules,
notifications, database/object/search/configuration consistency, cache state, and
private surfaces. Open or update an incident and record recovery-objective results
and residual risk.

## Completion and teardown

Activation is terminal only when the exact release, traffic state, data state,
monitoring state, receipts, and provider inventory reconcile. Teardown may delete
only resources listed in the separately approved ownership manifest. Unknown or
unowned resources block deletion. A partial provider result remains pending and
must never be reported as success.

## Residual risk

Passing finite tests does not prove absence of unknown defects. Provider outages,
new vulnerabilities, browser changes, credential compromise, operator error, and
unmodeled workload remain possible. Production owners accept documented residual
risk only after reviewing current evidence; elapsed time alone never closes work.

### Security-preserving recovery compatibility

New production backup configurations require `securityTrustedOwner` (the existing
migration/database/SECURITY DEFINER owner), `securityRuntimeRoles` (the restricted
runtime role names), and `securityRoleMap` (an explicit object mapping every
non-`pg_` cluster role name to that identical existing target name). Supply these
through the existing owner-only backup configuration, not command-line credentials.
The supported boundary is the same PostgreSQL major and role topology. Both databases
must already have the approved owner, database ACLs and database/role settings; the
recovery tool never changes roles, memberships, passwords or database privileges.

New archives contain authenticated `security.json`, bound to the exact database dump.
Ownership, ACLs (including PUBLIC function EXECUTE revocations), RLS/FORCE and policies
are preserved by transactional restore and checked before any restored application SQL
or successful restore receipt. Missing/unmapped/renamed or escalated roles and any
security mismatch fail closed. A failed parity check leaves the isolated target
unaccepted: do not connect runtime users or promote it. Dispose of the isolated target
through its existing authorized lifecycle and correct prerequisites before retrying.

Legacy encrypted archives without this evidence still support `restore-isolated`
offline extraction, explicitly returning `databaseRestoreExecuted: false` and
`securityVerified: false`. They are rejected by `restore-database-isolated` before
`pg_restore`; no readiness or restore-success receipt is issued. Do not reconstruct
ACLs from fixtures or manufacture a manifest for old bytes. Make a new backup from
the verified source using the updated configuration. If that source is unavailable,
legacy disaster recovery requires a separate reviewed recovery/security procedure,
not this supported acceptance path.

The current closed support envelope requires PostgreSQL 15 or newer, a fresh target
with the standard `public` schema owned by `pg_database_owner` and PUBLIC USAGE
without CREATE, and direct-grant runtime roles with no effective membership in any
other role (including predefined `pg_*` authority roles). Every non-predefined cluster
role is mapped; subset maps and cross-cluster logical role renaming are unsupported.
Foreign servers/wrappers/mappings, large objects, subscriptions, event triggers,
non-`plpgsql` extensions, custom languages and user aggregates are unsupported and
fail closed. Do not remove legitimate source objects to make the check pass; request
separately reviewed support for that recovery topology.

The closed envelope also rejects parameter-level ACL grants, publications, user-schema
collations/operators/operator classes/operator families/conversions/text-search
objects, and any stored role/database settings. These authority and execution settings
require separate reviewed support; never clear legitimate settings or privileges to
force acceptance. Database encoding, locale/provider, ICU rules and collation version
must match exactly, and internal constraint triggers must retain ordinary enabled
execution. Connection-local test/service settings are not transported as role settings.

#### Security manifest version 2

Database-restore acceptance now requires security-manifest version 2. Version 1
security manifests, like archives with no security manifest, remain extract-only;
they are never silently reinterpreted or upgraded. Create a fresh backup from the
verified source for this recovery path. The outer backup configuration and encryption
format are unchanged.

Version 2 records effective ACLs using PostgreSQL's `acldefault` for the precise
object kind and owner only when the catalog ACL is SQL NULL. Explicit empty ACLs
never trigger that fallback. Grantor, grantee, grant options and PUBLIC privileges
remain significant; function PUBLIC EXECUTE revocations cannot become default
EXECUTE permission. Column defaults are separately empty because table privileges
are recorded on their relation, not duplicated as column grants. Explicit default-
privilege rows and non-ACL-bearing relation kinds retain their existing boundaries.

PostgreSQL may restore a literal `character varying` array cast to `text[]` using
individual text casts on each element. Only this proven plain-literal spelling is
canonicalized in constraint definitions and policy expressions. String contents,
all surrounding clauses, values/order, owners and other security state must still
match. Escape-prefixed/backslash-ambiguous literals, typmods, collations, nested or
nonliteral arrays and other casts are not generalized. No database functions are
evaluated, no grants repaired, and unknown differences still deny acceptance.
