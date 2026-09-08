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
