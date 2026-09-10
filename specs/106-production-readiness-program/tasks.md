# Ordered tasks

Unchecked tasks are required implementation or evidence work. A task may be
checked only from exact-source evidence; a passing helper-level test is not a
substitute for the integration proof named by the task.

## Phase 0 — Program baseline and closed contracts

- [x] B001 Pin the exact clean Base2 baseline and inventory every service, route, module, profile, data store, workflow, and provider boundary. (FR-001, FR-002, FR-072)
- [x] B002 Record current functionality and explicitly distinguish existing capability, production gap, extension, and optional future capability. (FR-068, FR-070)
- [x] B003 Define environment-profile schemas and a machine-readable difference allowlist. (FR-001, FR-026, FR-069)
- [x] B004 Build the release-manifest schema for source, images, migrations, configuration, SBOM, provenance, and checksums. (FR-002, FR-059)
- [x] B005 Model assets, identities, data classes, trust boundaries, cryptographic keys, service networks, attackers, abuse cases, and recovery authorities. (FR-019, FR-031, FR-065, FR-071, FR-073, FR-074)
- [x] B006 Define the tenant-isolation invariant across every synchronous, asynchronous, cached, indexed, exported, stored, and observed surface. (FR-019)
- [x] B007 Define service indicators, objectives, error budgets, recovery objectives, and capacity budgets without inventing unsupported guarantees. (FR-013, FR-057, FR-060, FR-068)
- [x] B008 Define typed approval scopes and exact-target receipts for publication, merge, deployment, provider, DNS, certificate, destruction, and destructive data work. (FR-007, FR-069)
- [x] B009 Define bounded size, time, retry, concurrency, retention, cardinality, and cost defaults for every new resource consumer. (FR-028, FR-042, FR-057, FR-058, FR-071)
- [x] B010 Define capability manifests that prove disabled modules leave no runtime or allocation residue. (FR-054, FR-072)
- [x] B011 Define release-train entry, blocking-review, evidence, rollback, and exit gates. (FR-008, FR-063, FR-068)
- [x] B012 Add an executable Feature 106 plan validator covering task order, requirement traceability, authority phrases, and completion honesty. (FR-007, FR-063, FR-068, FR-069)

## Phase 1 — Native observability and incident center

- [x] B013 Write tests first for telemetry minimization, redaction, tenant separation, cardinality, retention, and deletion. (FR-063, FR-065, FR-071)
- [x] B014 Add Django models and migrations for sites, services, health samples, synthetic runs, objectives, incidents, alerts, acknowledgements, and evidence references. (FR-009, FR-013, FR-014)
- [x] B015 Add forced-RLS and scoped repository proof for tenant-owned operational records and separately bounded platform records. (FR-019, FR-071)
- [x] B016 Add a bounded structured event and metric vocabulary shared by modules without accepting arbitrary sensitive labels. (FR-009, FR-071)
- [x] B017 Implement health adapters for public routes, APIs, PostgreSQL, workers, queues, object storage, DNS, certificates, email, schedules, and capacity. (FR-010)
- [x] B018 Implement truthful dependency states for healthy, degraded, unavailable, stale, unknown, muted, and intentionally disabled. (FR-010, FR-016, FR-070)
- [x] B019 Implement rate-bounded collection, aggregation, retention, and backpressure that cannot harm the monitored workload. (FR-016, FR-057, FR-071)
- [x] B020 Implement safe synthetic journeys for anonymous, member, editor, administrator, forms, uploads, search, and logout using synthetic tenants and data. (FR-011, FR-019)
- [x] B021 Add source-bound visual synthetic checks with deterministic capture, masks, thresholds, baseline review, and drift rejection. (FR-012, FR-064)
- [x] B022 Add incident correlation, deduplication, severity, ownership, timeline, acknowledgement, resolution, recurrence, and post-incident records. (FR-014)
- [x] B023 Add sanitized Discord delivery with expiry, acknowledgement, deduplication, retry, fallback queue, and delivery observation. (FR-015, FR-016)
- [x] B024 Build the private accessible operations UI for fleet, site, service, release, objective, incident, and evidence views. (FR-009, FR-014, FR-064)
- [x] B025 Add role and recent-auth enforcement for incident mutation and bounded recovery controls. (FR-033, FR-045)
- [x] B026 Prove monitor loss, alert loss, stale evidence, flapping, queue pressure, restart, clock shift, and dependency outage fail visibly without alert storms. (FR-016, FR-060, FR-070)
- [x] B027 Run telemetry privacy, accessibility, visual, load, fault, and tenant-isolation gates and close all blocking findings. (FR-019, FR-063, FR-064, FR-065, FR-071)

## Phase 2 — Immutable environments, deployment, and rollback

- [x] B028 Write tests first for profile separation, artifact identity, stale approval, replay, concurrency, interruption, promotion, and rollback. (FR-001, FR-002, FR-003, FR-004, FR-006)
- [x] B029 Implement validated development, test, preview, staging, and production configuration profiles with no secret values in generated artifacts. (FR-001, FR-031)
- [x] B030 Render and verify immutable image digests, migration set, schema version, configuration digest, SBOM, provenance, and source identity. (FR-002, FR-059)
- [x] B031 Implement build-once promotion and reject rebuilt, mutable-tagged, dirty, divergent, or incomplete candidates. (FR-003, FR-059)
- [x] B032 Implement an integrity-bound deployment lease, journal, checkpoint, resume, replay no-op, and stale/concurrent rejection. (FR-004, FR-008)
- [x] B033 Implement fixed canary or blue/green traffic states and typed expiring feature flags with pre-switch and post-switch health and synthetic gates. (FR-005, FR-011, FR-077)
- [x] B034 Implement automatic traffic halt and exact previous-release selection when blocking checks fail. (FR-005, FR-006, FR-070)
- [x] B035 Implement compatibility-aware code rollback that never deletes durable data or performs implicit reverse migration. (FR-006, FR-018)
- [x] B036 Extend the single deployment entrypoint with typed preview, stage, canary, promote, rollback, status, and evidence operations. (FR-004, FR-062)
- [x] B037 Add independent approval verification for each protected release and provider transition. (FR-007, FR-069)
- [x] B038 Produce integrity-bound, redacted, exact-source operation receipts with honest pending and terminal states. (FR-008, FR-034, FR-068)
- [x] B039 Test crash at every deployment checkpoint, lost responses, exact replay, altered replay, expired approval, concurrent runner, and partial provider outcome. (FR-004, FR-060, FR-065)
- [x] B040 Test staged certificate use and prove preview/test cannot issue or request production certificates. (FR-001, FR-026)
- [x] B041 Run production-like local deployment, canary, failure, resume, rollback, and evidence-integrity acceptance with synthetic data. (FR-005, FR-006, FR-063, FR-066)

## Phase 3 — PostgreSQL, durability, retention, and restore

- [x] B042 Write tests first for pooling, pressure, mixed versions, RLS, backup, PITR capability, isolated restore, retention, and reconciliation. (FR-017 through FR-024, FR-066)
- [x] B043 Add verified encrypted database transport/storage configuration, measured connection pooling, transaction/statement timeouts, role limits, saturation admission, and pool health. (FR-017, FR-024, FR-073)
- [x] B044 Inventory all tenant-owned tables and add or repair forced-RLS policies with application, worker, migration, and break-glass roles. (FR-019, FR-033)
- [x] B045 Prove two-tenant and hostile-context isolation through real disposable PostgreSQL across APIs, repositories, jobs, exports, search, media, audit, cache keys, and telemetry. (FR-019, FR-065)
- [x] B046 Add migration metadata for expand, migrate, contract, compatibility window, expected lock, runtime, rollback, and destructive classification. (FR-018, FR-066)
- [x] B047 Add mixed-old/new application migration tests and prevent contraction before compatibility and separate destructive approval. (FR-007, FR-018)
- [x] B048 Implement encrypted database and object inventory backups with explicit key identity, isolated credentials, checksums, retention, rotation, recovery, and manifests. (FR-020, FR-031, FR-073)
- [x] B049 Implement provider-capability detection for PITR and an explicit tested backup fallback when PITR is unavailable. (FR-021, FR-068)
- [x] B050 Implement an isolated restore target guard that rejects every live, production, ambiguous, or unowned destination. (FR-022, FR-065)
- [x] B051 Reconcile restored relational rows, object manifests, search indexes, configuration, tenant boundaries, and audit chains. (FR-022, FR-024)
- [x] B052 Implement retention, archive, legal hold, anonymization, export, and erasure state machines with idempotent audit. (FR-023, FR-034)
- [x] B053 Add backup age, integrity, capacity, slow query, missing index, migration, PITR, restore, and reconciliation signals to operations. (FR-010, FR-024)
- [x] B054 Prove corrupt, incomplete, stale, wrong-key, cross-tenant, interrupted, and malicious restore inputs fail closed. (FR-020, FR-022, FR-065, FR-066)
- [x] B055 Run repeated database migration, RLS, backup, restore, and recovery suites and close all blocking findings. (FR-018, FR-019, FR-020, FR-022, FR-063, FR-066)

## Phase 4 — Edge, domains, certificates, CDN, and private surfaces

- [x] B056 Write tests first for ownership challenge, takeover, canonical hosts, redirects, proxy trust, cache isolation, abuse, and privileged surfaces. (FR-025 through FR-030, FR-065)
- [x] B057 Model tenant domain claims, challenges, verification evidence, canonical selection, lifecycle, and release binding. (FR-025, FR-030)
- [x] B058 Implement replay-safe domain ownership verification and prevent abandoned, reused, wildcard, homograph, and cross-tenant takeover. (FR-025, FR-065)
- [x] B059 Implement deterministic apex, `www`, tenant subdomain, custom domain, canonical URL, and redirect behavior for IPv4 and IPv6. (FR-030)
- [x] B060 Implement environment-scoped staging certificate request, renewal, expiry, revocation, rollback, and alert states. (FR-026)
- [x] B061 Prove test and preview configurations cannot reach production certificate endpoints or inherit production account material. (FR-026, FR-031, FR-069)
- [x] B062 Add encrypted origin transport plus static and public-media CDN policies with versioned cache keys, invalidation, safe headers, and origin protection. (FR-027, FR-049, FR-073)
- [x] B063 Prove authenticated, signed, private, tenant-specific, and revoked content cannot be cached or disclosed incorrectly. (FR-019, FR-027, FR-065)
- [x] B064 Enforce edge body/header limits, request and upstream timeouts, rate/concurrency limits, trusted proxies, security headers, CORS, cookies, abuse controls, service-network segmentation, and outbound allowlists. (FR-028, FR-074)
- [x] B065 Keep Django admin, pgAdmin, Traefik, metrics, diagnostics, and API schema private by default with explicit role and network gates. (FR-029, FR-045)
- [x] B066 Add domain, DNS, certificate, edge, CDN, and privileged-surface health to native operations. (FR-010, FR-016)
- [x] B067 Test DNS delay, certificate failure, cache poisoning, host confusion, proxy spoofing, rate exhaustion, private-surface bypass, SSRF, metadata access, DNS rebinding, lateral movement, and egress denial. (FR-025 through FR-030, FR-060, FR-065, FR-074)
- [x] B068 Run source-bound browser, redirect, header, cache, accessibility, and staging-certificate acceptance without production issuance. (FR-026, FR-063, FR-064)

## Phase 5 — Secrets, audit, jobs, schedules, email, and notifications

- [x] B069 Write tests first for secret resolution, redaction, rotation, break-glass, audit integrity, job replay, schedule time, and notification delivery. (FR-031 through FR-040, FR-065)
- [x] B070 Inventory each credential class, owner, scope, source, consumer, lifetime, rotation, revocation, and recovery contract without recording values. (FR-031, FR-032)
- [x] B071 Implement JIT secret references and prove values do not enter source, images, environment snapshots, logs, evidence, client bundles, or browser storage. (FR-031, FR-065)
- [x] B072 Implement and drill expiry, rotation, revocation, overlap, consumer restart, and recovery for each credential class. (FR-032, FR-060)
- [x] B073 Implement time-bound break-glass request, use, observation, expiry, revocation, and mandatory follow-up review. (FR-033, FR-034)
- [x] B074 Implement redacted integrity-bound operator and security audit chains with tenant scope, access control, retention, and verified export. (FR-034, FR-071)
- [x] B075 Add the canonical durable job schema with tenant, owner, generation, payload digest/schema, state, attempts, leases, idempotency, and receipts. (FR-035)
- [x] B076 Implement bounded fair discovery, admission, leases, backoff, jitter, idempotent side effects, stale recovery, and duplicate-delivery no-op. (FR-036, FR-042)
- [x] B077 Implement visible dead-letter review, acknowledgement, safe replay, cancellation, and resolution without arbitrary commands. (FR-037, FR-069)
- [x] B078 Implement scheduler state for next/last run, lateness, missed policy, catch-up, timezone, DST, overlap, resource admission, and restart. (FR-038)
- [x] B079 Add job, dead-letter, schedule, delay, saturation, and replay evidence to native operations. (FR-010, FR-016, FR-070)
- [x] B080 Implement production transactional email sender verification, accessible templates, safe expiring links, delivery, bounce, complaint, and suppression handling. (FR-039)
- [x] B081 Implement tenant-aware in-app/email history, preferences, urgency, quiet time, deduplication, unsubscribe, and mandatory-security exceptions. (FR-040)
- [x] B082 Prove email and operator alert providers can fail without losing durable state, leaking content, or reporting false success. (FR-015, FR-039, FR-040, FR-070)
- [x] B083 Run crash, replay, clock/DST, provider-outage, secret-rotation, audit-tamper, accessibility, and tenant-isolation acceptance. (FR-019, FR-032 through FR-040, FR-063 through FR-066)

## Phase 6 — Tenant lifecycle, quotas, identity, policy, and settings

- [x] B084 Write tests first for tenant lifecycle, quota races, recovery, MFA/passkeys, sessions, policy parity, settings scope, and destructive confirmation. (FR-041 through FR-046, FR-063, FR-065)
- [x] B085 Implement provision, configure, suspend, archive, restore, ownership transfer, export, and separately approved deletion state machines. (FR-007, FR-041)
- [x] B086 Make tenant disable and suspension remove serving and allocation authority without silently deleting recoverable data. (FR-041, FR-072)
- [x] B087 Implement atomic per-tenant user, storage, media, API, job, email, search, and cost quotas with reservations and reconciliation. (FR-042)
- [x] B088 Add quota state, forecasts, denial reasons, alerts, and safe operator/user remediation without cross-tenant comparison. (FR-014, FR-042)
- [x] B089 Implement verified identity recovery, optional standards-based MFA, recovery codes, and passkeys with downgrade resistance. (FR-043, FR-065)
- [x] B090 Implement active session/device inventory, remote revocation, rotation, anomaly evidence, and bounded security alerts. (FR-044)
- [x] B091 Define versioned role and policy vocabulary with deny-by-default resolution and consequence classification. (FR-045)
- [x] B092 Enforce policy parity across Django, FastAPI, React affordances, workers, exports, search, media, administration, and operations. (FR-019, FR-045)
- [x] B093 Separate account, tenant, site, module, and operator settings scopes with schema ownership and safe defaults. (FR-046)
- [x] B094 Add searchable accessible settings, unsaved-change protection, optimistic conflict handling, recent-auth gates, consequence copy, sensitive history, and user-versus-site locale/timezone preferences. (FR-046, FR-064, FR-075)
- [x] B095 Prove disabled capabilities and expired feature flags leave no settings, roles, routes, jobs, schedules, allocations, configuration, authority, or navigation residue. (FR-045, FR-046, FR-072, FR-077)
- [x] B096 Run cross-role, cross-tenant, race, recovery, session, browser, accessibility, visual, and lifecycle recovery acceptance. (FR-019, FR-041 through FR-046, FR-063 through FR-066)

