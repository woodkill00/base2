# Feature Specification: Base2 Universal Website Foundation

**Feature Branch**: `093-base2-foundation-hardening`
**Created**: 2026-08-24
**Status**: In progress
**Input**: Harden Base2 into a secure, configuration-driven, fully tested foundation that can create many kinds of websites, while disposable DigitalOcean previews consume resources only while actively used.

## Objective

Produce one current-main Base2 foundation whose deployment, security, visual behavior, content, accounts, operations, optional capabilities, and preview lifecycle are explicit, reusable, observable, and safe by default. The existing volcanic/obsidian visual work is a design source only; it must be ported onto current `main`, never promoted from its stale branch.

## Scope and delivery rule

This umbrella feature is delivered in independently releasable slices. A capability is not available merely because a route, button, workflow, or configuration key exists: it must have a real implementation, a documented disabled state, or be absent. No check may report success after suppressing a failure.

The baseline includes the hardened core, manifest-driven site composition, essential public pages and forms, accounts/administration, a module contract, representative feature packs, and the disposable preview factory. Future packs use the same contract and do not require forking the foundation.

## User Scenarios & Testing

### User Story 1 - Trustworthy clone-to-preview path (Priority: P1)

As an owner, I can configure Base2, launch a production-like preview through the supported orchestrator, verify it, and destroy it without hidden steps or orphaned resources.

**Independent Test**: From a clean checkout and fixture credentials, deploy one canary, validate public and internal health contracts, destroy it, and prove zero leased resources or stale DNS remain.

**Acceptance Scenarios**:

1. **Given** valid configuration, **When** the supported deploy entrypoint runs, **Then** every service becomes healthy and a complete redacted evidence bundle is produced.
2. **Given** any failed stage, **When** cleanup runs or the lease expires, **Then** only resources owned by that run are removed and the failure is visible.
3. **Given** no active lease, **When** idle policy evaluates the preview, **Then** billable resources are destroyed or explicitly retained by policy.

### User Story 2 - Honest quality and security gates (Priority: P1)

As a maintainer, I can trust a green branch because required tests, coverage, dependency audits, security scans, migrations, and production-like smoke checks cannot silently pass known failures.

**Independent Test**: Inject one representative failure into each gate family and prove the gate fails closed with an actionable artifact; restore it and prove the complete gate is green.

**Acceptance Scenarios**:

1. **Given** a vulnerable dependency, failed scanner, coverage regression, or broken test, **When** CI runs, **Then** the required check fails.
2. **Given** a required startup import failure, **When** the service boots, **Then** startup fails with a redacted diagnostic instead of omitting routes or flags.
3. **Given** the complete matrix, **When** it finishes, **Then** its summary distinguishes passed, failed, skipped, unavailable, and not-run checks.

### User Story 3 - Configuration-driven branded site (Priority: P1)

As a site creator, I can create a distinct website by editing a validated manifest and content records rather than changing foundation source code.

**Independent Test**: Build two fixture brands from the same commit and confirm names, domains, navigation, theme, metadata, legal links, enabled modules, and content differ with no leakage.

**Acceptance Scenarios**:

1. **Given** a valid manifest, **When** the site starts, **Then** branding, navigation, feature flags, domains, metadata, and policy links come from it.
2. **Given** an invalid manifest, **When** validation runs, **Then** startup and deployment fail before public exposure.
3. **Given** a disabled module, **When** its route is requested, **Then** it is unavailable and the UI does not advertise it.

### User Story 4 - Complete public website experience (Priority: P1)

As a visitor, I can use a polished, accessible, responsive site with working navigation, content, search, contact, legal, error, and consent experiences.

**Independent Test**: Exercise keyboard, screen-reader, mobile, desktop, reduced-motion, dark/light, form, search, offline-error, and 404 journeys against a built preview.

**Acceptance Scenarios**:

1. **Given** any visible control, **When** activated, **Then** it performs a real documented action or is clearly disabled with a reason.
2. **Given** a valid contact submission, **When** abuse controls pass, **Then** it is durably recorded and delivered or queued with visible status.
3. **Given** an unknown URL, **When** opened, **Then** a branded accessible 404 appears with a recovery path.

### User Story 5 - Secure accounts and administration (Priority: P2)

