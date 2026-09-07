# Implementation plan

## Delivery shape

Feature 106 is an umbrella program delivered as independently reviewable release
trains on this branch. Each train follows Django model and migration contracts,
then FastAPI contracts, then React integration, then operational and visual
evidence. A train cannot consume the authority of another train merely because
both appear in this feature.

## Architecture

1. Establish the exact baseline, capability inventory, data classification,
   threat model, service objectives, release contract, and program validator.
2. Add a private native operations plane using bounded structured events,
   health samples, synthetic results, incidents, and sanitized alert delivery.
   Monitoring storage and credentials remain isolated from tenant workloads.
3. Separate environment profiles and construct immutable release bundles that
   move through preview, staging, canary, promotion, and rollback without rebuild.
4. Harden PostgreSQL and object durability with forced tenant isolation,
   compatibility-aware migrations, encrypted backups, optional PITR, and
   isolated restore/reconciliation drills.
5. Harden Traefik and domain automation while keeping privileged consoles
   private and preserving the staging-only certificate policy in all repository
   and routine acceptance work.
6. Standardize secrets, security audit, durable jobs, schedules, email, and
   notification contracts before higher-level product automation depends on them.
7. Complete tenant lifecycle, quota, identity, session, policy, settings,
   tenant-safe search, editorial, and production media integration.
8. Add constrained visual composition, versioned themes, archetype contracts,
   module lifecycle, integrations, and optional commerce behind closed manifests.
9. Enforce performance, cost, supply-chain, privacy, resilience, accessibility,
   and developer-experience gates across the resulting platform.
10. Produce exact-source local and hosted evidence. A production-like ephemeral
    canary and its destroy operation require separate approvals; actual production
    activation requires another approval after canary evidence is reviewed.

## Release-train gates

Every train must satisfy the following before the next train can depend on it:

- closed requirements and traceability;
- forward and compatibility-aware migration proof;
- tenant, role, replay, race, hostile-input, and resource-boundary tests;
- source-bound accessibility, interaction, and visual proof when user-facing;
- performance, dependency, secret, license, and static-security checks;
- bounded fault, restart, rollback, and evidence-integrity tests;
- independent code, security, UX, and operations review appropriate to risk;
- no critical, high, or medium unresolved finding;
- a documented residual-risk and disabled-capability statement.

## Data and trust boundaries

- Django remains the domain-model source of truth; FastAPI mirrors versioned
  contracts and React remains an untrusted client.
- PostgreSQL forced tenant isolation is the final data-plane backstop for
  tenant-owned records. Global worker discovery is bounded and separated from
  tenant-bound mutation transactions.
- Operational telemetry is a separate minimized data class. It may reference
  opaque tenant, release, service, and incident identifiers but not credentials,
  message bodies, uploaded bytes, access tokens, or unrestricted request data.
- Object storage exposes opaque identifiers. Private delivery is authorization
  checked, expiry bound, and cache safe.
- Privileged operations use fixed typed actions, exact targets, expiring
  approvals, JIT secrets, receipts, and independent observation.

## Rollback and recovery

Code rollback selects a previous immutable compatible release. Database changes
use expand/migrate/contract sequencing; destructive contraction is delayed until
compatibility evidence and a separate approval exist. Capability disable removes
routes, navigation, workers, schedules, and new allocation authority while
preserving recoverable data. Provider teardown is exact-resource bound, verified,
and never inferred from failed deployment or expired approval.

## Cost and provider policy

Local and CI work is provider free. Provider-backed acceptance declares maximum
resources, region, runtime, cost ceiling, source digest, teardown deadline, and
cleanup owner before approval. Ephemeral resources default to destroy, and an
empty-inventory receipt is required. Long-lived production resources are outside
this feature's implicit authority.

## Completion rule

The program is implementation-complete only when every task is checked from real
evidence, the validator and full gates pass at the exact head, all findings are
closed or explicitly owner-accepted below the blocking threshold, documentation
matches behavior, and all approved ephemeral resources are proven absent. Finite
testing demonstrates the declared matrix; it does not prove unknown defects
impossible.