## Phase 7 — Search, editorial, media delivery, and website essentials

- [x] B097 Write tests first for authorization-aware indexing, editorial conflicts, object delivery, privacy, SEO, forms, and optional-surface absence. (FR-047 through FR-050, FR-063, FR-065, FR-072)
- [x] B098 Define the optional search manifest, document schema, permission projection, cursor, filters, facets, ranking, limits, and freshness contract. (FR-047, FR-072)
- [x] B099 Implement tenant-scoped indexing and query across authorized content, records, media, members, and enabled modules. (FR-019, FR-047)
- [x] B100 Implement bounded reindex, deletion, permission-change invalidation, outage recovery, consistency checks, and operations signals. (FR-010, FR-047, FR-070)
- [x] B101 Implement editorial draft, revision, schedule, preview, review, publish, archive, conflict, and rollback state machines. (FR-048)
- [x] B102 Add expiring permission-aware preview links and prove they cannot bypass tenant, role, publication, or cache boundaries. (FR-019, FR-027, FR-048, FR-065)
- [x] B103 Integrate production object storage and safe CDN delivery behind the existing Media contracts without weakening quarantine. (FR-027, FR-049)
- [x] B104 Add resumable/multipart upload, lifecycle tiers, reference tracking, and deletion consequences within fixed resource limits. (FR-049, FR-057)
- [x] B105 Build reusable accessible navigation, breadcrumb, header, footer, loading, empty, degraded, denial, and error patterns with translation, pluralization, direction, and fallback contracts. (FR-050, FR-064, FR-075)
- [x] B106 Implement legal/privacy/consent surfaces and consent-aware analytics boundaries with no dark patterns. (FR-050, FR-061)
- [x] B107 Implement locale-aware canonical URLs plus metadata, sitemap, robots, Open Graph, structured data, share, and print contracts. (FR-025, FR-030, FR-050, FR-075)
- [x] B108 Implement accessible forms, validation, spam/abuse controls, rate limits, durable submission receipts, and safe notification linkage. (FR-028, FR-035, FR-039, FR-050)
- [x] B109 Prove search, preview, object, metadata, consent, form, and cache state remain tenant and permission isolated under change and deletion. (FR-019, FR-023, FR-047 through FR-050, FR-065)
- [x] B110 Run content-scale load, browser, accessibility, visual, SEO contract, privacy, security, restore, and disabled-profile acceptance. (FR-022, FR-057, FR-063 through FR-066, FR-072)

## Phase 8 — Visual builder, themes, archetypes, modules, integrations, and commerce

- [x] B111 Write tests first for constrained composition, token validity, upgrades, module graphs, webhooks, key scope, and commerce replay. (FR-051 through FR-056, FR-063, FR-065)
- [x] B112 Define a closed accessible component and layout schema with bounded nesting, responsive constraints, and no executable markup/style path. (FR-051, FR-065)
- [x] B113 Implement deterministic page composition, preview, validation, publication, version history, and rollback through the content workflow. (FR-048, FR-051)
- [x] B114 Define versioned semantic design tokens for color, typography, spacing, layout, elevation, motion, and interaction states. (FR-052)
- [x] B115 Implement theme inheritance, compatibility, migration, preview, accessibility validation, upgrade, and rollback. (FR-052, FR-064)
- [x] B116 Specify and generate business, portfolio, documentation, publication, community, directory, event, booking, catalog, marketplace, subscription, support, and nonprofit archetypes. (FR-053)
- [x] B117 Bind each archetype to exact modules, routes, roles, data, journeys, visual profiles, capacity assumptions, and estimated provider cost. (FR-053, FR-058)
- [x] B118 Extend module manifests with dependencies, conflicts, compatibility, migrations, permissions, routes, jobs, schedules, storage, observability, backup, resources, and test packs. (FR-054)
- [x] B119 Implement deterministic module enable, disable, upgrade, downgrade, and data-preserving uninstall plans with exact rollback. (FR-054, FR-066, FR-072)
- [x] B120 Build a private module catalog and reject unsigned, incompatible, over-authorized, or undeclared third-party extensions. (FR-054, FR-059, FR-065)
- [x] B121 Implement scoped expiring API keys and OAuth integrations with rotation, quotas, audit, and revocation. (FR-031, FR-032, FR-055)
- [x] B122 Implement signed replay-safe webhooks with delivery history, bounded retry, dead letters, endpoint verification, and secret rotation. (FR-035 through FR-037, FR-055)
- [x] B123 Build a versioned developer API and webhook portal with compatibility, deprecation, consumer-contract evidence, synthetic test identities, and no production secrets. (FR-055, FR-062, FR-076)
- [x] B124 Define commerce as a disabled-by-default module with provider abstraction, prohibited-data boundaries, and explicit activation approval. (FR-007, FR-056, FR-069, FR-072)
- [x] B125 Implement idempotent product, price, order, subscription, invoice, tax, refund, and reconciliation state contracts using a fake provider first. (FR-036, FR-056)
- [x] B126 Prove provider webhook forgery, replay, reordering, duplication, outage, refund race, and cross-tenant access fail safely. (FR-019, FR-055, FR-056, FR-065)
- [x] B127 Run generator determinism, archetype, module lifecycle, accessibility, visual, integration, commerce, security, and rollback acceptance. (FR-051 through FR-056, FR-063 through FR-066)

## Phase 9 — Performance, supply chain, resilience, governance, and golden paths

- [x] B128 Write tests first for performance budgets, scaling transitions, cost ceilings, artifact policy, faults, privacy controls, and shell parity. (FR-057 through FR-062, FR-063)
- [x] B129 Establish representative small, medium, and large tenant datasets and public, member, editor, operator, and background load models. (FR-057)
- [x] B130 Enforce budgets for web vitals, frontend bundles, API latency, queries, pool use, worker throughput, CPU, memory, storage, and telemetry overhead. (FR-057)
- [x] B131 Add cache policy and invalidation proof, N+1/slow-query detection, compression, code splitting, responsive media, and graceful degradation. (FR-027, FR-057)
- [x] B132 Define vertical/horizontal scaling triggers, queue and database pressure responses, safe degradation, and scale-down behavior. (FR-013, FR-058)
- [x] B133 Calculate provider resources, maximum runtime, region, cost ceiling, teardown deadline, and cleanup ownership before any provider-backed run. (FR-007, FR-058, FR-069)
- [x] B134 Implement automatic ephemeral expiry and exact verified teardown with no authority to delete unowned or production resources. (FR-058, FR-069)
- [x] B135 Pin build and runtime dependencies and images and enforce protected-branch, required-check, code-owner, least-workflow-permission, dependency-update, immutable-action, license, vulnerability, secret, SBOM, signature, and provenance policies. (FR-059, FR-078)
- [x] B136 Add bounded fault drills for application, worker, queue, database, object storage, search, DNS, certificates, email, alerting, and provider responses. (FR-060)
- [x] B137 Measure recovery objectives, detect incomplete recovery, and link every drill to incident and residual-risk evidence. (FR-013, FR-014, FR-060, FR-068)
- [x] B138 Build the documented inventory for data classes, purposes, consent, retention, vendors, regions, accessibility, incidents, and user rights without unsupported certification claims. (FR-023, FR-061, FR-068)
- [x] B139 Implement one Bash and one PowerShell golden path for setup, generate, migrate, test, preview, release, recover, and rollback without cross-shell calls. (FR-062)
- [x] B140 Prove fresh-machine and recovered-WSL operation with documented prerequisites, deterministic seed data, clear errors, and no hidden state. (FR-062, FR-070)

## Phase 10 — Integrated assurance, staged acceptance, and closeout

- [x] B141 Build the complete test matrix mapping every requirement to unit, integration, contract, migration, API, frontend, E2E, negative, and operational proof. (FR-063)
- [x] B142 Capture and review exact-source keyboard, screen-reader, zoom, motion, contrast, RTL, locale, timezone, translation-fallback, responsive, cross-browser, interaction, and visual evidence for every user-facing state. (FR-012, FR-064, FR-075)
- [x] B143 Run authorization, tenant escape, hostile input, SSRF, metadata, DNS-rebinding, egress, injection, replay, race, exhaustion, encryption/key-rotation, supply-chain, workflow-policy, and secret-leak suites. (FR-019, FR-031, FR-059, FR-065, FR-073, FR-074, FR-078)
- [x] B144 Run forward migration, compatibility window, backup, isolated restore, code rollback, interrupted operation, and disaster recovery proof. (FR-018, FR-020 through FR-023, FR-060, FR-066)
- [x] B145 Run complete local and CI gates twice at the exact clean candidate head, verify repository/workflow governance, and repeat critical state-machine and isolation suites. (FR-063, FR-065, FR-068, FR-078)
- [ ] B146 Obtain fresh independent code, security, UX/accessibility, data, and operations reviews and close every critical, high, and medium finding. (FR-063 through FR-068)
- [ ] B147 Review the exact diff, generated surface, dependencies, migrations, residual risks, evidence inventory, and absence of secret or provider state. (FR-008, FR-059, FR-068, FR-069)
- [ ] B148 Obtain separate exact-head approval before publication and create only the approved draft pull request. (FR-007, FR-069)
- [ ] B149 Require all hosted checks and exact-head review before requesting a separately approved merge. (FR-003, FR-007, FR-063)
- [ ] B150 Obtain separate provider approval for a bounded production-like ephemeral canary with staging certificates and synthetic data. (FR-007, FR-026, FR-058, FR-067, FR-069)
- [ ] B151 Run the exact-source ephemeral canary, synthetic journeys, visual matrix, performance budgets, security probes, backup, restore, and rollback. (FR-005, FR-011, FR-012, FR-057, FR-063 through FR-067)
- [ ] B152 Destroy only the exact approved ephemeral resources and prove empty provider inventory, cost receipt, and terminal evidence. (FR-008, FR-058, FR-067, FR-069)
- [ ] B153 Re-run the tasks-to-analysis cycle against canary findings and add, implement, and verify every newly required task before closeout. (FR-063, FR-068, FR-070)
- [ ] B154 Produce the production activation runbook, explicit remaining approvals, rollback point, recovery contacts, and honest residual-risk statement. (FR-006, FR-007, FR-060, FR-068, FR-069)
- [ ] B155 Validate disabled optional modules have no routes, navigation, jobs, schedules, allocation, credentials, or provider residue in every profile. (FR-010, FR-054, FR-072)
- [ ] B156 Validate monitoring, incident, audit, backup, restore, and alert evidence is tenant-safe, redacted, integrity-bound, fresh, and retention-bounded. (FR-008, FR-014 through FR-016, FR-020, FR-022, FR-034, FR-071)
- [ ] B157 Validate documentation, configuration references, API schemas, compatibility/deprecation guidance, localization behavior, migration guidance, operator procedures, and generated-site instructions match exact behavior. (FR-002, FR-046, FR-055, FR-061, FR-062, FR-075, FR-076)
- [ ] B158 Mark no task complete from elapsed time alone and report all pending external, provider, approval, and real-time evidence honestly. (FR-068, FR-069, FR-070)
- [ ] B159 Remove Feature 106 from active lifecycle authority only after all required tasks and exact evidence are complete. (FR-007, FR-008, FR-068)
- [ ] B160 Treat actual production activation as a new exact-source, exact-environment, separately approved operation outside implicit feature authority. (FR-007, FR-067, FR-069)

## Phase 11 — Exact-head independent-review corrections

- [ ] B161 Prove release health evidence is causally ordered around each traffic mutation with distinct pre-change and post-change observations plus a post-switch synthetic journey. (FR-005, FR-063, FR-068)
- [ ] B162 Enforce one least-privilege Celery database identity, remove broader request-runtime credentials from workers, and prove every asynchronous task retains only its declared table operations. (FR-019, FR-031, FR-065, FR-073)
- [ ] B163 Implement a production-capable email adapter, durable outbox replay schedule, failure visibility, and bounded retry/dead-letter behavior without silently stranded verification or reset mail. (FR-014, FR-036, FR-038, FR-071)
- [ ] B164 Bound monitoring fan-out by queue capacity and evidence freshness, deduplicate outstanding collections, and prove the maximum supported tenant batch cannot create unbounded stale work. (FR-013, FR-014, FR-036, FR-057)
- [ ] B165 Repair durable scheduling with ISO-safe idempotency, exact atomic capacity admission, timezone and DST-aware rules, missed-run and overlap policy, and bounded deterministic-testable retry jitter. (FR-036, FR-038, FR-057, FR-063)
- [ ] B166 Renew long-running job leases against database time, reject stale settlement, and prove reclaim, overlap, crash, and retry behavior under work exceeding one lease interval. (FR-036, FR-060, FR-065)
- [ ] B167 Normalize every legacy row accepted by the previous scheduler before new constraints and prove the declared mixed-version migration window with old-writer/new-schema and new-reader/old-schema coverage. (FR-018, FR-066)
- [ ] B168 Connect tenant provision, configure, suspend, archive, restore, transfer, export, and delete to one durable transactional state machine with atomic one-time destructive approval consumption and recovery receipts. (FR-008, FR-019, FR-023, FR-031, FR-045)
- [ ] B169 Connect encrypted production backup, retention rotation, inventory, point-in-time recovery, isolated restore, object/search/audit reconciliation, monitoring, and scheduling to real operator entrypoints while retaining hermetic adapters for tests. (FR-020 through FR-023, FR-038, FR-060, FR-066)
- [ ] B170 Pin validated object-storage addresses through the actual TLS connection, preserve hostname certificate verification, reject DNS rebinding, and integrate the adapter into tenant media delivery. (FR-025, FR-026, FR-065)
- [ ] B171 Implement automatic exact-owned ephemeral expiry with durable creation and deadline evidence, a bounded production entrypoint, replay safety, and verified terminal inventory. (FR-008, FR-058, FR-069)
- [ ] B172 Localize the complete supported Arabic and RTL journey including shell, settings, operations labels, dynamic states, severities, and fallbacks; regenerate exact-source baselines and review manifests. (FR-012, FR-046, FR-064, FR-075)
- [ ] B173 Make summary and incident freshness independent and visible, and require explicit accessible confirmation and consequence copy for dead-letter cancellation. (FR-012, FR-014, FR-064)
- [ ] B174 Extend keyboard order/action/return-focus, touch target/tap, computed reduced-motion, degraded, recent-auth, read-only, cross-browser, zoom, and assistive-technology evidence without overstating finite automation. (FR-012, FR-064, FR-068)
- [ ] B175 Re-run complete gates twice at the new exact clean head, repeat critical state-machine/isolation suites, and bind every local and hosted evidence claim to that exact commit rather than an ancestor. (FR-063, FR-065, FR-068, FR-078)
- [ ] B176 Repeat fresh independent code, security, UX/accessibility, data, and operations review at the repaired exact head and iterate until no critical, high, or medium finding remains. (FR-063 through FR-068)

