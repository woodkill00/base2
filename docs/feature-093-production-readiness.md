# Feature 093 production-readiness guide

Feature 093 turns Base2 into a versioned, secure website foundation and a deterministic website factory. It does not activate a production site, permanent hosting, production payments, live certificate issuance, or unrestricted automation.

## Migration and upgrades

1. Pin the exact Base2 source commit and export it with the supported factory command.
2. Validate the factory profile, provenance, module compatibility, governance files, and child-local complete gate before review.
3. Run the upgrade advisor in preview mode. Its patch is data only and is never applied, pushed, merged, or deployed automatically.
4. Back up persistent state with the authenticated recovery workflow before migrations.
5. Reject downgrades, stale backups, unknown modules, incompatible versions, route conflicts, and missing migrations.
6. Promote an immutable digest-bound release only after health evidence. Retain the exact prior release for rollback.

Core persistence remains Django and PostgreSQL. FastAPI mirrors the declared contract and React remains an untrusted client; a migration must not move authoritative business state into the browser or an optional module.

## Operations

Use the versioned complete gate as the release truth. Every required check reports `passed`, `failed`, `blocked`, or `unavailable`; required missing tools and dependency failures never become success. The WSL recovery launcher may restart WSL once only when every failed check carries a recognized native-runtime corruption signature and the exact commit remains unchanged.

Observe structured health, queues, logs, metrics, traces, leases, DNS transactions, cost, and incident transitions. Alerts are idempotent: one failure notification and one recovery notification per incident. Preview cleanup compares lease identity, provider ID, ownership tag, and DNS history before mutation. Ambiguity fails closed.

## Security boundary

- Secrets are resolved just in time from a private SecretRef and never belong in Git, child archives, reports, logs, screenshots, or generated repositories.
- Tenant, identity realm, role, permission, CSRF, replay, rate-limit, MIME, size, quarantine, data-rights, audit, and provider-capability boundaries are required tests.
- Provider input, repository content, profiles, modules, and generated output are treated as untrusted data. No request-supplied command is executed.
- The edge policy denies private admin routes and dangerous defaults. Production certificates are impossible in Feature 093: the accepted canary is hard-wired to Let’s Encrypt staging.
- Security scanner absence, timeout, malformed output, critical/high findings, secret-pattern findings, or provenance mismatch fails the required gate.

## Modules and factory

Modules use strict versioned manifests, namespaced permissions, declared routes/jobs/models/migrations/settings/health/capabilities, dependency ordering, and explicit data lifecycle. Installation, disable, export, upgrade, rollback, and destructive removal are distinct operations. Destructive removal and live capability activation require separate authority.

The factory exports an exact committed tree, excludes the parent worktree and runtime state, transforms only allowlisted declarative fields, emits provenance/governance/security files, and runs the child-local gate. Blog/portfolio, SaaS, and marketplace fixtures demonstrate different deterministic outputs from one foundation commit.

## Cost and ephemeral previews

Every live preview requires a separately approved exact plan binding source/archive digests, provider target, DNS mutation, ownership namespace, region/size/image, lease, concurrency, trial count, certificate mode, and cost ceilings. Admission reads exact owned inventory before creation. DNS is published only after health, and inactive previews must consume zero Droplet runtime after bounded cleanup.

The Feature 093 generated-child acceptance used three sequential one-droplet trials, a 15-minute maximum lease per trial, a USD 1.00 total ceiling, and staging-only certificates. All three leases ended `destroyed`; independent reconciliation found zero exact droplets and zero exact DNS records. The estimated total was three US cents.

## Recovery

Persistent state is classified before teardown. Required state is encrypted with AES-256-GCM, bound to target/schema/SecretRef metadata, atomically stored owner-only, verified before deletion, restored only to an absent isolated target, and checked for exact digest and schema compatibility. Wrong target, wrong key, corruption, partial output, stale schema, existing target, and expired retention fail closed.

Release rollback restores the exact prior immutable identity. Recovery evidence records RPO/RTO, three backup/restore cycles, three release cycles, incident and recovery notifications, staging certificate behavior, and zero retained temporary state. Live canary evidence adds three independently destroyed leases and DNS restoration observations.

## Drift and evidence

`python3 scripts/python/validate_surface_drift.py` verifies locked SHA-256 inventories for documentation, configuration, OpenAPI contracts, generated client/profile artifacts, module manifests, and route sources. New, missing, or changed entries fail with a group and path. Intentional changes require review and an explicit `--write`, followed by hostile drift tests and the full gate.

The final experience ledger is built with `scripts/python/feature_093_closeout.py experience`; the recovery ledger uses `recovery` plus the exact live and operations results. Both refuse incomplete or mismatched evidence. Generated ledgers are private artifacts unless deliberately reviewed for publication.

## Activation and residual risk

Local/providerless tests do not grant provider authority. Push, PR creation, merge, production deployment, permanent hosting, public production DNS, production certificates, payments, credentials, destructive module removal, and broader automation each remain separately approved.

Automated testing gives full evidence coverage for declared requirements, routes, controls, states, authority boundaries, and known failure classes; it cannot prove unknown defects impossible. Residual risks include provider outages, upstream image changes, browser/platform changes, compromised credentials, DNS propagation, capacity beyond the tested profile, and operator approval mistakes. Mitigations are exact pinning, least privilege, bounded leases/cost, immutable evidence, monitoring, backup/restore drills, independent inventory reconciliation, and fail-closed approvals.

## Release checklist

1. Worktree is clean and the reviewed commit is exact.
2. Spec-Kit analysis has zero findings and all completed tasks cite evidence.
3. Surface drift and injected stale-artifact tests pass.
4. Two consecutive complete gates pass at the same exact commit; all skips and unavailable tools are reconciled.
5. Experience and recovery ledgers bind that commit and the accepted live evidence.
6. Secret scans and dependency/security audits have zero unaccepted findings.
7. The PR is reviewed before any merge. Deployment or production activation receives a separate exact approval.

## Feature 093 closeout evidence

The implementation candidate `05e71a59bcb7528791af5dab2ccadff9462338cc` passed two consecutive local complete gates. Each executed all 77 required checks with zero failures, skips, blocked checks, or unavailable tools. The same commit passed two consecutive attempts of all seven push workflows: backend, frontend, contract, E2E, smoke, repository guards, and the Option1 authority guard.

The integrity-bound experience ledger passed for both fixture brands, four enabled pack families, and all required route/control/accessibility/visual/performance checks. Its SHA-256 is `66ac50eb11e8467d7d50f21eb77be12d49d57acf7caecf35df879d035616719f`.

The integrity-bound recovery ledger passed with three backup/restore/rollback cycles, three destroyed live-canary leases, restored DNS, zero provider resources, zero secret values emitted, RPO 0 seconds, and an RTO ceiling of 60 seconds. Its SHA-256 is `3cec4cf8268287d425ab19093f98ace0896d10725759f3260af2c988c73d9fe7`.

No pull request, merge, production deployment, permanent resource, live certificate, or provider mutation is authorized by this closeout. The pushed feature branch remains the review boundary until a separate owner decision.
