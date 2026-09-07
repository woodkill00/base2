# Specification

## Goal

Make Base2 a secure, observable, recoverable, scalable, and reusable production
website platform. Every generated site must have a consistent operational
contract, while optional product capabilities remain closed, tenant-scoped, and
disabled when not selected.

## User outcomes

1. A site owner can launch an exact reviewed release, understand its health,
   recover it safely, and control its domain without becoming an infrastructure
   expert.
2. A site member receives accessible, secure, responsive, and predictable
   account, content, media, search, and notification experiences.
3. An operator can see incidents and resource pressure before users must report
   them, investigate from sanitized evidence, and use bounded recovery actions.
4. A developer can generate, test, preview, promote, roll back, and extend a
   Base2 site through documented single entrypoints and closed contracts.
5. A tenant cannot discover, consume, mutate, export, or influence another
   tenant's identities, data, jobs, media, domains, telemetry, quotas, or keys.

## Functional requirements

### Environments, releases, and deployment

- **FR-001** Base2 MUST define explicit development, test, preview, staging,
  and production profiles whose differences are machine-validated.
- **FR-002** A release MUST identify one clean source commit, immutable image
  digests, migrations, configuration schema, SBOM, provenance, and checksums.
- **FR-003** Staging-to-production promotion MUST reuse the reviewed artifacts;
  rebuilding a different artifact is forbidden.
- **FR-004** Deployment MUST be serialized, resumable, replay-safe, and reject
  stale approvals, stale source, concurrent mutation, or partial evidence.
- **FR-005** A canary or blue/green strategy MUST verify health and synthetic
  journeys before moving traffic.
- **FR-006** Rollback MUST restore the last compatible verified release without
  deleting durable tenant data or reversing an unsafe schema transition.
- **FR-007** Publication, merge, live deployment, spending, DNS mutation,
  production certificate issuance, destructive migration, and provider teardown
  MUST remain separately and exactly approved.
- **FR-008** Every release operation MUST produce sanitized, integrity-bound,
  exact-source evidence and an honest terminal or pending state.

### Native observability and incidents

- **FR-009** Base2 MUST provide a private native operations center for every
  managed site, environment, service, dependency, and release.
- **FR-010** Health collection MUST cover public routes, APIs, database, workers,
  queues, object storage, DNS, certificates, email, schedules, and capacity.
- **FR-011** Synthetic checks MUST exercise representative anonymous, member,
  editor, administrator, form, upload, search, and logout journeys safely.
- **FR-012** Source-bound visual checks MUST detect material regressions at the
  supported viewport, theme, zoom, direction, and contrast profiles.
- **FR-013** Each service MUST declare measurable indicators, objectives,
  latency/error budgets, freshness, and capacity thresholds.
- **FR-014** Incidents MUST support deduplication, severity, timeline,
  acknowledgement, ownership, resolution, recurrence, and post-incident review.
- **FR-015** Operator alerts MUST be sanitized, rate-bounded, delivery-observed,
  and actionable through expiring least-authority controls; Discord is an
  operator channel, not the sole source of truth.
- **FR-016** Missing, delayed, stuck, flapping, or failed monitoring and alerting
  MUST itself become visible without creating an unbounded alert loop.

### Data durability and tenant isolation

- **FR-017** Production database usage MUST have measured connection pooling,
  bounded concurrency, statement limits, and pressure visibility.
- **FR-018** Schema changes MUST prove forward compatibility, mixed-version
  operation, zero- or bounded-downtime behavior, and a safe rollback strategy.
- **FR-019** Tenant isolation MUST be enforced at database, repository, API,
  job, export, search, media, audit, cache, and observability boundaries.
- **FR-020** Automated backups MUST be encrypted, integrity-bound, inventoried,
  retention-governed, and isolated from application credentials.
- **FR-021** Point-in-time recovery MUST be supported where the selected
  production database provides it, with an explicit honest fallback otherwise.
- **FR-022** Restore drills MUST use isolated targets, reject live targets, and
  validate relational, object, search, configuration, and tenant consistency.
- **FR-023** Retention, archival, legal hold, anonymization, export, and erasure
  MUST be explicit, auditable, replay-safe, and tenant-scoped.
- **FR-024** Integrity, capacity, slow-query, index, migration, backup, and
  restore failures MUST be observable and actionable.

### Edge, domains, certificates, and privileged surfaces

- **FR-025** Custom-domain onboarding MUST verify ownership, prevent tenant
  takeover, and provide deterministic canonical and redirect behavior.
- **FR-026** Certificate issuance and renewal MUST be environment-scoped,
  observable, reversible, and incapable of issuing production certificates
  from preview or test profiles.