## Phase 12 — Exact-head review cycle 11 corrections

- [ ] B177 Connect durable tenant lifecycle state to request serving, allocation, session/job revocation, and honest deletion orchestration; never claim recoverable data is gone until every declared data surface has terminal evidence. (FR-008, FR-019, FR-023, FR-045, FR-068)
- [ ] B178 Revoke every historical cross-tenant worker policy/grant, compartmentalize worker queues and secret sets by duty, and prove each worker identity can access only its declared tenant-scoped or narrowly global tables. (FR-019, FR-031, FR-065, FR-073)
- [ ] B179 Wire one storage-backend factory and the complete pinned-S3 configuration/secret mounts into API and every background content/media path, with identical local and S3 behavior and honest readiness probes. (FR-025 through FR-027, FR-049, FR-065)
- [ ] B180 Require a production-capable email adapter at production startup, make disabled delivery retryable rather than terminal for required authentication mail, and add real bounded delivery-readiness evidence. (FR-014, FR-036, FR-038, FR-071)
- [ ] B181 Make lifecycle replay exact and reachable before transition validation; bind revision, configuration, target owner, and receipt digest, and implement accepted tenant-member ownership transfer without typo lockout. (FR-019, FR-031, FR-045, FR-065)
- [ ] B182 Prove monitoring capacity can meet every freshness SLA at the admitted tenant ceiling, enforce queue-depth admission and per-tenant freshness, and reject configurations that exceed the declared worker/probe budget. (FR-013, FR-014, FR-036, FR-057)
- [ ] B183 Snapshot object bytes exactly once into a stable backup staging boundary, hash the staged bytes, archive only that snapshot, and clean it on success and every failure. (FR-020 through FR-023, FR-060, FR-066)
- [ ] B184 Fence each email claim with an opaque lease token and deterministic Message-ID/provider idempotency key so stale workers cannot overwrite newer attempts and SMTP crash recovery is explicit. (FR-036, FR-038, FR-060, FR-065)
- [ ] B185 Align production backup/restore receipt names, kinds, schedules, and maximum ages with operations consumers so valid daily evidence remains fresh without false green status. (FR-014, FR-020 through FR-022, FR-068)
- [ ] B186 Repair database-plus-object recovery acceptance to require and verify every expected payload member instead of contradicting the generated archive. (FR-020 through FR-023, FR-060, FR-066)
- [ ] B187 Extend compatibility evidence through schema 29 and make backup/restore verify the live migration ledger rather than trusting a configured schema label. (FR-018, FR-020, FR-066)
- [ ] B188 Move durable schedule claims to database time, renew long-running job leases continuously with fencing, and prove skew, overlap, reclaim, and stale settlement behavior. (FR-036, FR-038, FR-060, FR-065)
- [ ] B189 Unify database saturation admission and telemetry thresholds and return reset connections to the current pool rather than a replaced pool. (FR-013, FR-014, FR-057)
- [ ] B190 Quarantine and report invalid backup receipts and exact-owned orphan archives, then apply bounded retention without deleting unknown or unowned files. (FR-008, FR-020, FR-022, FR-071)
- [ ] B191 Localize all visible and accessible Operations, Settings, navigation, theme, feedback, notification, privacy, and destructive-action copy for English, German, and Arabic. (FR-012, FR-046, FR-064, FR-075)
- [ ] B192 Preserve exactly one page-level heading while retaining localized shell context and deterministic screen-reader navigation on every authenticated route. (FR-012, FR-050, FR-064)
- [ ] B193 Bind visual assurance to an exact successful runner receipt, exercise German plus Arabic/RTL, and cover degraded, stale, reauthentication, and read-only states across reflow/mobile and supported browser engines without overstating finite automation. (FR-012, FR-063, FR-064, FR-068, FR-075)
- [ ] B194 Re-run critical suites, complete gates twice, fresh exact-head C/H/M reviews, diff/secret/provider-state checks, and iterate again until no critical, high, or medium finding remains. (FR-063, FR-065, FR-068, FR-069, FR-078)

## Phase 13 — Complete-gate-discovered corrections

- [ ] B195 Bind the operations visual contract to all 35 exact-source captures and reject stale count expectations. (FR-063, FR-064, FR-068)
- [ ] B196 Return and test localized notification completion feedback independently from the initiating button label. (FR-012, FR-046, FR-064, FR-075)
- [ ] B197 Repair lifecycle backfill against the real membership schema and prove it in disposable PostgreSQL migration acceptance. (FR-018, FR-045, FR-066)
- [ ] B198 Separate request, content, runtime, and email database identities across bootstrap, migration, setup, Compose, and E2E surfaces with independent credentials and least-privilege grants. (FR-019, FR-031, FR-065, FR-073)
- [ ] B199 Prove content discovery plus tenant-fenced mutation, runtime operation/quota/job access, email outbox select/update, and cross-duty denial through real PostgreSQL forward, rollback, and reapply checks. (FR-019, FR-036, FR-060, FR-065, FR-073)
- [ ] B200 Align the migration compatibility catalog and contract with schema 29 and classify the permission-only transition without a false destructive claim. (FR-018, FR-066, FR-068)
- [ ] B201 Restore the fixed 90% changed-line floor with focused private SMTP configuration and fenced outbox-claim coverage. (FR-038, FR-063, FR-065, FR-071)

## Phase 14 — Exact-head review cycle 15 corrections

- [ ] B202 Localize embedded and standalone account security, notification delivery labels, shell/sidebar context, and every rendered Operations enum; apply saved locale and RTL direction immediately and prove the behavior in component tests. (FR-012, FR-046, FR-064, FR-075)
- [ ] B203 Pass explicit environment and verified-database-TLS settings to every Python process, start and observe all three Celery worker queues, and mount SMTP credentials only into the email worker. (FR-013, FR-014, FR-031, FR-038, FR-062, FR-073)
- [ ] B204 Repair content-worker grants and historical RLS so global discovery remains possible but every mutation is tenant-fenced; prove data-rights access and cross-tenant insert, update, and delete denial against disposable PostgreSQL. (FR-018, FR-019, FR-023, FR-065, FR-073)
- [ ] B205 Gate production requests and asynchronous work on durable active lifecycle state, revoke queued jobs, schedules, and sessions when serving stops, repair legacy ownership, atomically transfer authorization ownership, and refuse terminal deletion without reconciled per-surface evidence. (FR-008, FR-019, FR-023, FR-031, FR-045, FR-068)
- [ ] B206 Make S3 writes immutable and replay-safe, bind reads and deletes to an exact object version, use real storage readiness, and fail production startup closed until S3 backup/restore is supported. (FR-020 through FR-027, FR-049, FR-060, FR-065, FR-066)
- [ ] B207 Validate every registered Celery task has one fixed queue, emit per-role worker heartbeats, observe all queue depths and liveness, deduplicate fan-out, enforce admitted capacity, and run bounded probes concurrently inside the declared freshness ceiling. (FR-013, FR-014, FR-036, FR-057, FR-063)
- [ ] B208 Split email fencing into expand/backfill/contract phases, make contract replay interruption-safe, reject stale settlement, quarantine uncertain expired claims, and retain deterministic provider idempotency identity. (FR-018, FR-036, FR-038, FR-060, FR-065, FR-066, FR-071)
- [ ] B209 Snapshot local object bytes exactly once before archival, compare the database object-reference ledger around the snapshot, remove failed output, and bound invalid-receipt/orphan quarantine without deleting excess unknown files. (FR-008, FR-020 through FR-023, FR-060, FR-066, FR-071)
- [ ] B210 Require the exact latest Django and API migration ledgers for readiness and recovery evidence, remove duplicate environment configuration, and keep preview canaries honest about synthetic mail, internal database TLS, and staging certificates. (FR-002, FR-014, FR-018, FR-038, FR-062, FR-068)
- [ ] B211 Add and pass focused regression coverage for every cycle-15 correction, rerun disposable PostgreSQL forward acceptance, lint/type/Compose validation, and restore the fixed changed-line coverage floor. (FR-063, FR-065, FR-066, FR-068, FR-078)
- [ ] B212 Commit one clean repaired candidate and pass the complete local gate twice at that identical exact head; treat all ancestor and failed-candidate evidence as historical only. (FR-063, FR-065, FR-068, FR-078)
- [ ] B213 Repeat fresh independent UX/accessibility, data, and code/security/operations reviews and iterate again until critical, high, and medium findings are all zero before requesting exact-head publication approval. (FR-063 through FR-069, FR-078)
- [ ] B214 Replace the formatting-sensitive readiness-query assertion exposed by the broad API suite with normalized SQL-shape and exact latest-ledger checks, then rerun the complete API suite. (FR-018, FR-063, FR-068)
- [ ] B215 Complete the pinned S3 protocol implementation with typed bucket readiness, conditional immutable writes, exact version receipts, and version-bound reads and deletes. (FR-025, FR-026, FR-049, FR-060, FR-065)
- [ ] B216 Regenerate and validate the exact surface-drift inventory after reviewed configuration and route changes. (FR-002, FR-055, FR-061, FR-063, FR-068)
- [ ] B217 Re-run the complete Operations visual matrix after localization changes and bind its generated captures, runner receipt, and evidence manifest to the repaired exact sources. (FR-012, FR-063, FR-064, FR-068, FR-075)
- [ ] B218 Update the account browser contract to the localized human-readable notification accessible name and rerun the complete account/admin journey. (FR-012, FR-046, FR-063, FR-064, FR-075)
- [ ] B219 Restore the fixed 90% changed-line floor with direct failure-path coverage for bounded internal probes, worker and queue evidence, closed task routing, lifecycle admission, dispatch reservations, and enqueue cleanup. (FR-013, FR-014, FR-031, FR-057, FR-063, FR-065, FR-068)

## Phase 15 — Exact-head review cycle 17 corrections

- [ ] B220 Supply deterministic delivery keys on every email insert, prove creation through the real migrated schema, and stage rollout so old writers cannot race the contract migration. (FR-018, FR-036, FR-038, FR-060, FR-065, FR-066)
- [ ] B221 Give data-rights claims fenced expiring leases, reclaim/quarantine and retention behavior, and crash-safe side-effect/completion/audit reconciliation with fault drills. (FR-019, FR-023, FR-036, FR-060, FR-065)
- [ ] B222 Split data-rights into its own queue, database role, and secret set; revoke global identity DML from content workers and expose only tenant/subject-fenced operations with PostgreSQL denial proof. (FR-019, FR-031, FR-065, FR-073)
- [ ] B223 Reconcile every database object reference to exact captured bytes and digest at backup and restored-database acceptance, including negative missing, wrong, and mixed-snapshot drills. (FR-020 through FR-023, FR-060, FR-066)
- [ ] B224 Prevent tenant suspension from revoking user-global sessions for other active tenants and prove multi-tenant session behavior. (FR-019, FR-031, FR-045, FR-065)
- [ ] B225 Produce privacy exports from one repeatable-read snapshot or equivalent fenced cut and prove concurrent correction/deletion cannot yield mixed-time output. (FR-019, FR-023, FR-060, FR-065)
- [ ] B226 Make migration 0030 rollback exact or explicitly irreversible with rollback tooling that refuses to cross it, plus forward/backward ledger proof. (FR-018, FR-060, FR-066, FR-068)
- [ ] B227 Serialize API migration runners with a PostgreSQL advisory lock and prove two concurrent runners converge without duplicate DDL or ledger races. (FR-018, FR-060, FR-065, FR-066)
- [ ] B228 Make production database hosting/TLS configuration internally consistent and prove a verified TLS handshake rather than claiming verify-full against bundled non-TLS PostgreSQL. (FR-025, FR-026, FR-031, FR-062, FR-065)
- [ ] B229 Connect ephemeral expiry to durable plan persistence, bounded scanner/CLI/service scheduling, exact-owned provider adapters, replay safety, and terminal inventory evidence. (FR-008, FR-058, FR-060, FR-067, FR-069)
- [ ] B230 Remove deployment error suppression, add role/queue-aware worker healthchecks, fail hard on timeout, and prove deployment cannot continue without every required worker. (FR-013, FR-014, FR-060, FR-063, FR-068)
- [ ] B231 Make monitoring fan-out capacity reservation atomic across collection and alert producers, release reservations on every outcome, and prove concurrent ticks cannot exceed the queue ceiling. (FR-013, FR-014, FR-036, FR-057, FR-065)
- [ ] B232 Render passkey enrollment explicitly unavailable until a complete bounded enrollment/recovery implementation exists and test both capability states. (FR-012, FR-031, FR-064, FR-068)
- [ ] B233 Render AppShell sidebar items as typed navigation controls, bind the mobile controlled id and localized label, close and restore focus on activation, and test keyboard/touch behavior. (FR-012, FR-050, FR-064, FR-075)
- [ ] B234 Use post-save locale copy immediately and map settings failures to localized safe messages without leaking English service fallbacks; prove German and Arabic success/failure states. (FR-012, FR-046, FR-064, FR-075)
- [ ] B235 Translate every Operations model enum including running and enforce table-driven model-to-locale coverage. (FR-012, FR-046, FR-064, FR-075)
- [ ] B236 Make visual runner receipts distinguish skipped/no-assertion cases and bind assertion/capture identifiers to the intended matrix. (FR-012, FR-063, FR-064, FR-068)
- [ ] B237 Disable production API docs and OpenAPI aliases by default with one consistent authenticated/configured exposure policy and matching documentation. (FR-002, FR-031, FR-055, FR-068)
- [ ] B238 Re-run focused PostgreSQL, backup/restore, fault, deployment, capacity, frontend, visual, and security suites for every cycle-17 correction. (FR-063 through FR-068, FR-078)
- [ ] B239 Commit a new clean exact head, restart and pass two complete gates, repeat critical suites, and obtain fresh independent reviews with C/H/M all zero. (FR-063 through FR-069, FR-078)

## Phase 16 — Integration-discovered corrections