As an organization owner, I can manage users, invitations, roles, sessions, credentials, content, audit history, and tenant settings without exposing another tenant or public admin surfaces.

**Independent Test**: Create two tenants and run positive and hostile account/admin journeys, proving authorization, isolation, revocation, auditability, and recovery.

### User Story 6 - Reusable feature packs (Priority: P2)

As a site creator, I can enable reviewed feature packs without changing the Base2 core or unintentionally exposing data, routes, jobs, or navigation.

**Independent Test**: Enable each representative pack in a fixture site, validate model-to-API-to-React behavior and accessibility, then disable it and prove clean removal from runtime surfaces.

**Representative packs**: portfolio, blog/news, documentation, forms, gallery/media, events, booking, memberships/subscriptions, commerce/catalog, community, support, and marketplace/listings.

### User Story 7 - Visual system port and regression safety (Priority: P2)

As a visitor, I receive the refined volcanic/obsidian design on the current foundation with consistent tokens, components, states, and accessibility.

**Independent Test**: Render the approved route/state/viewport matrix and compare deterministic screenshots plus semantic accessibility results against reviewed baselines.

### User Story 8 - Production operations and recovery (Priority: P2)

As an operator, I can observe, back up, restore, update, roll back, and diagnose a site using supported entrypoints and integrity-bound evidence.

**Independent Test**: Run bounded fault, backup/restore, rollback, certificate, alert, and recovery drills in an isolated preview and verify RPO/RTO evidence.

### User Story 9 - Automated website factory (Priority: P3)

As an owner, I can generate a new site repository from Base2 using a validated profile, without inheriting secrets, runtime state, stale branding, or unsafe deployment authority.

**Independent Test**: Generate multiple site types, run their complete local gates, create and destroy isolated previews, and compare generated manifests and module inventories.

### User Story 10 - Extensible future capability (Priority: P3)

As a maintainer, I can add a new module through a versioned contract, migrations, tests, docs, and compatibility checks without editing unrelated packs.

**Independent Test**: Build a fixture module using only the public module interface, validate installation/removal/upgrade, and prove a bad module fails before deployment.

## Edge Cases

- Connectivity is lost after provider creation but before the local receipt is written.
- A stale cleanup job sees a replacement resource with a similar name.
- DNS points at an old preview while the new preview is unhealthy.
- ACME storage is absent, group-readable, or owned by the wrong UID.
- An image lacks the binary named by its health check.
- Environment values contain whitespace, quotes, CRLF, or inline comments.
- A scanner is unavailable, times out, or emits malformed output.
- A module has missing migrations, conflicting routes, or cyclic dependencies.
- Search, cache, jobs, uploads, or admin requests attempt cross-tenant access.
- Form submissions are replayed, spammed, oversized, or hostile.
- Visual evidence varies because of animation, fonts, time, locale, or network content.
- Backup succeeds but restore validation or migration compatibility fails.
- Lease renewal races with teardown or provider quota blocks reconciliation.
- Child repository creation is interrupted halfway through transformation.

## Requirements

### Deployment, cost, and evidence

- **FR-001**: Production-like deployment MUST use `digital_ocean/scripts/python/orchestrate_deploy.py` as the sole orchestration implementation.
- **FR-002**: Deployment MUST validate and normalize configuration before provider mutation.
- **FR-003**: Container builds MUST work with the supported builder without unsupported heredoc behavior.
- **FR-004**: Health checks MUST use installed binaries and test meaningful readiness.
- **FR-005**: TLS state MUST have least-privilege ownership/mode before Traefik starts.
- **FR-006**: Every provider resource MUST carry unique ownership and be recorded in an atomic lease receipt.
- **FR-007**: Cleanup MUST compare provider identity, ownership tags, and receipt before deletion and fail closed on ambiguity.
- **FR-008**: Preview TTL, renewal, idle teardown, manual destroy, interrupted-create recovery, and zero-resource verification MUST be supported.
- **FR-009**: DNS changes MUST be health-gated, record prior state, and be restored or removed on rollback/teardown.
- **FR-010**: Deployment/teardown MUST produce redacted, integrity-bound evidence including cost metadata.

### Quality and security gates

