# Base2 Production Readiness Program

## Baseline

Feature 106 began from clean Base2 `main` at
`dc2ffa14e992586afba8461cd6567fd364c96088`. The machine-readable inventory is
`shared/config/production-readiness-v1.json`; its validator rejects repository
module, site-profile, or workflow drift until the inventory is deliberately
reviewed and updated.

Base2 already has a deterministic site factory, module manifests, tenant-aware
Django/FastAPI contracts, React user interfaces, settings, content/data and
media workspaces, staging-certificate previews, bounded DigitalOcean lifecycle
tools, supply-chain policy, visual assurance, and complete-gate orchestration.
Feature 106 does not treat those as production evidence without current
integration proof.

## Capability classification

| Area            | Baseline capability                            | Feature 106 work                                                                  |
| --------------- | ---------------------------------------------- | --------------------------------------------------------------------------------- |
| Site generation | Deterministic manifests and generated profiles | Production archetypes, lifecycle, compatibility, cost and acceptance              |
| Modules         | Closed manifests and dependency order          | Complete observability, backup, resource, migration and uninstall contracts       |
| Identity        | OAuth/session/role security foundations        | MFA/passkeys, device sessions, recovery and cross-layer policy parity             |
| Settings        | Unified settings platform                      | Complete scope, locale, history, consequence and conflict behavior                |
| Content/data    | Universal governed workspace                   | Editorial workflow, preview, search, object delivery and scale                    |
| Media           | Quarantine-first governed library              | Production object storage, CDN, resumable transfer and lifecycle economics        |
| Preview         | Bounded staging-certificate DigitalOcean flows | Immutable promotion, canary/blue-green, replay-safe rollback and evidence         |
| Operations      | Structured telemetry and local incident ledger | Native multi-site operations center, synthetics, objectives, incidents and alerts |
| Recovery        | Recovery contracts and selected drills         | Integrated database/object/search restore, PITR capability and disaster proof     |
| Security        | Tenant, secret, edge and supply-chain checks   | Key lifecycle, network egress, break glass, governance and adversarial matrix     |

## Environments

- Development and test are provider-free and use disabled certificate issuance.
- Preview and staging use synthetic data and staging certificates only. Provider
  access requires an exact, expiring approval.
- Production configuration describes the target contract but grants no runtime
  authority. Live deployment, DNS mutation, production certificates, spending,
  credentials, destructive migrations, and teardown are separately approved.
- Artifacts move from staging to production without rebuild. A dirty, mutable,
  divergent, incomplete, or unsigned candidate is rejected.

## Data and trust model

The public edge and browser are untrusted. Application services operate with
least privilege. PostgreSQL forced tenant isolation is the final tenant-data
backstop. Global worker discovery is bounded and separated from tenant-bound
mutation transactions. Hostile media parsing remains isolated. Operational
telemetry is minimized and cannot contain credentials, request bodies, upload
bytes, message contents, or unrestricted labels. Provider and secret control
planes are separate from tenant workloads.

Sensitive data requires encryption in transit and at rest with explicit key
identity and rotation. Internal service networks and outbound access are
least-privilege and tested against SSRF, metadata access, DNS rebinding, lateral
movement, and exfiltration.

## Resource defaults

The checked-in defaults are conservative admission ceilings, not capacity
claims: 30-second requests, 300-second job leases, five attempts, eight
concurrent tenant operations, 30-day telemetry, 365-day incidents, 120-minute
ephemeral lifetime, and a USD 1.00 ephemeral cost ceiling. Each production
profile must replace assumptions with measured capacity evidence before live
activation.

## Release and recovery rule

Release bundles bind exact source, clean state, immutable images, migration and
configuration digests, SBOM, provenance, artifact digest, creation time, and
signature. Protected transitions use fixed typed actions, exact targets,
expiring approvals, checkpoints, receipts, and independent observation.

Rollback selects the prior compatible immutable release. Database evolution
uses expand/migrate/contract sequencing; contraction cannot be inferred from a
code rollback. Capability disable preserves recoverable data while removing
routes, navigation, workers, schedules, new storage allocation, credential
resolution, and provider actions.

## Evidence and completion

Each workstream requires current unit, integration, migration, contract,
frontend, E2E, tenant, security, accessibility, visual, performance, recovery,
and fault evidence appropriate to its boundary. Unknown defects remain
possible. Native monitoring, incident response, bounded recovery, and honest
residual-risk reporting cover what finite pre-release testing cannot prove.