- [ ] B240 Carry the dedicated data-rights database role and generated acceptance credential through every disposable PostgreSQL bootstrap and migration command, then prove the complete forward, reverse, concurrency, and role-isolation acceptance succeeds. (FR-018, FR-019, FR-031, FR-060, FR-065, FR-066, FR-073)
- [ ] B241 Preserve functional navigation for legacy string sidebar inputs while retaining typed route controls, one consistent accessible name, mobile close/focus return, and complete frontend compatibility coverage. (FR-012, FR-050, FR-063, FR-064, FR-075)
- [ ] B242 Regenerate Operations screenshots, exact runner evidence, and surface-drift inventory from the final integrated sources, and execute framework-specific suites in their correct isolated environments. (FR-012, FR-018, FR-063, FR-064, FR-068, FR-075, FR-078)

## Phase 17 — Complete-gate cycle 19 corrections

- [ ] B243 Freeze the authentication rate-limit regression inside one deterministic fixed window so an actual wall-clock minute rollover cannot reset its bucket and create a false gate failure. (FR-031, FR-057, FR-060, FR-063, FR-065)
- [ ] B244 Run pre-commit source normalization before final browser capture and evidence generation, then bind the committed visual manifest to those exact normalized sources. (FR-012, FR-063, FR-064, FR-068, FR-075, FR-078)

## Phase 18 — Exact-head review cycle 20 corrections

- [ ] B245 Replace direct data-rights identity and operation-table DML with fixed security-definer claim, read, mutate, and settle procedures bound to one operation, tenant, subject, and lease token; prove the credential cannot enumerate operations or self-select another tenant. (FR-019, FR-023, FR-031, FR-060, FR-065, FR-073)
- [ ] B246 Separate tenant-scoped privacy closure from account-wide closure, preserve global identity and other-tenant sessions/memberships for tenant-only requests, and require separately explicit reconciled authority for global account destruction. (FR-019, FR-023, FR-031, FR-045, FR-060, FR-065)
- [ ] B247 Export one PostgreSQL repeatable-read snapshot for both the object-reference ledger and pg_dump, fence the ending ledger, and reject true ABA and concurrent mixed-snapshot backup drills. (FR-020 through FR-023, FR-060, FR-065, FR-066)
- [ ] B248 Define a versioned subject-data inventory covering every direct requester, owner, actor, membership, content, media, scheduling, approval, and audit reference; make export/erasure completeness fail closed and prove every registered surface. (FR-019, FR-023, FR-060, FR-065, FR-068)
- [ ] B249 Make the mobile application drawer a complete accessible modal interaction with contained tab order, inert/background isolation, Escape close, activation close, and deterministic focus return. (FR-012, FR-050, FR-063, FR-064)
- [ ] B250 Bind each visual receipt row to an actually observed current-run screenshot attachment and include every rendered shell, navigation, theme, and styling source in invalidation; prove stale or synthesized captures are rejected. (FR-012, FR-063, FR-064, FR-068, FR-075)
- [ ] B251 Expose current-route orientation through localized visible state and `aria-current` without breaking legacy or typed sidebar inputs. (FR-012, FR-046, FR-050, FR-064, FR-075)
- [ ] B252 Generate and test the data-rights worker secret in every canary and full-preview environment rather than permitting fixture fallback. (FR-031, FR-062, FR-065, FR-073)
- [ ] B253 Require Django and every production database client to mount the CA and use hostname-verifying TLS against the external database; reject missing, bundled, loopback, and unverifiable production topology. (FR-025, FR-026, FR-031, FR-062, FR-065)
- [ ] B254 Fail deployment when the provider result lacks a resolved target address and prohibit success until all mandatory remote verification completes. (FR-005, FR-060, FR-063, FR-068)
- [ ] B255 Remove remote source-sync error suppression, bind deployment to one expected commit, verify the checked-out commit before build and after health checks, and reject healthy stale code. (FR-005, FR-060, FR-063, FR-065, FR-068)
- [ ] B256 Implement generic ephemeral expiry through durable exact-owned plan persistence, bounded scan/CLI/service/timer scheduling, replay-safe provider adapters, and terminal inventory receipts. (FR-008, FR-058, FR-060, FR-067, FR-069)
- [ ] B257 Make rollback Git and Compose restoration fail hard with explicit partial-rollback evidence; never print or return completion after a suppressed restoration error. (FR-005, FR-060, FR-063, FR-068)
- [ ] B258 Apply one production API-documentation policy to docs, schema aliases, and Traefik exposure, default closed and authenticated when explicitly enabled. (FR-002, FR-031, FR-055, FR-068)
- [ ] B259 Prove Celery Beat is actively scheduling through a fresh heartbeat rather than broker connectivity alone, and block deployment on stale or absent scheduler evidence. (FR-013, FR-014, FR-036, FR-060, FR-063)
- [ ] B260 Remove bundled PostgreSQL startup/dependencies from the external production topology while retaining explicit local, E2E, and development profiles. (FR-013, FR-031, FR-057, FR-062)
- [ ] B261 Add focused hostile and failure-path tests for every cycle-20 correction, rerun real PostgreSQL, backup/restore, frontend, browser, Compose, deployment, security, and exact-source evidence checks. (FR-060, FR-063 through FR-068, FR-078)
- [ ] B262 Create a new clean exact head, restart two complete gates and ten critical repetitions, then repeat independent UX, data, and operations review until all C/H/M totals are zero. (FR-063 through FR-069, FR-078)
- [ ] B263 Close the data-rights acceptance defects with non-disclosing claim guards, exact expired-claim renewal, fixed terminal settlement, claim-context propagation, and a complete real-PostgreSQL proof of tenant and operation isolation. (FR-019, FR-023, FR-031, FR-060, FR-065, FR-073)
- [ ] B264 Bind the production database dump and immutable-object ledger to one exported repeatable-read snapshot and prove that concurrent and ABA changes fail closed. (FR-020 through FR-023, FR-060, FR-065, FR-066)
- [ ] B265 Version and verify the complete subject-data inventory, including media grants, audit subjects, reporters, reviewers, and appellants, without weakening global-identity preservation. (FR-019, FR-023, FR-060, FR-065, FR-068)
- [ ] B266 Deploy a durable bounded generic-expiry registry, scanner, CLI, hardened timer, replay-safe receipt, and one fixed exact-owned DigitalOcean adapter with no arbitrary-command surface. (FR-008, FR-058, FR-060, FR-067, FR-069)
- [ ] B267 Prove the production deployment excludes bundled PostgreSQL while local profiles retain it, and prove rollback cannot claim success after Git, Compose, or exact-head restoration failure. (FR-005, FR-013, FR-031, FR-057, FR-060, FR-062, FR-063, FR-068)
- [ ] B268 Replace browser network-idle assumptions with explicit user-visible readiness assertions and rerun the complete Chromium, Firefox, WebKit, localization, responsive, and accessibility visual matrix. (FR-012, FR-050, FR-060, FR-063, FR-064, FR-075)
- [ ] B269 Normalize all integrated sources, regenerate current-run visual and surface evidence, pass focused and complete gates on one exact head, and repeat independent reviews until all release-blocking totals are zero. (FR-060, FR-063 through FR-069, FR-075, FR-078)
- [ ] B270 Replace the lint-rejected nested data-rights claim contexts with one structurally checked context boundary and rerun the API lint gate. (FR-019, FR-031, FR-060, FR-063, FR-065)
- [ ] B271 Exercise the empty drawer, panel-origin reverse tab, non-wrapping forward tab, legacy workspace mapping, and fallback mapping branches until the unchanged critical-glass 100/99/100/100 coverage floor passes. (FR-012, FR-050, FR-060, FR-063, FR-064, FR-075, FR-078)
- [ ] B272 Normalize full-page visual captures to scroll position zero before comparison, regenerate affected exact-source baselines, and prove an immediate no-update rerun is stable across the supported browser matrix. (FR-012, FR-060, FR-063, FR-064, FR-068, FR-075, FR-078)
- [ ] B273 Make legacy Content Workspace sidebar links switch the real hash-addressed tab and expose `aria-current` on exactly one full path-plus-hash destination, including back/forward-safe routing. (FR-012, FR-046, FR-050, FR-060, FR-063, FR-064, FR-075)
- [ ] B274 Remove the unwrapped router-update warning from keyboard navigation evidence and retain clean deterministic focus/activation assertions. (FR-012, FR-050, FR-060, FR-063, FR-064, FR-078)
- [ ] B275 Revoke direct data-rights identity, workspace, and operation-table DML and expose only fixed claim/read/mutate/settle security-definer procedures bound to one operation, tenant, subject, token, and unexpired lease; deny same-tenant unrelated-row mutation and expired settlement. (FR-019, FR-023, FR-031, FR-060, FR-065, FR-073)
- [ ] B276 Make tenant-only closure consult other active memberships through one narrowly scoped fixed procedure and prove in real two-tenant PostgreSQL that global identity and sessions survive until separately authorized global closure. (FR-019, FR-023, FR-031, FR-045, FR-060, FR-065)
- [ ] B277 Route durable queued-operation discovery through a fixed dispatcher procedure and hand off only exact IDs to the data-rights worker so failed initial dispatch cannot strand work. (FR-013, FR-019, FR-031, FR-036, FR-060, FR-065, FR-073)
- [ ] B278 Replace the identifier-only subject index with versioned value-level projections and treatments for every registered subject-bearing identity, credential, audit, workspace, media, abuse, scheduling, approval, and operations field; add schema-introspection drift and value-level export/erasure proof. (FR-019, FR-023, FR-060, FR-065, FR-068)
- [ ] B279 Add an independent post-capture live-ledger fence outside the exported snapshot and a disposable PostgreSQL concurrency/ABA test while retaining the single snapshot shared by the reference ledger and pg_dump. (FR-020 through FR-023, FR-060, FR-065, FR-066)
- [ ] B280 Give the generic-expiry systemd unit a stable verified checkout working directory and interpreter, and prove it starts from a normal systemd root directory. (FR-008, FR-013, FR-058, FR-060, FR-063, FR-069)
- [ ] B281 Enforce generic-expiry capacity at registration and isolate malformed-plan and adapter failures into durable per-plan receipts while continuing unrelated valid due plans. (FR-008, FR-014, FR-036, FR-058, FR-060, FR-067, FR-069, FR-071)
- [ ] B282 Check rollback SSH native exit status, emit local partial-rollback evidence, recollect the remote failure marker, and ensure no caller suppresses rollback failure. (FR-005, FR-014, FR-060, FR-063, FR-068, FR-071)
- [ ] B283 Make the documented expected-commit environment format parse to one exact 40-character hash, including safe inline-comment handling or comment-free examples, and add a runtime fixture. (FR-005, FR-060, FR-061, FR-062, FR-063, FR-068)
- [ ] B284 Remove every implicit bundled-PostgreSQL dependency and readiness assertion from production worker startup while preserving explicit development, local, and E2E database profiles. (FR-013, FR-031, FR-057, FR-060, FR-062, FR-063)
- [ ] B285 Replace the invalid psycopg `servicefile` keyword with a private bounded allowlisted service-file parser, then prove the independent live-ledger connection observes a real concurrent PostgreSQL commit. (FR-020 through FR-023, FR-031, FR-060, FR-065, FR-066)
- [ ] B286 Resolve the newly disclosed `js-yaml` CPU-exhaustion advisory through an exact lockfile-only transitive update, then require a clean production audit before restarting exact-head gates. (FR-031, FR-060, FR-063, FR-065, FR-066)
- [ ] B287 Bound the mobile command-menu visual assertion to a two-pixel raster tolerance, retain structural and interaction assertions, and prove repeated captures still reject material drift without a one-pixel GPU flake. (FR-012, FR-060, FR-063, FR-064, FR-068, FR-075, FR-078)
- [ ] B288 Keep production environment backups outside every collected evidence root with restrictive permissions and guaranteed cleanup, prohibit interpolated Compose output, and recursively prove retained deployment artifacts contain no secret canaries. (FR-005, FR-031, FR-060, FR-063, FR-065, FR-068, FR-071)
- [ ] B289 Replace disabled SSH host verification with an exact trusted provisioned host-key pin for every command and secret transfer, and fail before credential access on missing or changed identity. (FR-005, FR-031, FR-060, FR-063, FR-065, FR-069)
- [ ] B290 Remove database-owner credentials from the network-facing production API, provide distinct migration and least-privilege runtime identities, route request repositories through bounded authority, and prove owner-only DDL and cross-tenant DML are denied. (FR-018, FR-019, FR-031, FR-060, FR-062, FR-065, FR-073)
- [ ] B291 Preserve expiry per-plan isolation while returning a nonzero degraded service result whenever any due plan fails, and bind monitoring/notification to the durable sanitized failure receipts. (FR-008, FR-013, FR-014, FR-036, FR-058, FR-060, FR-063, FR-067, FR-069, FR-071)
- [ ] B292 Bind Celery Beat readiness to a fresh heartbeat from the current deployment/container epoch and reject stale pre-deployment evidence regardless of its wall-clock age. (FR-013, FR-014, FR-036, FR-060, FR-063, FR-065)
- [ ] B293 Serialize expiry capacity admission and durable registration so concurrent writers cannot exceed the fixed inventory ceiling, with contention and crash-safe tests. (FR-008, FR-014, FR-036, FR-057, FR-058, FR-060, FR-065, FR-067, FR-071)
- [ ] B294 Separate dispatcher and data-rights worker identities so workers cannot enumerate or pre-read queued cross-tenant requests, require an exact unexpired claim token for fixed reads, and prove enumeration and ciphertext reads fail before claim. (FR-019, FR-023, FR-031, FR-036, FR-060, FR-065, FR-073)
- [ ] B295 Make tenant-only privacy closure always stop at tenant scope and add a separately reauthenticated, explicitly confirmed, reconciled global-account operation with idempotent receipts and all-tenant handling. (FR-019, FR-023, FR-031, FR-045, FR-060, FR-065)
- [ ] B296 Add a monotonic transactional object-reference generation fence or equivalent mutation lock around production capture and prove a real concurrent PostgreSQL A-to-B-to-A cycle is rejected. (FR-020 through FR-023, FR-060, FR-065, FR-066)
- [ ] B297 Generate export, RLS, erasure, and schema-drift coverage from one versioned subject-data registry and fail closed on every unregistered direct requester, owner, actor, reviewer, reporter, or appellant field. (FR-019, FR-023, FR-060, FR-065, FR-068)
- [ ] B298 Derive GlassSidebar orientation from the router-backed full path and hash, then prove tab-button activation and browser history keep exactly one matching `aria-current` item. (FR-012, FR-046, FR-050, FR-060, FR-063, FR-064, FR-075)
- [ ] B299 Make the monotonic reference-generation migration explicitly PostgreSQL-only so SQLite unit databases retain a valid migration graph while disposable PostgreSQL still proves trigger creation and reversal. (FR-020 through FR-023, FR-060, FR-063, FR-065, FR-066)
- [ ] B300 Regenerate the exact route/config surface lock after intentional API and environment additions, then prove hostile and stale-source drift remains rejected. (FR-060, FR-063, FR-065, FR-068, FR-078)
- [ ] B301 Regenerate operations visual evidence from the final normalized sources and current captures, then prove exact-source and stale-capture rejection before restarting complete gates. (FR-012, FR-060, FR-063, FR-064, FR-068, FR-075, FR-078)