- **FR-011**: Required CI MUST cover repository guards, frontend, API, Django, contracts, integration, E2E, accessibility, visual, performance, deployment canary, and security as applicable.
- **FR-012**: Required checks MUST NOT suppress policy failures with soft-failure controls or unconditional success coercion.
- **FR-013**: Summaries MUST distinguish failure, skip, unavailable, and not-run from success.
- **FR-014**: Fixtures MUST be self-contained and not depend on untracked/generated files or PowerShell on Linux.
- **FR-015**: Coverage MUST apply to the whole owned surface with ratcheted floors and no misleading subset labels.
- **FR-016**: Dependency vulnerabilities MUST meet a severity/SLA policy and block at its threshold.
- **FR-017**: Secret, SBOM, provenance, image, dependency, static, dynamic, and IaC scans MUST create machine-readable artifacts and fail by policy.
- **FR-018**: Actions and deployable images MUST be pinned immutably with reviewed update automation.
- **FR-019**: Required route, flag, migration, or dependency failures MUST fail startup; optional degradation MUST be typed and visible.
- **FR-020**: Errors MUST carry request/run identity and redact secrets and personal data.

### Site manifest and public experience

- **FR-021**: A versioned site manifest MUST define identity, domains, theme, navigation, SEO, legal links, locales, consent/analytics, contact, modules, and operations.
- **FR-022**: Manifest validation MUST reject unknown keys, incompatible modules, unsafe URLs, duplicate routes, and missing values.
- **FR-023**: One commit MUST render multiple fixture brands without edits or leakage.
- **FR-024**: Core pages MUST include home, about, contact, privacy, terms, accessibility, search, sign-in, account, and branded 404/500 when applicable.
- **FR-025**: Every visible control/link MUST have tested behavior, an explicit disabled explanation, or be absent.
- **FR-026**: Content MUST support draft/published/scheduled/archive, metadata, revisions, preview, redirects, and sitemap state.
- **FR-027**: Search MUST index only authorized published content with tenant boundaries and freshness status.
- **FR-028**: Forms MUST provide validation, CSRF, rate limits, bot controls, durable outbox status, retention, and consent evidence.
- **FR-029**: Media MUST validate type/size, generate responsive variants, track ownership/attribution, and prevent executable delivery.
- **FR-030**: Public pages MUST meet WCAG 2.2 AA, responsive, keyboard, screen-reader, reduced-motion, contrast, focus, and localization requirements.
- **FR-031**: SEO MUST provide canonical URLs, robots, sitemap, OpenGraph, structured data, and redirect validation without exposing private content.
- **FR-032**: Analytics MUST default off and nonessential trackers may not load before applicable consent.

### Accounts, administration, and isolation

- **FR-033**: Accounts MUST support secure signup/login/logout, verification, reset, session inventory/revocation, and reauthentication.
- **FR-034**: MFA MUST support TOTP/recovery codes; WebAuthn/passkeys MUST be a versioned optional method.
- **FR-035**: Organizations, memberships, invitations, roles, and permissions MUST use deny-by-default server enforcement.
- **FR-036**: Tenant isolation MUST cover models, services, APIs, caches, jobs, search, and tests.
- **FR-037**: Admin surfaces MUST be private by default and least-privilege.
- **FR-038**: Security-sensitive actions MUST produce append-only redacted audit records.
- **FR-039**: API/external credentials MUST be scoped, protected, revocable, and auditable, and never returned after creation.
- **FR-040**: Export, correction, retention, and deletion workflows MUST be explicit and integrity tested.

### Module system and representative packs

- **FR-041**: Packs MUST declare a versioned manifest for models, migrations, routes, navigation, permissions, jobs, settings, health, lifecycle, and compatibility.
- **FR-042**: Module enable, disable, upgrade, export, and removal MUST be deterministic and validated before deployment.
- **FR-043**: Persistent packs MUST implement Django models first, FastAPI mirror second, React integration third, with independent tests/docs.
- **FR-044**: Portfolio, blog/news, docs, forms, gallery/media, events, and booking packs MUST be delivered as reference content capabilities.
- **FR-045**: Membership/subscription, commerce/catalog, community, support, and marketplace/listing packs MUST remain behind explicit activation/provider boundaries.
- **FR-046**: Payment behavior MUST default to sandbox/disabled and require separate credentials, webhook verification, and production activation.
- **FR-047**: Installation MUST NOT grant arbitrary code, credentials, network, admin, publish, payment, or deployment authority.