- **FR-027** Static and media delivery MUST support cache-safe CDN/object
  boundaries without caching private, tenant-sensitive, or stale authorization.
- **FR-028** The edge MUST enforce bounded request size, timeouts, headers,
  rate/concurrency limits, abuse controls, and trusted-proxy semantics.
- **FR-029** Django admin, pgAdmin, Traefik, diagnostics, metrics, and API schema
  surfaces MUST be private by default and separately authorized when exposed.
- **FR-030** DNS, IPv4/IPv6, canonical host, subdomain, redirect, and certificate
  behavior MUST be tested without assuming one provider or address.

### Secrets, audit, and recovery authority

- **FR-031** Credentials MUST be resolved just in time from approved secret
  references and never copied into source, images, logs, evidence, or browsers.
- **FR-032** Every credential class MUST have tested expiry, rotation,
  revocation, and recovery procedures using least-privilege identities.
- **FR-033** Break-glass access MUST be time-bounded, independently visible,
  minimally scoped, fully audited, and require follow-up review.
- **FR-034** Security and operator audit records MUST be redacted,
  integrity-bound, tenant-aware, access-controlled, and retention-bounded.

### Jobs, schedules, email, and notifications

- **FR-035** Background work MUST use a standard durable job model with tenant,
  owner, payload schema, generation, state, attempt, lease, and idempotency.
- **FR-036** Retries MUST be bounded with backoff and jitter; duplicate delivery,
  stale leases, restart, and network loss MUST not duplicate side effects.
- **FR-037** Terminal failures MUST enter a visible dead-letter/review flow with
  safe replay, cancellation, acknowledgement, and exact receipts.
- **FR-038** Scheduled work MUST expose next/last run, lateness, missed runs,
  timezone/DST behavior, resource admission, and catch-up policy.
- **FR-039** Transactional email MUST support verified sender configuration,
  delivery/bounce/suppression evidence, accessible templates, and safe links.
- **FR-040** Users MUST have tenant-aware in-app and email notification history,
  preferences, deduplication, urgency, quiet-time, and unsubscribe behavior.

### Tenant, identity, settings, and authorization

- **FR-041** Tenant/site lifecycle MUST cover provision, configure, suspend,
  archive, restore, transfer, export, and separately confirmed deletion.
- **FR-042** Per-tenant quotas MUST cover users, storage, media, API, jobs,
  email, search, and provider cost without revealing other tenants.
- **FR-043** Identity MUST support verified recovery plus optional MFA and
  passkeys without weakening existing OAuth and session protections.
- **FR-044** Users MUST see and revoke active sessions/devices and receive
  bounded alerts for relevant security events.
- **FR-045** Roles and policy MUST be explicit and consistently enforced by
  Django, FastAPI, React affordances, workers, exports, and administration.
- **FR-046** Account and site settings MUST distinguish scope, support search,
  accessible state, unsaved-change protection, consequence copy, and history
  for sensitive changes.

### Universal product capabilities

- **FR-047** Optional tenant-scoped search MUST index only authorized content,
  data, media, members, and modules and support bounded filters and recovery.
- **FR-048** Editorial workflow MUST support drafts, revisions, scheduling,
  preview, review, publication, archive, conflict handling, and rollback.
- **FR-049** Media storage MUST support production object storage, safe CDN
  delivery, lifecycle controls, resumable upload, and reference-aware deletion.
- **FR-050** Generated sites MUST include accessible navigation, errors, legal
  pages, privacy/consent controls, metadata, sitemap, robots, structured data,
  forms, spam controls, print, and share behavior.
- **FR-051** An optional visual builder MUST compose constrained accessible
  components rather than permitting arbitrary executable markup or styles.
- **FR-052** Versioned design tokens and themes MUST produce deterministic,
  responsive, accessible output with upgrade and rollback behavior.
- **FR-053** Every supported site archetype MUST declare modules, routes, roles,
  seed data, tests, capacity assumptions, and estimated provider cost.
- **FR-054** Modules MUST support dependency resolution, compatibility,
  versioned migration, enable/disable, upgrade/downgrade, data-preserving
  uninstall, permissions, observability, backup, resource, and test contracts.
- **FR-055** Integrations MUST use scoped expiring keys or OAuth, signed
  replay-safe webhooks, quotas, retries, dead letters, audit, and clear removal.
- **FR-056** Commerce MUST remain optional and disabled by default; when enabled,
  payment state, webhooks, refunds, subscriptions, taxes, and audit MUST be
  provider-abstracted and must not store prohibited payment secrets.

### Performance, resilience, governance, and developer experience