## Phase 19 — Exact-head review cycle 32 corrections

- [ ] B302 Make every deployment failure artifact use non-interpolating Compose output and run one unconditional recursive secret gate as the final action on every success, failure, missing-address, and exception exit. (FR-005, FR-031, FR-060, FR-063, FR-065, FR-068, FR-071)
- [ ] B303 Require one exact trusted known-hosts file with reject-on-unknown semantics in every Paramiko and OpenSSH orchestration path before any secret transfer or remote mutation. (FR-005, FR-031, FR-060, FR-063, FR-065, FR-069)
- [ ] B304 Bootstrap least-privilege database roles and complete owner-scoped migrations before starting any network API, Django, worker, or scheduler process, and prove fresh and upgrade ordering. (FR-005, FR-013, FR-018, FR-031, FR-060, FR-062, FR-063, FR-065, FR-073)
- [ ] B305 Make rollback prove role and schema compatibility, exact source and deployment epoch, required container health, and internal API and Django readiness before it may report completion. (FR-005, FR-014, FR-060, FR-063, FR-065, FR-068, FR-071)
- [ ] B306 Route integrity-verified generic-expiry failure receipts into a bounded durable deduplicated alert observer and systemd failure path so degraded scans cannot disappear silently. (FR-008, FR-013, FR-014, FR-036, FR-058, FR-060, FR-063, FR-067, FR-069, FR-071)
- [ ] B307 Replace blanket API-table grants with one explicit per-table and per-verb matrix, deny migration-ledger and queue mutation, enforce tenant RLS on tenant-bearing API tables, and prove cross-tenant negative DML in real PostgreSQL. (FR-018, FR-019, FR-023, FR-031, FR-060, FR-062, FR-065, FR-073)
- [ ] B308 Extend the object-reference generation fence to media variants and media object versions and prove true A-to-B-to-A detection for every protected reference branch in real PostgreSQL. (FR-020 through FR-023, FR-060, FR-065, FR-066)
- [ ] B309 Stream every retained deployment artifact through the secret scanner with overlap-safe boundary matching and prove oversized and chunk-boundary canaries cannot be skipped. (FR-005, FR-031, FR-060, FR-063, FR-065, FR-068, FR-071)
- [ ] B310 Derive global privacy closure from the union of active memberships and every registered subject-bearing tenant row so orphaned historical tenant data is still exported and erased. (FR-019, FR-023, FR-031, FR-045, FR-060, FR-065, FR-068)
- [ ] B311 Canonicalize absent and invalid Content Workspace hashes to Records for sidebar orientation and prove default, valid, invalid, and browser-history states expose exactly one current destination. (FR-012, FR-046, FR-050, FR-060, FR-063, FR-064, FR-075)
- [ ] B312 Implement complete accessible tab semantics for the Content Workspace, including roving focus, arrow/Home/End keys, controlled panels, and stable history behavior. (FR-012, FR-050, FR-060, FR-063, FR-064, FR-075)
- [ ] B313 Correct the stale local-only email-service contract so documentation and tests accurately describe the supported bounded SMTP path. (FR-031, FR-060, FR-063, FR-068)
- [ ] B314 Run API schema creation before Django's cross-schema least-authority migrations in every fresh, upgrade, rollback, preview, and disposable PostgreSQL path, then prove ordered forward and reverse convergence. (FR-005, FR-018, FR-019, FR-031, FR-060, FR-062, FR-063, FR-065, FR-073)
- [ ] B315 Update the service-health contract to assert the intentional migration-before-startup graph rather than a removed legacy comment and prove workers remain mandatory after the fence. (FR-005, FR-013, FR-014, FR-060, FR-063, FR-065, FR-068)
- [ ] B316 Extract exact SSH trust admission into a side-effect-free tested module and cover missing, symlinked, malformed, pinned, and reject-on-unknown behavior above the changed-line floor. (FR-005, FR-031, FR-060, FR-063, FR-065, FR-069, FR-078)

## Phase 20 — Exact-head gate cycle 35 corrections

- [ ] B317 Reconcile the locked API environment after an interrupted PyYAML installation produced internally inconsistent package files, then prove real Compose YAML parsing succeeds from the exact locked dependency. (FR-060, FR-063, FR-065, FR-066, FR-078)
- [ ] B318 Cover recursive artifact-scanner filtering, symlink rejection, and both CLI terminal results so the security implementation remains directly exercised and the unchanged 90% changed-line floor passes honestly. (FR-005, FR-031, FR-060, FR-063, FR-065, FR-068, FR-071, FR-078)

## Phase 21 — Independent review cycle 36 corrections

- [ ] B319 Remove the mutable generic pre-deployment lifecycle, capture the true prior production head and epoch before mutation, and make one exact expected commit pass the API-first migration fence before any request or worker service starts. (FR-005, FR-013, FR-018, FR-031, FR-060, FR-062, FR-063, FR-065, FR-068)
- [ ] B320 Add an explicitly owner-approved authenticated first-host key enrollment boundary for newly created hosts, while every ordinary and changed-key connection remains pinned and fail closed before credentials or mutation. (FR-005, FR-007, FR-031, FR-060, FR-063, FR-065, FR-069)
- [ ] B321 Replace SAN-only and insecure HTTP deployment probes with CA-validating, hostname-verifying, expiry-valid TLS checks and prove self-signed, expired, wrong-host, and untrusted certificates fail. (FR-002, FR-005, FR-025, FR-031, FR-055, FR-060, FR-063, FR-065, FR-068)
- [ ] B322 Make every supported migration and remote-verification entrypoint run owner-scoped API migrations before Django migrations, before startup, without suppressed failure. (FR-005, FR-018, FR-031, FR-060, FR-062, FR-063, FR-065, FR-068, FR-073)
- [ ] B323 Revoke network API read/update access to the email outbox, expose only a fixed safe enqueue procedure, retain the separate worker authority, and prove reset/verification bearer material cannot be read or mutated through the API role. (FR-018, FR-019, FR-023, FR-031, FR-060, FR-065, FR-073)
- [ ] B324 Increment the object-reference generation fence for every site and asset reassignment that changes the immutable ledger, and prove A-to-B-to-A rejection for each protected column and branch. (FR-020 through FR-023, FR-060, FR-065, FR-066)
- [ ] B325 Make migration 0032 exactly restore its predecessor RLS/policy state on reverse, then prove latest-to-0031-to-latest convergence in disposable PostgreSQL. (FR-018, FR-019, FR-031, FR-060, FR-063, FR-065, FR-066, FR-073)
- [ ] B326 Make the migration CLI's programmatic entrypoint independent of the parent test runner arguments while its executable entrypoint still parses real command-line options, and directly prove check mode is non-mutating. (FR-005, FR-018, FR-060, FR-063, FR-065, FR-068)
- [ ] B327 Directly exercise the API migration disable and bounded lock-contention failure paths so the unchanged 90% changed-line floor covers meaningful release safety behavior. (FR-005, FR-014, FR-018, FR-036, FR-057, FR-060, FR-063, FR-065, FR-068, FR-078)

## Phase 22 — Independent review cycle 39 corrections

- [ ] B328 Remove the broad Traefik environment file, provide only explicitly allowlisted nonsecret configuration and scoped authentication files, prohibit raw container-environment capture, and prove remote and promoted evidence contain no credential canaries. (FR-005, FR-014, FR-031, FR-060, FR-062, FR-063, FR-065, FR-068, FR-071, FR-073)
- [ ] B329 Define and enforce a finite Full, UpdateOnly, and CreateIfMissing deployment-mode state machine that cannot silently skip provisioning or create duplicate provider resources, with exact provider, SSH, DNS, and mutation counts. (FR-005, FR-007, FR-057, FR-060, FR-063, FR-067, FR-069)
- [ ] B330 Verify staging-only HTTPS through a repository-pinned test trust store with hostname, validity, and SAN enforcement while preserving the explicit browser-untrusted staging contract; reject untrusted, expired, and wrong-host chains. (FR-002, FR-005, FR-025, FR-031, FR-055, FR-060, FR-063, FR-065, FR-068)
- [ ] B331 Capture the true prior remote source, deployment epoch, and private environment before mutation; invoke fail-hard rollback for every synchronous rollout failure and require exact source, epoch, schema, service, and endpoint restoration evidence. (FR-005, FR-014, FR-018, FR-031, FR-060, FR-063, FR-065, FR-068, FR-071)
- [ ] B332 Prevent asynchronous remote verification from producing terminal deployment success before process exit, completion marker, exact source and epoch, healthy endpoints, and complete evidence; reject timeout, crash, stale marker, and concurrent execution. (FR-005, FR-014, FR-036, FR-057, FR-060, FR-063, FR-065, FR-068, FR-071)
- [ ] B333 Make both supported operator migration wrappers bootstrap roles and run API then Django migrations with an explicit owner-scoped migration identity, and prove the sequence against an empty disposable PostgreSQL database. (FR-005, FR-018, FR-019, FR-031, FR-060, FR-062, FR-063, FR-065, FR-073)
- [ ] B334 Make tracked-environment detection fail closed for tracked files and Git inspection failures while distinguishing only a genuinely unavailable Git executable, with behavioral tests for every outcome. (FR-005, FR-031, FR-060, FR-063, FR-065, FR-068)
- [ ] B335 Give independently loaded Settings resources explicit localized unavailable states, never present fallback or empty data as fetched fact, and localize every bounded privacy operation kind and status with an honest unknown fallback in English, German, and Arabic. (FR-012, FR-014, FR-019, FR-023, FR-046, FR-060, FR-063, FR-064, FR-068, FR-075)
- [ ] B336 Replace contradictory substring-only deployment assertions with behavioral state-machine, process, rollback, TLS, secret-isolation, and terminal-success tests; rerun focused PostgreSQL, migration, frontend, browser, deployment, and security acceptance. (FR-005, FR-031, FR-060, FR-063 through FR-068, FR-071, FR-078)
- [ ] B337 Commit one clean repaired candidate, restart both complete gates and all critical repetitions, then repeat independent UX, data, and operations review until critical, high, and medium totals are zero before publication. (FR-007, FR-060, FR-063 through FR-069, FR-078)

## Phase 23 — Pre-gate hardening cycle 40 corrections

- [ ] B338 Represent a first deployment target without a prior environment as an explicit fresh state, and prove failure rollback restores the original checkout, removes the transferred environment, and leaves no Base2 container active. (FR-005, FR-007, FR-014, FR-031, FR-060, FR-063, FR-068, FR-071)
- [ ] B339 Structurally redact every basic-auth verifier from rendered Traefik evidence while preserving noncredential routing diagnostics, and prove inline, list, and unrelated user fields are handled safely. (FR-005, FR-014, FR-031, FR-060, FR-063, FR-065, FR-068, FR-071, FR-073)
- [ ] B340 Regenerate locked surfaces, rerun the full deployment suite and focused security checks, then create a new exact candidate only after the fresh-host and retained-evidence boundaries pass. (FR-060, FR-063 through FR-069, FR-078)
- [ ] B341 Directly exercise deployment-mode and staging-TLS command, retry, timeout, disabled-verification, and missing-SAN branches so changed-line coverage clears the unchanged 90% release floor. (FR-005, FR-025, FR-055, FR-060, FR-063, FR-065, FR-068, FR-078)

## Phase 24 — Independent review cycle 42 corrections

- [ ] B342 Propagate the deployment environment into the owner-scoped migration service, admit only the explicit migration role, and reject production owner connections without verify-full TLS, an absolute CA path, and an external database host. (FR-005, FR-018, FR-031, FR-060, FR-062, FR-063, FR-065, FR-073)
- [ ] B343 Localize every bounded security-event action in English, German, and Arabic with a safe localized unknown fallback, and prove backend tokens never appear in known or unknown user journeys. (FR-012, FR-014, FR-046, FR-060, FR-063, FR-064, FR-068, FR-075)
- [ ] B344 Replace fail-open provider discovery with paginated typed found, missing, pending, ambiguous, and error states; authorize creation only from authoritative missing and reject all uncertainty without provider mutation. (FR-005, FR-007, FR-014, FR-031, FR-057, FR-060, FR-063, FR-067, FR-069, FR-071)
- [ ] B345 Build and pin the API migration image to the same exact source image as the API runtime in forward and rollback paths, and prove a stale migration image cannot execute. (FR-005, FR-018, FR-031, FR-060, FR-062, FR-063, FR-065, FR-068)
- [ ] B346 Make fresh-target Compose teardown fail hard and prove exact Compose-project absence for generated project names, including a teardown-failure negative execution test. (FR-005, FR-014, FR-031, FR-060, FR-063, FR-068, FR-071)
- [ ] B347 Require a complete exact-source hash manifest and recursive secret scan of all required local deployment evidence before remote evidence deletion or terminal success; fail closed on copy, manifest, hash, or scan loss. (FR-005, FR-014, FR-031, FR-060, FR-063, FR-065, FR-068, FR-071)
- [ ] B348 Make AllTests enable both remote and local suites and propagate every pytest, lint, type, browser, smoke, and required-result failure without skipped-tool success. (FR-005, FR-012, FR-014, FR-060, FR-063, FR-064, FR-068, FR-071, FR-075, FR-078)
- [ ] B349 Verify Flower and Django-admin staging access boundaries with the pinned CA, hostname, and explicit expected status, and remove obsolete asynchronous retry guidance. (FR-002, FR-005, FR-014, FR-025, FR-031, FR-055, FR-060, FR-063, FR-065, FR-068)
- [ ] B350 Commit a clean repaired candidate, restart both complete gates and both ten-run critical suites, then repeat fresh UX, data, and operations review until all critical, high, and medium totals are zero. (FR-007, FR-060, FR-063 through FR-069, FR-078)

## Phase 25 — Pre-commit complete-gate cycle 43 correction

- [ ] B351 Replace the DigitalOcean coverage C tracer with deterministic pure-Python tracing after a full-suite run exposed interpreter-state corruption that passed when isolated; prove the exact partition and complete gate run repeatably without weakening coverage or failure propagation. (FR-005, FR-060, FR-063, FR-065, FR-068, FR-078)

## Phase 26 — Independent review cycle 44 corrections