### Visual system, operations, and factory

- **FR-048**: The visual design MUST be ported as reviewed commits onto current main; the stale branch MUST never become the merge base.
- **FR-049**: The design system MUST define tokens, themes, components, layouts, states, responsive behavior, motion, and accessibility contracts.
- **FR-050**: Visual tests MUST cover route/state/viewport/theme/locale/reduced-motion/loading/empty/error/permission matrices deterministically.
- **FR-051**: Observability MUST include structured logs, metrics, traces, health/readiness, alerts, SLOs, and safe diagnostics.
- **FR-052**: Backup/restore, migration, rollback, DR, and certificate renewal MUST have bounded automated drills and measured RPO/RTO.
- **FR-053**: Deployments MUST support immutable identity, preflight, migration safety, health-gated traffic, rollback, and observation.
- **FR-054**: The factory MUST export an immutable commit/profile without `.git`, secrets, state, logs, caches, or provider receipts.
- **FR-055**: Generated repos MUST receive independent identity, manifest, secret references, CI, docs, and upgrade metadata.
- **FR-056**: Factory outputs MUST pass the same applicable gate and an isolated create/deploy/verify/destroy trial.
- **FR-057**: Upgrades MUST provide compatibility, migration preview, rollback, and provenance.
- **FR-058**: Destructive, public, billable, credential, DNS, payment, or production actions MUST require explicit scoped authorization and rollback evidence.

## Key Entities

- **SiteManifest**: Versioned desired site identity, composition, policy, and operations.
- **ModuleDefinition/Installation**: Pack declaration and site-specific lifecycle.
- **ContentRecord/Revision**: Tenant-owned versioned publication state.
- **MediaAsset**: Validated media, variants, ownership, retention, and integrity.
- **Organization/Membership/Role**: Tenant and authorization relationships.
- **AuditEvent**: Append-only security/administrative outcome evidence.
- **PreviewLease**: Exact provider resources, ownership, TTL, state, and teardown receipt.
- **DeploymentEvidence**: Commit/manifest-bound stage, test, health, cost, and artifact results.
- **GeneratedSiteProvenance**: Source commit, generator, profile, modules, and upgrade lineage.

## Success Criteria

- **SC-001**: Clean supported environments reach a healthy production-like stack with no hidden repair.
- **SC-002**: Three consecutive canaries deploy and destroy with zero orphaned owned resources or stale managed DNS.
- **SC-003**: Injected failures in every required gate family block progression and produce diagnostics.
- **SC-004**: Whole-surface coverage meets ratcheted policy; changed lines are covered or explicitly reviewed; subset coverage is never mislabeled.
- **SC-005**: Two fixture sites from one commit pass content, route, SEO, accessibility, and isolation assertions.
- **SC-006**: 100% of visible controls have validated behavior, disabled rationale, or are absent.
- **SC-007**: The WCAG 2.2 AA matrix has zero serious/critical automated findings and all manual checks pass.
- **SC-008**: Supported modules pass lifecycle and authorization/isolation contract tests.
- **SC-009**: Three backup/restore and rollback drills meet documented RPO/RTO.
- **SC-010**: Inactive previews consume zero Droplet runtime after TTL plus bounded cleanup.
- **SC-011**: A generated child repo passes its applicable gate and disposable preview trial without core edits.
- **SC-012**: Production audit has zero unaccepted critical/high findings; exceptions have owner, mitigation, and expiry.

## Assumptions

- DigitalOcean is the first preview provider; contracts remain provider-neutral.
- Preview compute is destroyed by default when inactive.
- PostgreSQL/Django remain canonical, FastAPI mirrors contracts, React is untrusted.
- “100% testing” means 100% of declared requirements, routes, controls, states, boundaries, and known failure classes map to evidence; it cannot prove unknown defects impossible.

## Non-goals

- Building a specific customer site.
- Enabling production payments, public production DNS, or permanent billable infrastructure without separate authorization.
- Promising every conceivable vertical; the module contract is the extension point.
- Downloading or executing third-party untrusted content.