- **FR-057** Base2 MUST enforce budgets for page load, API latency, queries,
  bundles, CPU, memory, storage, and background throughput.
- **FR-058** Capacity plans MUST define scaling thresholds, degradation,
  resource ceilings, cost estimates, and automatic ephemeral teardown.
- **FR-059** Releases MUST use pinned dependencies and images, SBOMs,
  vulnerability/license/secret scans, signatures, provenance, and policy gates.
- **FR-060** Bounded fault drills MUST cover application, worker, database,
  storage, DNS, certificate, provider, and notification failures with measured
  recovery objectives.
- **FR-061** Base2 MUST support a documented data inventory, classification,
  consent, retention, accessibility, vendor, incident, and regional-processing
  control plane without claiming certifications it has not earned.
- **FR-062** One documented local and CI golden path MUST cover setup, generate,
  migrate, test, preview, release, recover, and roll back with shell parity and
  no hidden workstation state.
- **FR-063** Every workstream MUST have unit, integration, contract, migration,
  API, frontend, end-to-end, and negative tests appropriate to its boundary.
- **FR-064** User-facing work MUST have keyboard, screen-reader, zoom, reduced
  motion, contrast, RTL, responsive, cross-browser, interaction, and visual
  evidence tied to the exact source.
- **FR-065** Security testing MUST cover authorization, tenant escape, hostile
  input, SSRF, injection, replay, race, exhaustion, supply chain, and secret leak.
- **FR-066** Durable-state work MUST prove backup, isolated restore, forward
  migration, compatible rollback, and interrupted-operation recovery.
- **FR-067** Release candidates MUST pass an exact-source, production-like,
  ephemeral canary and verified teardown before live production approval.
- **FR-068** Evidence MUST distinguish tested guarantees, pending evidence,
  residual risk, and unknown-risk limits; no finite suite may claim perfection.
- **FR-069** Repository code, tests, or an approved workstream MUST NOT infer
  credential, network, publication, merge, deployment, spending, DNS, provider,
  destructive, or production authority.
- **FR-070** Failures MUST be explicit and diagnosable; degraded or unavailable
  dependencies MUST never silently convert an incomplete operation into success.
- **FR-071** Telemetry MUST minimize sensitive data, enforce tenant boundaries,
  redact values, bound cardinality and retention, and support access/deletion.
- **FR-072** Optional capabilities MUST be disabled by default and leave no
  route, navigation, worker, schedule, storage allocation, or authority residue.
- **FR-073** Sensitive data MUST use verified encryption in transit and at rest
  with explicit key identity, rotation, revocation, backup, and recovery behavior.
- **FR-074** Service networks and outbound access MUST be least-privilege,
  deny-by-default where feasible, and resistant to SSRF, metadata access, DNS
  rebinding, lateral movement, and unobserved exfiltration.
- **FR-075** Generated sites MUST support locale, timezone, translation,
  pluralization, formatting, direction, fallback, and user-versus-site preference
  without corrupting schedules, URLs, search, email, or stored canonical data.
- **FR-076** Public APIs and events MUST have versioning, compatibility,
  deprecation, migration, and consumer-contract policies with measurable usage.
- **FR-077** Feature flags MUST be typed, scoped, expiring, observable,
  reversible, and incapable of bypassing authorization or leaving disabled
  routes, jobs, data allocation, or configuration residue.
- **FR-078** Protected-branch, required-check, code-owner, workflow-permission,
  dependency-update, and release-signing policy MUST be machine verified and
  must fail closed on drift.

## Non-functional requirements

- Critical authorization and tenant boundaries fail closed.
- All externally visible state transitions are idempotent or reject replay.
- Public interfaces are versioned and migrations remain compatibility aware.
- Every resource consumer has an explicit finite size, time, retry, concurrency,
  retention, and cost boundary.
- Accessibility targets WCAG 2.2 AA behavior without claiming certification
  solely from automation.
- Production-like tests use synthetic data and staging certificates only.

## Authority boundary

This feature authorizes repository specification and, after implementation is
separately requested, repository code and local tests. It does not authorize
publication, pull-request creation, merge, live deployment, paid provider use,
credential access, DNS mutation, production certificate issuance, destructive
data action, tenant communication, or provider teardown. Those operations must
each use a separate exact-scope approval and verified evidence.

## Non-goals

- Claiming zero unknown defects or automatic regulatory certification.
- Making every optional module mandatory for every site.
- Exposing infrastructure consoles as ordinary public product surfaces.
- Creating an unrestricted page builder, plugin runtime, workflow command
  runner, or third-party code execution path.
- Requiring a third-party monitoring SaaS for the native baseline.
- Permanently provisioning DigitalOcean resources during specification work.