- [ ] B352 Replace invented frontend security-action labels with one bounded English, German, and Arabic contract covering every real auth, identity, and user audit producer; retain an unknown fallback and enforce producer/translation parity. (FR-012, FR-014, FR-046, FR-060, FR-063, FR-064, FR-068, FR-075)
- [ ] B353 Validate the canonical effective production database target, including DATABASE_URL precedence, for every API, worker, and migration role; reject local, loopback, socket, malformed, and non-PostgreSQL overrides. (FR-005, FR-018, FR-031, FR-060, FR-062, FR-063, FR-065, FR-073)
- [ ] B354 Bind every evidence-manifest member to a matching canonical basename beneath the resolved evidence root and reject symlinked ancestors, lexical traversal, and external targets. (FR-005, FR-014, FR-031, FR-060, FR-063, FR-065, FR-068, FR-071)
- [ ] B355 Make every AllTests HTTPS and authenticated probe use the repository-pinned trust bundle with hostname and chain validation, propagate all curl failures, and prove hostile certificates cannot produce green evidence or receive credentials. (FR-002, FR-005, FR-014, FR-025, FR-031, FR-055, FR-060, FR-063, FR-065, FR-068, FR-071)
- [ ] B356 Carry exact provider identity end to end, paginate every lookup, reject duplicates, and serialize lookup plus create with a provider-backed atomic lease that fails closed on conflict or stale ownership. (FR-005, FR-007, FR-014, FR-031, FR-057, FR-060, FR-063, FR-067, FR-069, FR-071)
- [ ] B357 Reject credential-bearing repository transports, keep cloud-init credential-free, retain only its digest in local evidence, and move public source bootstrap behind authenticated SSH host enrollment with honest receipts. (FR-005, FR-007, FR-014, FR-031, FR-060, FR-063, FR-065, FR-068, FR-069, FR-071, FR-073)
- [ ] B358 Propagate the remote htpasswd escape validator's exact failure before diff, build, migration, service, or endpoint work and cover the ordering behavior. (FR-005, FR-014, FR-031, FR-060, FR-063, FR-065, FR-068, FR-071)
- [ ] B359 Remove floating root-piped bootstrap installers and mutable in-place upgrades, using only distribution-signed bounded bootstrap packages while preserving the separately pinned source/runtime release. (FR-005, FR-014, FR-031, FR-060, FR-063, FR-065, FR-068, FR-071)
- [ ] B360 Commit a new clean candidate, restart both 107-check gates and both ten-run critical suites, then repeat independent UX, data, and operations review until all critical, high, and medium totals are zero. (FR-007, FR-060, FR-063 through FR-069, FR-078)

## Phase 27 — Exact-head gate cycle 46 correction

- [ ] B361 Directly exercise the provider lookup CLI's typed success, provider-error, invalid-identity, empty-name, and lease-release paths so the unchanged 90% changed-line floor covers the new fail-closed provider boundary. (FR-005, FR-007, FR-060, FR-063, FR-065, FR-067, FR-068, FR-078)

## Phase 28 — Exact-head gate cycle 47 correction

- [ ] B362 Expose only the canonical looping utility copy to assistive technology and keyboard focus, remove viewport-dependent ordinal selection, and admit bounded subpixel centering variance; repeat the complete visual matrix before restarting both exact-head gates. (FR-002, FR-012, FR-046, FR-055, FR-060, FR-063, FR-064, FR-068, FR-075, FR-078)

## Phase 29 — Independent review cycle 48 corrections

- [ ] B363 Reject every collision among the PostgreSQL owner and all six runtime identities before any database call, retain distinct credentials per duty, and prove every collision leaves the owner and grants unchanged. (FR-019, FR-031, FR-060, FR-063, FR-065, FR-073)
- [ ] B364 Canonicalize the effective production database hostname, including terminal-dot DNS aliases and IPv4-mapped IPv6, and reject every local, loopback, unspecified, or link-local target for every production process role. (FR-005, FR-018, FR-031, FR-060, FR-062, FR-063, FR-065, FR-073)
- [ ] B365 Give every enabled public utility a real bounded action, prevent disabled utilities from changing state through pointer or keyboard input, localize the complete public Obsidian navigation for English, German, and Arabic, apply locale direction, and capture deterministic RTL/reflow evidence. (FR-012, FR-046, FR-050, FR-060, FR-063, FR-064, FR-068, FR-075)
- [ ] B366 Replace the provider tag pseudo-lock with a genuinely conditional exact-owner lease containing nonce and expiry, validate the provider response contract, release only matching ownership, and prove simultaneous, conflicting, crashed, and stale-owner behavior cannot duplicate paid resources. (FR-005, FR-007, FR-008, FR-014, FR-031, FR-057, FR-060, FR-063, FR-065, FR-067 through FR-069, FR-071)
- [ ] B367 Remove the production DropletIp identity bypass or require exact authoritative provider-ID and address equality, rejecting caller mismatch, ambiguity, and unresolved identity before connection or mutation. (FR-005, FR-007, FR-014, FR-031, FR-060, FR-063, FR-065, FR-068, FR-069)
- [ ] B368 Install the provider controller from a reviewed hash-locked dependency set without mutable upgrades, behaviorally pin the supported SDK response contract, and bind resolved distribution-package versions into bootstrap attestation. (FR-005, FR-014, FR-031, FR-059, FR-060, FR-063, FR-065, FR-068, FR-071)
- [ ] B369 Execute behavioral staging-TLS trust tests that accept the pinned valid hostname chain and reject wrong root, wrong hostname, expired, not-yet-valid, and transport-failure cases with a nonzero terminal result. (FR-002, FR-005, FR-014, FR-025, FR-031, FR-055, FR-060, FR-063, FR-065, FR-068, FR-071)
- [ ] B370 Normalize and regenerate all affected exact-source evidence, commit a clean candidate, restart both 107-check gates and both ten-run critical suites, then repeat fresh UX, data, and combined code/security/operations review until all critical, high, and medium totals are zero. (FR-007, FR-060, FR-063 through FR-069, FR-075, FR-078)

## Phase 30 — Independent review cycle 52 corrections

- [ ] B371 Reject percent-encoded production database host spellings before every process role can pass topology validation, covering encoded localhost, terminal-dot, IPv4, and IPv4-mapped IPv6 forms through DATABASE_URL and DB_HOST. (FR-005, FR-018, FR-031, FR-060, FR-062, FR-063, FR-065, FR-073)
- [ ] B372 Replace selection-widget semantics on the public utility action rail with truthful navigation/button semantics and prove keyboard focus, activation, disabled-state, and assistive-technology behavior. (FR-012, FR-046, FR-050, FR-060, FR-063, FR-064, FR-068, FR-075)
- [ ] B373 Localize the public home title, share prompt, and visible live share outcomes in English, German, and Arabic, and capture deterministic browser evidence after share success and fallback. (FR-012, FR-046, FR-050, FR-060, FR-063, FR-064, FR-068, FR-075)
- [ ] B374 Bound provider-ready status and address polling under one deadline, reject terminal states, preserve uncertain-outcome evidence, retain the exact lease after create uncertainty, and test perpetual-pending, terminal-error, and transport-failure sequences. (FR-004, FR-005, FR-008, FR-014, FR-057, FR-060, FR-063, FR-067 through FR-069, FR-071)
- [ ] B375 Remove ambient Git transport authority from the provider lease, enforce one explicit credential-free TLS or pinned-host SSH trust contract, and prove hostile URL rewriting, Git configuration, and transport-command injection cannot redirect serialization. (FR-005, FR-007, FR-008, FR-031, FR-060, FR-063, FR-065, FR-067 through FR-069, FR-071, FR-074)
- [ ] B376 Validate PROJECT_NAME as a bounded slug and DEPLOY_PATH as a canonical allowlisted absolute path before rendering any root cloud-init source, rejecting quotes, newlines, shell expansion, separators, traversal, and noncanonical paths. (FR-005, FR-007, FR-031, FR-060, FR-063, FR-065, FR-068, FR-071, FR-074)
- [ ] B377 Collect sanitized bootstrap package identity, authoritative provider identity, and exact user-data digest into required local evidence; make every write fail hard and bind all members to the terminal integrity manifest before cleanup or success. (FR-002, FR-005, FR-008, FR-014, FR-031, FR-059, FR-060, FR-063, FR-065, FR-068, FR-071)
- [ ] B378 Correct lease recovery documentation and make every supported provider dependency helper consume the same hash-locked requirements file with require-hashes and fail-hard behavior. (FR-005, FR-059, FR-060, FR-062, FR-063, FR-065, FR-068)
- [ ] B379 Regenerate locked evidence, commit a new clean candidate, restart both 107-check gates and both ten-run critical suites, then repeat fresh UX, data, and combined code/security/operations review until critical, high, and medium totals are zero. (FR-007, FR-060, FR-063 through FR-069, FR-075, FR-078)

## Phase 31 — Independent review cycle 53 corrections

- [ ] B380 Reject libc/libpq legacy numeric IPv4 aliases, including integer, abbreviated dotted, octal, and hexadecimal spellings, through both DB_HOST and DATABASE_URL for every production role. (FR-005, FR-018, FR-031, FR-060, FR-062, FR-063, FR-065, FR-073)
- [ ] B381 Enforce a documented hard maximum and coherent interval for paid-provider readiness at normalized configuration admission, so no caller can extend polling beyond the fixed terminal bound. (FR-004, FR-005, FR-008, FR-014, FR-057, FR-060, FR-063, FR-067 through FR-069, FR-071)
- [ ] B382 Replace inherited Git execution and authentication state with an absolute trusted Git executable plus one explicit owner-only askpass broker, scrub ambient executable, token, agent, proxy, and credential-manager variables, and prove legitimate and hostile paths behaviorally. (FR-005, FR-007, FR-008, FR-031, FR-059, FR-060, FR-063, FR-065, FR-067 through FR-069, FR-071, FR-074)
- [ ] B383 Require terminal deployment evidence to correlate exact authoritative discovered provider ID and IP with the provider response and a resolved deploy action, while keeping provision-only evidence nonterminal and separately modeled. (FR-002, FR-005, FR-008, FR-014, FR-060, FR-063, FR-065, FR-068, FR-069, FR-071)
- [ ] B384 Make manual-copy feedback temporally accurate after the blocking fallback closes and verify localized visible feedback without claiming an open dialog. (FR-012, FR-046, FR-050, FR-060, FR-063, FR-064, FR-068, FR-075)
- [ ] B385 Add an exact-clean-head repetition runner that atomically writes source-bound, hash-bound 10+10 evidence; commit a new candidate, rerun both complete gates and the persisted repetitions, then repeat fresh reviews until critical, high, and medium totals are zero. (FR-007, FR-060, FR-063 through FR-069, FR-075, FR-078)

## Phase 32 — Independent review cycle 55 corrections

- [ ] B386 Reject RFC localhost namespaces and standard libc IPv6/localdomain aliases through DB_HOST and DATABASE_URL for every production role without resolver-dependent admission. (FR-005, FR-018, FR-031, FR-060, FR-062, FR-063, FR-065, FR-073)
- [ ] B387 Replace the repetition-runner environment denylist with a fixed hermetic allowlist, isolated HOME/config roots, and explicit test mode so connection URLs, profiles, provider configuration, and unknown credentials never reach test children. (FR-005, FR-014, FR-031, FR-060, FR-063, FR-065, FR-068, FR-073, FR-078)
- [ ] B388 Run repetitions from one detached exact-commit worktree, revalidate both isolated and controller sources after every child and before promotion, and reject symlinked or unexpected evidence members. (FR-005, FR-007, FR-014, FR-031, FR-060, FR-063, FR-065, FR-068, FR-071, FR-078)
- [ ] B389 Enforce native-Windows broker owner and non-writable-ancestry ACLs, use only fixed system Git locations, and build a minimal Git child environment which excludes loader injection and every ambient authority source. (FR-005, FR-007, FR-008, FR-031, FR-059, FR-060, FR-063, FR-065, FR-067 through FR-069, FR-071, FR-074)
- [ ] B390 Commit a clean repaired candidate, rerun both exact complete gates and persisted 10+10 repetitions, then repeat fresh UX, data, and operations review until all critical, high, and medium totals are zero. (FR-007, FR-060, FR-063 through FR-069, FR-075, FR-078)

## Phase 33 — Pre-commit complete-gate cycle 56 correction

- [ ] B391 Directly exercise trusted-Git symlink and resolution-failure rejection so the unchanged changed-line coverage floor admits the repaired provider boundary. (FR-005, FR-007, FR-060, FR-063, FR-065, FR-068, FR-071, FR-074, FR-078)
- [ ] B392 Commit only after the complete repaired tree passes the full gate without reducing or rounding its 90% changed-line floor, then restart exact-head evidence. (FR-005, FR-007, FR-060, FR-063 through FR-069, FR-078)

## Phase 34 — Independent review cycle 57 corrections

- [ ] B393 Derive the native Windows directory and PowerShell ACL verifier through a trusted kernel API, ignore hostile SYSTEMROOT, WINDIR, and COMSPEC values, and give token-bearing Git only a newly created ACL-validated private temporary directory. (FR-005, FR-007, FR-008, FR-014, FR-031, FR-059, FR-060, FR-063, FR-065, FR-067 through FR-069, FR-071, FR-074)
- [ ] B394 Reject symlinked or non-directory repetition-evidence ancestors before creation or replay, proving ignored private evidence cannot be redirected outside the resolved repository. (FR-005, FR-014, FR-031, FR-060, FR-063, FR-065, FR-068, FR-071, FR-078)
- [ ] B395 Commit a new clean candidate, rerun both exact complete gates and persisted 10+10 repetitions, then repeat fresh UX, data, and operations review until all critical, high, and medium totals are zero. (FR-007, FR-060, FR-063 through FR-069, FR-075, FR-078)

## Phase 35 — Independent review cycle 58 corrections

- [ ] B396 Route authoritative lease-repository construction, deletion, and Git scratch through one fixed-anchor private-temp factory which never consumes ambient temp roots and validates Windows ACLs or Unix owner, mode, and writable ancestry. (FR-005, FR-007, FR-008, FR-014, FR-031, FR-060, FR-063, FR-065, FR-067 through FR-069, FR-071, FR-074)
- [ ] B397 Prove hostile ambient TEMP/TMP values cannot select either the outer lease repository or inner Git scratch and unsafe Unix ancestry fails closed before lease-object construction. (FR-005, FR-007, FR-008, FR-014, FR-031, FR-060, FR-063, FR-065, FR-068, FR-071, FR-074)
- [ ] B398 Enforce owner-private permissions on repetition evidence roots, exact-commit directories, manifests, and members during creation and replay, rejecting permission drift. (FR-005, FR-014, FR-031, FR-060, FR-063, FR-065, FR-068, FR-071, FR-078)
- [ ] B399 Commit a new clean candidate, rerun both exact complete gates and persisted 10+10 repetitions, then repeat fresh UX, data, and operations review until all critical, high, and medium totals are zero. (FR-007, FR-060, FR-063 through FR-069, FR-075, FR-078)

## Phase 36 — Pre-commit complete-gate cycle 59 correction

- [ ] B400 Directly test Windows ACL pass/failure and filesystem-error admission for the unified private-path factory so the unchanged 90% changed-line floor covers its fail-closed branches. (FR-005, FR-007, FR-060, FR-063, FR-065, FR-068, FR-071, FR-074, FR-078)
- [ ] B401 Re-run the isolated light-theme media visual owner after its one-time baseline mismatch, retain the failed evidence, and require a complete green gate before committing without changing an unrelated accepted baseline. (FR-002, FR-012, FR-055, FR-060, FR-063, FR-064, FR-068, FR-075, FR-078)

## Phase 37 — Exact-head repetition cycle 60 correction

- [ ] B402 Persist every failed exact-head repetition as bounded, private, source/suite/repetition-bound, member-hashed evidence before returning a sanitized terminal error, so transient and deterministic failures remain diagnosable. (FR-002, FR-005, FR-007, FR-014, FR-031, FR-060, FR-063, FR-065, FR-068, FR-071, FR-078)
- [ ] B403 Reproduce the failed backup/release/deployment family under the same hermetic environment, retain its result, and restart the complete exact-head evidence set only after the runner itself proves failure and success paths. (FR-005, FR-007, FR-060, FR-063 through FR-069, FR-078)

## Phase 38 — Concurrent lease and coverage cycle 61 correction

- [ ] B404 Keep the fixed owner-only lease scratch parent stable while concurrent callers use independently removed child directories, preventing cleanup races from rejecting every otherwise valid contender. (FR-005, FR-007, FR-008, FR-014, FR-031, FR-057, FR-060, FR-063, FR-065, FR-067 through FR-069, FR-071, FR-074, FR-078)
- [ ] B405 Prove repeated concurrent private-temp construction and exact remote claims admit one owner without duplicate authority, while retaining fail-closed conflicting, crashed, stale-owner, and transport behavior. (FR-005, FR-007, FR-008, FR-014, FR-031, FR-057, FR-060, FR-063, FR-065, FR-067 through FR-069, FR-071, FR-078)
- [ ] B406 Cover bounded failure-log truncation, malformed replay, permission drift, and symlinked failure roots so the unchanged 90% changed-line threshold directly exercises the diagnostic trust boundary. (FR-005, FR-007, FR-060, FR-063, FR-065, FR-068, FR-071, FR-078)

## Phase 39 — Exact coverage cycle 62 correction

- [ ] B407 Directly prove a non-directory repetition-evidence ancestor is rejected so the complete tree clears the exact unchanged 90% changed-line floor without rounding or exclusion. (FR-005, FR-007, FR-060, FR-063, FR-065, FR-068, FR-071, FR-078)

## Phase 40 — Native-Windows evidence boundary cycle 63 correction

- [ ] B408 Fail the WSL/Linux-owned exact-repetition runner closed on native Windows before creating any evidence path, rather than treating chmod as a Windows privacy boundary. (FR-005, FR-007, FR-031, FR-060, FR-063, FR-065, FR-068, FR-071, FR-074, FR-078)
- [ ] B409 Prove unsupported native-Windows execution creates no artifact root, reads no source, and returns only a sanitized terminal platform error. (FR-005, FR-007, FR-031, FR-060, FR-063, FR-065, FR-068, FR-071, FR-074, FR-078)
- [ ] B410 Restart all exact gates, repetitions, and independent reviews from a new candidate; accept closeout only when every reviewer reports zero critical, high, medium, and low findings. (FR-005, FR-007, FR-060, FR-063 through FR-069, FR-075, FR-078)

## Phase 41 — Hosted CI parity cycle 64 corrections

- [ ] B411 Replace mutable CI type-tool installation and conflicting development pins with exact service-specific dependency sets, including the required PyYAML stubs, and prove fresh installs pass dependency checks. (FR-005, FR-014, FR-031, FR-059, FR-060, FR-063, FR-065, FR-068, FR-078)
- [ ] B412 Give Django database settings an explicit truthful nested value type, add pinned Django MyPy to its development environment and complete gate, and require both API and Django typing in local and hosted acceptance. (FR-005, FR-014, FR-031, FR-060, FR-063, FR-065, FR-068, FR-078)
- [ ] B413 Add an owner-scoped, non-serving API migration service to the disposable E2E graph and require successful roles -> API migrations -> Django migrations before any runtime service, browser test, or smoke probe. (FR-005, FR-014, FR-019, FR-031, FR-060, FR-063, FR-065, FR-068, FR-071, FR-073, FR-078)
- [ ] B414 Make backend integration use the same complete bounded-role bootstrap and migration order, forbidding the incomplete targeted Django migration that omitted runtime functions. (FR-005, FR-014, FR-019, FR-031, FR-060, FR-063, FR-065, FR-068, FR-071, FR-073, FR-078)
- [ ] B415 Exercise email enqueue as the API runtime and inspection, claim, and settlement as the email worker without granting either role owner authority or direct privileges outside its duty. (FR-005, FR-014, FR-019, FR-031, FR-060, FR-063, FR-065, FR-068, FR-071, FR-073, FR-078)
- [ ] B416 Add workflow and Compose contracts for exact tool pins, complete migration ordering, owner-only migration services, and migration-targeted failure evidence so these hosted-only failures become local release blockers. (FR-002, FR-005, FR-014, FR-031, FR-060, FR-063, FR-065, FR-068, FR-071, FR-078)
- [ ] B417 Commit a new clean candidate, rerun both complete gates, fresh-volume E2E and smoke, exact-source repetitions, independent reviews, and all hosted checks; accept readiness only with zero findings and no skipped user-visible lane. (FR-002, FR-005, FR-007, FR-060, FR-063 through FR-069, FR-075, FR-078)

## Phase 42 — Fresh-volume readiness cycle 65 corrections

- [ ] B418 Add a reversible owner-applied migration granting the API runtime only read access to Django's non-secret migration ledger, retaining all existing least-privilege and RLS boundaries. (FR-005, FR-014, FR-019, FR-031, FR-060, FR-063, FR-065, FR-068, FR-071, FR-073, FR-078)
- [ ] B419 Bind API schema readiness to the exact latest required API and Django migration identifiers so an incomplete predecessor cannot report healthy. (FR-002, FR-005, FR-014, FR-031, FR-060, FR-063, FR-065, FR-068, FR-071, FR-078)
- [ ] B420 Recreate the disposable database from empty storage and prove migration completion, healthy runtime startup, ledger-only API visibility, and continued denial of owner, DDL, unrelated table, and bypass-RLS authority. (FR-002, FR-005, FR-014, FR-019, FR-031, FR-060, FR-063, FR-065, FR-068, FR-071, FR-073, FR-078)

## Phase 43 — Disposable-stack isolation cycle 66 corrections

- [ ] B421 Parameterize only the disposable stack's host API and web ports with documented unchanged CI defaults so parallel local validation cannot require stopping an unrelated stack. (FR-004, FR-005, FR-014, FR-031, FR-060, FR-063, FR-065, FR-068, FR-071, FR-078)
- [ ] B422 Re-run the empty-volume stack in an isolated host-port namespace, preserving the pre-existing local stack, and complete health, smoke, browser, migration, and role-boundary proof. (FR-002, FR-004, FR-005, FR-014, FR-031, FR-060, FR-063 through FR-065, FR-068, FR-071, FR-075, FR-078)

## Phase 44 — Synthetic test-support isolation cycle 67 corrections

- [ ] B423 Remove test-only outbox inspection from the normal API authority path and expose only that keyed route through a synthetic application which fails closed outside explicit E2E mode. (FR-005, FR-014, FR-019, FR-031, FR-060, FR-063, FR-065, FR-068, FR-071, FR-073, FR-078)
- [ ] B424 Run the synthetic route under the bounded email-worker read role on a loopback-only disposable port, with no docs, OpenAPI, production Compose, deployment, or unrelated API surface. (FR-005, FR-014, FR-019, FR-031, FR-060, FR-063, FR-065, FR-068, FR-071, FR-073, FR-078)
- [ ] B425 Point browser acceptance explicitly at the isolated synthetic endpoint and prove key rejection, production absence, successful token workflows, and continued denial of direct outbox reads to the API runtime. (FR-002, FR-005, FR-014, FR-019, FR-031, FR-060, FR-063 through FR-065, FR-068, FR-071, FR-075, FR-078)

## Phase 45 — Full-gate cycle 68 corrections

- [ ] B426 Keep the reversed API-role proof on explicit function absence without resolving privileges for an undefined signature, while the forward proof still requires exact API-role execute authority. (FR-005, FR-014, FR-019, FR-031, FR-060, FR-063, FR-065, FR-068, FR-071, FR-073, FR-078)
- [ ] B427 Add a contract for the forward-only privilege lookup and regenerate the surface-drift lock from the final manifest without weakening drift detection. (FR-002, FR-005, FR-007, FR-060, FR-063, FR-065, FR-068, FR-071, FR-078)
- [ ] B428 Re-run PostgreSQL acceptance, surface drift, the full complete gate, and all exact-candidate evidence only after both cycle-68 defects pass locally. (FR-002, FR-005, FR-007, FR-060, FR-063 through FR-069, FR-075, FR-078)

## Phase 46 — Hosted collection cycle 69 corrections

- [ ] B429 Rename the synthetic support entrypoint outside pytest's recursive test-module grammar without changing its loopback-only, keyed, non-production boundary. (FR-005, FR-014, FR-019, FR-031, FR-060, FR-063, FR-065, FR-068, FR-071, FR-073, FR-078)
- [ ] B430 Add a regression proving normal API and integration collection cannot import the synthetic startup guard while explicit synthetic startup still fails closed without E2E mode and key. (FR-002, FR-005, FR-014, FR-031, FR-060, FR-063, FR-065, FR-068, FR-071, FR-078)
- [ ] B431 Commit a new candidate and restart the complete gate, fresh-volume browser and role proof, exact repetitions, independent reviews, and all hosted checks from the new SHA. (FR-002, FR-005, FR-007, FR-060, FR-063 through FR-069, FR-075, FR-078)

## Phase 47 — Post-format lock cycle 70 corrections

- [ ] B432 Run the surface-drift validator after lint-staged formatting so a formatter cannot leave governed bytes inconsistent with their reviewed generated lock. (FR-002, FR-005, FR-007, FR-060, FR-063, FR-065, FR-068, FR-071, FR-078)
- [ ] B433 Prove the pre-commit ordering is formatter then validator and retain fail-closed behavior rather than silently regenerating or approving drift in the hook. (FR-002, FR-005, FR-007, FR-060, FR-063, FR-065, FR-068, FR-071, FR-078)
- [ ] B434 Regenerate the lock from final formatted bytes, commit a new candidate, and restart all exact-source local and hosted evidence only after the post-format validator passes. (FR-002, FR-005, FR-007, FR-060, FR-063 through FR-069, FR-075, FR-078)

## Phase 48 — Integration selection cycle 71 corrections

- [ ] B435 Override the API pytest default with an explicit integration marker for the isolated role-correct email-outbox invocation so it cannot silently select zero tests. (FR-002, FR-005, FR-014, FR-019, FR-031, FR-060, FR-063, FR-065, FR-068, FR-071, FR-073, FR-078)
- [ ] B436 Bind the exact isolated integration command into CI policy tests and prove it collects and executes both API-enqueue/email-worker-settlement cases. (FR-002, FR-005, FR-014, FR-019, FR-031, FR-060, FR-063, FR-065, FR-068, FR-071, FR-073, FR-078)
- [ ] B437 Commit a new candidate and restart all local, fresh-volume, repetition, independent-review, and hosted evidence from the exact replacement SHA. (FR-002, FR-005, FR-007, FR-060, FR-063 through FR-069, FR-075, FR-078)

## Phase 49 — Changed-line coverage cycle 72 corrections

- [ ] B438 Directly exercise missing email-worker credentials and require a sanitized fail-closed result before any role or pool transition. (FR-002, FR-005, FR-014, FR-019, FR-031, FR-060, FR-063, FR-065, FR-068, FR-071, FR-073, FR-078)
- [ ] B439 Prove the email integration context closes pools around the role switch and restores both present and absent owner environment values on exit. (FR-002, FR-005, FR-014, FR-019, FR-031, FR-060, FR-063, FR-065, FR-068, FR-071, FR-073, FR-078)
- [ ] B440 Clear the unchanged exact 90% changed-line floor, commit a new candidate, and restart all required exact-source and hosted evidence from its SHA. (FR-002, FR-005, FR-007, FR-060, FR-063 through FR-069, FR-075, FR-078)

## Phase 50 — Staged Python lint cycle 73 corrections

- [ ] B441 Replace the nested missing-credential assertion with a Ruff-clean multi-context proof without weakening its fail-closed behavior. (FR-002, FR-005, FR-014, FR-031, FR-060, FR-063, FR-065, FR-068, FR-071, FR-078)
- [ ] B442 Run pinned API Ruff over every staged API Python file in the pre-commit hook and add a repository contract for the exact lint-staged command. (FR-002, FR-005, FR-014, FR-031, FR-059, FR-060, FR-063, FR-065, FR-068, FR-071, FR-078)
- [ ] B443 Commit only after staged Ruff and surface validation pass, then restart every local, fresh-volume, repetition, review, and hosted check from the replacement SHA. (FR-002, FR-005, FR-007, FR-060, FR-063 through FR-069, FR-075, FR-078)

## Phase 51 — Responsive layout cycle 74 corrections

- [ ] B444 Recompute navigation edge state after document-size changes, load, page restoration, and the settled post-mount layout while cleaning every observer and listener on unmount. (FR-002, FR-005, FR-007, FR-021, FR-060, FR-063, FR-065, FR-068, FR-075, FR-078)
- [ ] B445 Make the movement-control browser proof establish and verify its top-edge precondition before asserting that descent is available. (FR-002, FR-005, FR-007, FR-021, FR-060, FR-063, FR-065, FR-068, FR-075, FR-078)
- [ ] B446 Repeat the exact tablet movement interaction at least twenty times and retain zero-failure evidence before restarting the complete gates. (FR-002, FR-005, FR-007, FR-021, FR-060, FR-063, FR-065, FR-068, FR-075, FR-078)
- [ ] B447 Commit a replacement candidate and restart every complete gate, fresh-volume proof, exact repetition, independent review, and hosted check from that exact SHA. (FR-002, FR-005, FR-007, FR-060, FR-063 through FR-069, FR-075, FR-078)

## Phase 52 — Isolated E2E operator cycle 75 corrections

- [ ] B448 Document the exact isolated E2E port-variable names, unchanged hosted defaults, fixed disposable project name, browser URLs, and exact-project volume teardown. (FR-002, FR-004, FR-005, FR-007, FR-060, FR-063, FR-065, FR-068, FR-071, FR-078)
- [ ] B449 Add a policy regression binding every documented isolated port variable and teardown boundary to the Compose interface. (FR-002, FR-004, FR-005, FR-007, FR-060, FR-063, FR-065, FR-068, FR-071, FR-078)
- [ ] B450 Commit a replacement candidate and restart both complete gates, fresh-volume E2E, exact repetitions, independent reviews, and hosted checks from that exact SHA. (FR-002, FR-005, FR-007, FR-060, FR-063 through FR-069, FR-075, FR-078)

## Phase 53 — Concurrent visual cycle 76 corrections

- [ ] B451 Parameterize only the visual harness's numeric unprivileged loopback port, preserving default 4174, strict binding, and server non-reuse. (FR-002, FR-004, FR-005, FR-007, FR-021, FR-060, FR-063, FR-065, FR-068, FR-075, FR-078)
- [ ] B452 Reject nonnumeric, privileged, and out-of-range visual port inputs before starting a build or server, and bind the exact boundary into the visual harness contract. (FR-002, FR-004, FR-005, FR-007, FR-060, FR-063, FR-065, FR-068, FR-071, FR-078)
- [ ] B453 Run simultaneous focused visual suites on distinct loopback ports and prove both pass without reusing or terminating either server. (FR-002, FR-004, FR-005, FR-007, FR-021, FR-060, FR-063, FR-065, FR-068, FR-075, FR-078)
- [ ] B454 Commit a replacement candidate and restart both complete gates, fresh-volume E2E, exact repetitions, independent reviews, and hosted checks from that exact SHA. (FR-002, FR-005, FR-007, FR-060, FR-063 through FR-069, FR-075, FR-078)

## Phase 54 — Isolated browser cycle 77 corrections

- [ ] B455 Bind E2E API, synthetic support, and web publications to loopback while retaining unchanged hosted port defaults. (FR-002, FR-004, FR-005, FR-014, FR-031, FR-060, FR-063, FR-065, FR-068, FR-071, FR-078)
- [ ] B456 Derive a coherent browser API URL, frontend origin, and CORS allowlist for isolated runs without making arbitrary hosts or production origins part of the test runner. (FR-002, FR-004, FR-005, FR-014, FR-031, FR-060, FR-063, FR-065, FR-068, FR-071, FR-078)
- [ ] B457 Add a no-schema synthetic health endpoint and require it in both Compose health admission and hosted readiness polling. (FR-002, FR-004, FR-005, FR-014, FR-019, FR-031, FR-060, FR-063, FR-065, FR-068, FR-071, FR-078)
- [ ] B458 Add a real Playwright page journey that renders the public application, submits registration through the configured browser API, observes the exact response, and reaches the authenticated dashboard. (FR-002, FR-004, FR-005, FR-021, FR-060, FR-063, FR-065, FR-068, FR-075, FR-078)
- [ ] B459 Provide one fixed-project WSL runner that validates distinct unprivileged ports, precleans its exact disposable volumes, waits boundedly for all services, and traps exact teardown on every exit. (FR-002, FR-004, FR-005, FR-007, FR-014, FR-031, FR-060, FR-063, FR-065, FR-068, FR-071, FR-078)
- [ ] B460 Parse and assert loopback mappings and origin/build coherence, plus runner preclean, readiness, validation, and cleanup, instead of relying on documentation substrings. (FR-002, FR-004, FR-005, FR-007, FR-014, FR-031, FR-060, FR-063, FR-065, FR-068, FR-071, FR-078)
- [ ] B461 Prove stale-project removal, fresh migrations, three-service readiness, real browser/API flows, and empty exact-project inventory after runner success and an injected failure. (FR-002, FR-004, FR-005, FR-007, FR-014, FR-019, FR-031, FR-060, FR-063 through FR-065, FR-068, FR-071, FR-075, FR-078)
- [ ] B462 Commit a replacement candidate and restart both complete gates, fresh-volume E2E, exact repetitions, independent reviews, and hosted checks from that exact SHA. (FR-002, FR-005, FR-007, FR-060, FR-063 through FR-069, FR-075, FR-078)

## Phase 55 — Same-origin browser cycle 78 corrections

- [ ] B463 Route frontend `/api` requests to the fixed private Compose API service with bounded timeouts and no client-controlled upstream. (FR-002, FR-004, FR-005, FR-014, FR-031, FR-060, FR-063, FR-065, FR-068, FR-071, FR-078)
- [ ] B464 Preserve same-origin browser policy and `connect-src 'self'`, removing the unnecessary configurable browser API build origin. (FR-002, FR-004, FR-005, FR-014, FR-031, FR-060, FR-063, FR-065, FR-068, FR-071, FR-078)
- [ ] B465 Bind the page-driven registration response to the configured web origin and prove the exact POST returns 201 before the dashboard transition. (FR-002, FR-004, FR-005, FR-021, FR-060, FR-063, FR-065, FR-068, FR-075, FR-078)
- [ ] B466 Re-run the fixed-project fresh-volume lifecycle, verify automatic teardown, then commit a replacement and restart every exact-source gate, repetition, review, and hosted check. (FR-002, FR-005, FR-007, FR-060, FR-063 through FR-069, FR-075, FR-078)

## Phase 56 — Fixed-project concurrency cycle 79 corrections

- [ ] B467 Acquire a nonblocking repository-local process lock before any fixed-project Docker operation so concurrent isolated-runner invocations cannot preclean or tear down one another. (FR-002, FR-004, FR-005, FR-007, FR-014, FR-031, FR-060, FR-063, FR-065, FR-068, FR-071, FR-078)
- [ ] B468 Bind lock ordering and concurrent rejection into local policy tests and operator guidance, retaining automatic kernel release after success, failure, or interruption. (FR-002, FR-004, FR-005, FR-007, FR-014, FR-031, FR-060, FR-063, FR-065, FR-068, FR-071, FR-078)
- [ ] B469 Prove one owner can complete while a concurrent contender fails before Docker access, then commit a replacement and restart all exact-source evidence from the new SHA. (FR-002, FR-005, FR-007, FR-060, FR-063 through FR-069, FR-075, FR-078)

## Phase 57 — Hosted bare-health guard cycle 80 corrections

- [ ] B470 Preserve the repository-wide ban on bare product `/health` routes and rename the synthetic-only readiness route so it cannot be mistaken for an admitted product surface. (FR-002, FR-005, FR-014, FR-031, FR-060, FR-063, FR-065, FR-068, FR-071, FR-078)
- [ ] B471 Update Compose, hosted polling, the WSL runner, and boundary tests to require the exact synthetic readiness route while proving bare `/health`, `/api/health`, docs, and OpenAPI remain absent from the synthetic process. (FR-002, FR-004, FR-005, FR-014, FR-019, FR-031, FR-060, FR-063, FR-065, FR-068, FR-071, FR-078)
- [ ] B472 Commit a replacement candidate, require both hosted guard jobs to pass, and restart all exact-source gates, repetitions, isolated-stack proofs, and reviews from the new SHA. (FR-002, FR-005, FR-007, FR-060, FR-063 through FR-069, FR-075, FR-078)

## Phase 58 — Coverage tracer cycle 81 corrections

- [ ] B473 Replace the DigitalOcean partition's unstable pure-Python tracer with Python 3.12 `sys.monitoring` coverage while retaining isolated partitions, exact source selection, coverage combination, and nonzero failure propagation. (FR-002, FR-005, FR-007, FR-060, FR-063, FR-065, FR-068, FR-071, FR-078)
- [ ] B474 Bind the exact tracer core into the complete-gate contract and repeatedly exercise the formerly crashing generated-child partition plus the complete DigitalOcean coverage runner. (FR-002, FR-005, FR-007, FR-060, FR-063, FR-065, FR-068, FR-071, FR-078)
- [ ] B475 Commit a replacement candidate and restart both full gates, repetitions, isolated-stack proof, hosted checks, and independent reviews only after coverage succeeds without tracer warnings or retries. (FR-002, FR-005, FR-007, FR-060, FR-063 through FR-069, FR-075, FR-078)

## Phase 59 — Exact repetition native-crash cycle 82 corrections

- [ ] B476 Add deterministic Python hash and system-malloc settings to the exact-head hermetic child environment without admitting ambient credentials, network endpoints, profiles, or provider authority. (FR-005, FR-007, FR-014, FR-031, FR-060, FR-063, FR-065, FR-068, FR-071, FR-078)
- [ ] B477 Permit at most three attempts only for native crash return codes while retaining every failed attempt as bounded private hash-bound evidence; keep ordinary assertion, timeout, source-drift, and integrity failures immediately terminal. (FR-002, FR-005, FR-007, FR-014, FR-031, FR-060, FR-063, FR-065, FR-068, FR-071, FR-078)
- [ ] B478 Bind recovered native-crash evidence paths into the successful exact-source manifest and prove one recovery, exhaustion, ordinary failure, replay, tamper, environment allowlisting, and exact cleanup behavior. (FR-002, FR-005, FR-007, FR-014, FR-031, FR-060, FR-063, FR-065, FR-068, FR-071, FR-078)
- [ ] B479 Commit a replacement candidate and restart the fresh stack, exact repetitions, both full gates, hosted checks, and independent reviews from that SHA with no unreported failure. (FR-002, FR-005, FR-007, FR-060, FR-063 through FR-069, FR-075, FR-078)

## Phase 60 — Disposable migration native-crash cycle 83 corrections

- [ ] B480 Add deterministic Python allocator/hash settings only to disposable Django migration containers in PostgreSQL acceptance. (FR-002, FR-005, FR-014, FR-019, FR-031, FR-060, FR-063, FR-065, FR-068, FR-071, FR-073, FR-078)
- [ ] B481 Retry only idempotent transactional disposable migrations at most three times for native exits `-11`, `134`, or `139`, while keeping role assertions, SQL checks, ordinary failures, and cleanup single-shot and fail-closed. (FR-002, FR-005, FR-007, FR-014, FR-019, FR-031, FR-060, FR-063, FR-065, FR-068, FR-071, FR-073, FR-078)
- [ ] B482 Prove native recovery, native exhaustion, immediate ordinary failure, fixed command scope, unchanged role checks, and final disposable-container cleanup. (FR-002, FR-005, FR-007, FR-014, FR-019, FR-031, FR-060, FR-063, FR-065, FR-068, FR-071, FR-073, FR-078)
- [ ] B483 Commit a replacement candidate and restart the fresh stack, exact repetitions, both full gates, hosted checks, and independent reviews from that SHA. (FR-002, FR-005, FR-007, FR-060, FR-063 through FR-069, FR-075, FR-078)

## Phase 61 — Django coverage native-crash cycle 84 corrections

- [ ] B484 Replace Django's C coverage tracer with Python 3.12 `sys.monitoring` plus deterministic allocator/hash settings while preserving the exact test inventory and coverage report. (FR-002, FR-005, FR-007, FR-060, FR-063, FR-065, FR-068, FR-071, FR-078)
- [ ] B485 Retry the isolated Django coverage process at most three times only for native exits, deleting partial reports before retry while keeping test assertion and configuration failures immediately terminal. (FR-002, FR-005, FR-007, FR-060, FR-063, FR-065, FR-068, FR-071, FR-078)
- [ ] B486 Prove recovery, exhaustion, ordinary fail-fast behavior, partial-report removal, fixed suite/config, stable tracing, and a complete 96-test Django coverage run without late-start measurement warnings. (FR-002, FR-005, FR-007, FR-060, FR-063, FR-065, FR-068, FR-071, FR-078)
- [ ] B487 Commit a replacement candidate and restart every exact-source and hosted proof plus all independent reviews from that SHA. (FR-002, FR-005, FR-007, FR-060, FR-063 through FR-069, FR-075, FR-078)

## Phase 62 — Independent review cycle 85 corrections

- [ ] B488 Bind every recovered native-crash failure receipt into the passed repetition manifest with its exact relative path and manifest SHA-256. (FR-002, FR-008, FR-060, FR-063, FR-065, FR-068, FR-070)
- [ ] B489 Revalidate each recovery receipt, failure log, digest, hash, size, private mode, exact source, fixed command, suite, repetition, attempt, native exit, containment, and nonsymlink path before replaying passed evidence. (FR-002, FR-008, FR-031, FR-060, FR-063, FR-065, FR-068, FR-070)
- [ ] B490 Prove valid recovery replay and fail closed on deletion, content tamper, symlink, traversal, wrong source, invalid exit, duplicate reference, ordinary failure, and native exhaustion. (FR-008, FR-060, FR-063, FR-065, FR-068, FR-070)
- [ ] B491 Declare every repository-test runtime import in the exact hash-locked orchestrator environment, validate the lock contract, repair stale profile and database-time lease assertions, and run the documented command successfully. (FR-002, FR-059, FR-062, FR-063, FR-068, FR-070)
- [ ] B492 Commit a replacement candidate and restart the clean-stack proof, exact repetitions, both complete gates, hosted checks, and every independent review from that SHA. (FR-002, FR-005, FR-007, FR-060, FR-063 through FR-069, FR-075, FR-078)

## Phase 63 — Django interpreter-isolation cycle 86 corrections

- [ ] B493 Execute every exact Django unit-test module in a fresh deterministic `sys.monitoring` coverage process so corrupted interpreter state cannot propagate across unrelated modules. (FR-002, FR-060, FR-063, FR-068, FR-070)
- [ ] B494 Retain native-only bounded recovery per fixed partition, combine parallel coverage data replay-safely, remove partition residue, and preserve immediate ordinary-failure propagation. (FR-002, FR-008, FR-060, FR-063, FR-065, FR-068, FR-070)
- [ ] B495 Repeat the formerly failing migration module twenty times in isolation and prove the partitioned runner executes all 96 tests with the unchanged combined coverage result and no warning, retry, or residue. (FR-060, FR-063, FR-065, FR-068, FR-070)
- [ ] B496 Commit a replacement candidate and restart the clean-stack proof, exact repetitions, both complete gates, hosted checks, and every independent review from that SHA. (FR-002, FR-005, FR-007, FR-060, FR-063 through FR-069, FR-075, FR-078)

## Phase 64 — Focused Django tracer cycle 87 corrections

- [ ] B497 Remove duplicate pytest-cov instrumentation from every focused Django complete-gate check while retaining the dedicated all-module partitioned coverage authority. (FR-002, FR-060, FR-063, FR-068, FR-070)
- [ ] B498 Bind all focused Django commands to explicit empty addopts and a disabled coverage plugin so repository defaults cannot silently restore the unstable C tracer. (FR-002, FR-060, FR-063, FR-068, FR-070)
- [ ] B499 Prove the gate manifest enforces those boundaries and repeat the formerly failing site-content migration check twenty times in fresh uninstrumented processes. (FR-060, FR-063, FR-065, FR-068, FR-070)
- [ ] B500 Commit a replacement candidate and restart the clean-stack proof, exact repetitions, both complete gates, hosted checks, and every independent review from that SHA. (FR-002, FR-005, FR-007, FR-060, FR-063 through FR-069, FR-075, FR-078)
