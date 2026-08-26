# Feature Specification: Base2 Full-Stack Obsidian Preview

**Feature Branch**: `094-base2-full-preview`
**Created**: 2026-08-26
**Status**: In progress
**Input**: Deliver the canonical Base2 Obsidian experience and a disposable, secured, full-stack DigitalOcean preview whose public, API, and operator surfaces are honestly verified.

## Objective

Turn the generic Base2 foundation into its own canonical, reusable reference site and prove the complete stack in a bounded live preview. Preserve the minimal public canary as a separate mode. Never expose an operator surface merely to make a smoke test pass, and never call a hermetic screenshot proof of live visual parity.

## User Scenarios & Testing

### User Story 1 - Recognizable canonical Base2 experience (Priority: P1)

As the owner, I see the approved complete Obsidian design and Base2 identity instead of a fixture brand when the Base2 reference profile is selected.

**Independent Test**: Build `base2-obsidian`, load it at desktop/tablet/mobile sizes, and compare approved reference captures plus component and interaction states.

**Acceptance Scenarios**:

1. **Given** the canonical profile, **When** the homepage loads, **Then** Base2 identity, Obsidian tokens, full composition, and the exact source/profile marker are present.
2. **Given** any supported viewport, theme preference, reduced-motion preference, or keyboard-only navigation, **When** the owner uses the page, **Then** content remains usable and visually coherent.
3. **Given** a fixture profile, **When** it builds, **Then** it remains distinct and does not silently inherit Base2 branding.
4. **Given** the live preview, **When** a browser captures the page, **Then** it satisfies the same approved visual contract as the local build and reports no unexpected console or network failure.

### User Story 2 - Complete and honest preview surfaces (Priority: P1)

As the owner, I can visit the frontend, API entrypoint, health endpoint, Django admin, Swagger, Traefik, pgAdmin, and Flower at documented addresses and receive an intentional response.

**Independent Test**: Run the full-preview router in a production-like Compose stack and prove each route returns its specified public, redirect, authentication, authorization, or success response.

**Acceptance Scenarios**:

1. **Given** full-preview mode, **When** each exact hostname resolves, **Then** it reaches only its registered service.
2. **Given** `/api`, **When** requested anonymously, **Then** a safe service index is returned; `/api/health` remains machine-readable.
3. **Given** an unauthenticated or non-allowlisted operator request, **When** it reaches an operator hostname, **Then** it fails closed before application access.
4. **Given** valid preview credentials and an allowlisted owner address, **When** each operator address is opened, **Then** the intended UI or documented redirect loads.
5. **Given** minimal-canary mode, **When** an operator hostname is requested, **Then** it remains absent even if DNS exists.

### User Story 3 - Exact DNS and lease lifecycle (Priority: P1)

As the owner, I can create and destroy a preview without stale DNS, orphaned compute, premature DNS removal, or deletion of unrelated resources.

**Independent Test**: Exercise a provider fake and one separately approved live trial through create, bind, early owner teardown, expiry teardown, retry, partial failure, and reconciliation.

**Acceptance Scenarios**:

1. **Given** an approved preview, **When** DNS is created, **Then** every exact record ID, name, type, value, run ID, and expected resource identity is integrity-bound.
2. **Given** an early teardown without exact owner authority, **When** the lease is not expired, **Then** neither compute nor DNS is changed and the outcome is not reported as teardown success.
3. **Given** exact early-teardown authority or expiry, **When** cleanup runs, **Then** the bound Droplet is removed before its exact DNS records and zero owned resources remain.
4. **Given** changed, missing, duplicated, foreign, or ambiguous identity, **When** cleanup runs, **Then** it fails closed with actionable evidence.
5. **Given** a cleanup retry, **When** resources are already absent, **Then** it is a verified idempotent success.

### User Story 4 - Secure owner access (Priority: P1)

As the owner, I can access operator tools from my current network without making them generally public or embedding credentials in deployment artifacts.

**Independent Test**: Validate exact IPv4 `/32` and IPv6 `/128` admission, basic authentication, application authentication, secret resolution, rotation, denial, and redaction.

**Acceptance Scenarios**:

1. **Given** a private RFC1918 address, malformed CIDR, broad CIDR, or unverified public address, **When** preview configuration is rendered, **Then** protected exposure is rejected.
2. **Given** the verified current public address and owner-bound secret references, **When** configuration is rendered, **Then** raw credentials are present only in private runtime state.
3. **Given** a changed public address, **When** the bounded allowlist update is separately authorized, **Then** only the exact allowlist changes and access is re-probed.
4. **Given** logs, reports, HTTP responses, process listings, and repository history, **When** scanned, **Then** no raw secret or reusable credential is present.

### User Story 5 - Reproducible evidence and safe live readiness (Priority: P2)

As a maintainer, I can distinguish locally ready, provider-ready, live-ready, and live-verified states from evidence rather than assumptions.

**Independent Test**: Run the full local gate and a credential-free provider simulation, then verify the live launch remains blocked until exact authority and current inputs exist.

**Acceptance Scenarios**:

1. **Given** any failed test, unavailable required tool, stale generated artifact, visual mismatch, route mismatch, secret finding, or lifecycle discrepancy, **When** the gate runs, **Then** readiness is false.
2. **Given** all local checks pass, **When** no live authority exists, **Then** the result is `ready_for_live_approval` and performs no provider mutation.
3. **Given** a live trial, **When** outside-in verification finishes, **Then** a redacted evidence bundle binds source commit, archive digest, profile digest, host matrix, certificate mode, lease, DNS, and service health.

## Edge Cases

- The owner triggers teardown before expiry.
- Compute deletion succeeds but DNS deletion temporarily fails, or vice versa.
- A DNS record ID is reused or its value changes.
- The owner has IPv4, IPv6, carrier NAT, a VPN, or a changing public address.
- A stale subdomain points to a previous Droplet.
- A protected service is healthy internally but inaccessible through Traefik.
- Credentials resolve but contain invalid basic-auth syntax.
- The selected profile is omitted from a Docker build arg or generated runtime registry.
- A cached browser bundle displays a previous profile.
- Staging TLS produces a browser warning while routing is otherwise correct.
- The 2 GB preview approaches memory pressure during a parallel image build.
- A test is skipped or a scanner is unavailable.

## Functional Requirements

- **FR-001**: The repository MUST contain one canonical `base2-obsidian` site profile distinct from fixture brands.
- **FR-002**: The canonical profile MUST enable every currently implemented compatible Base2 core module and declare preview indexing disabled.
- **FR-003**: The selected profile MUST be propagated through generation, service-local copies, runtime selection, Docker build arguments, metadata, and evidence.
- **FR-004**: Unknown, absent, stale, or mismatched profiles MUST fail closed.
- **FR-005**: The Obsidian experience MUST have approved deterministic visual references for desktop, tablet, and mobile.
- **FR-006**: Visual validation MUST cover responsive layout, keyboard, focus, reduced motion, theme initialization, loading, empty, validation, authentication, and error states.
- **FR-007**: Live visual validation MUST inspect screenshot parity, browser console errors, failed requests, profile identity, and source identity.
- **FR-008**: Minimal-canary routing MUST remain root/API-only.
- **FR-009**: Full-preview routing MUST be a separate explicit mode and expose only the documented host/path matrix.
- **FR-010**: `/api` MUST return a stable, non-sensitive service index and `/api/health` MUST retain dependency health.
- **FR-011**: Swagger documentation MUST be disabled outside explicit full-preview/local policy and protected in a live full preview.
- **FR-012**: Django admin, Swagger, Traefik, pgAdmin, and Flower MUST require edge authentication and an exact owner allowlist in a live full preview.
- **FR-013**: Django admin and pgAdmin MUST additionally require their own application authentication.
- **FR-014**: PostgreSQL, Redis, Docker API, FastAPI, Django, pgAdmin, and workers MUST expose no direct public host ports.
- **FR-015**: Allowlist input MUST accept only verified public IPv4 `/32` or IPv6 `/128` entries, with an explicitly bounded list size.
- **FR-016**: Private, loopback, link-local, multicast, unspecified, documentation, and broader-than-host CIDRs MUST be rejected for live owner admission.
- **FR-017**: Preview credentials MUST be generated or resolved privately, separated per service, and never emitted raw.
- **FR-018**: The feature MUST preserve staging-only ACME and MUST NOT request production certificates.
- **FR-019**: DNS creation MUST be an exact transaction over the required hostnames with duplicate/stale detection and rollback evidence.
- **FR-020**: A preview lease MUST bind the exact Droplet plus every owned DNS record identity and integrity digest.
- **FR-021**: Early teardown MUST require exact owner authority and MUST not report `ok` when it performs no requested cleanup.
- **FR-022**: DNS deletion MUST occur only after compute is absent or a durable pending-cleanup state is recorded.
- **FR-023**: Cleanup MUST reject identity drift, ambiguity, foreign resources, and partial unverified state.
- **FR-024**: Cleanup and reconciliation MUST be idempotent and produce explicit mutation counts.
- **FR-025**: The supported preview entrypoint MUST preflight source, profile, DNS, allowlist, credentials, budget, size, region, certificate mode, and clean ownership state before mutation.
- **FR-026**: The preview MUST default to a 60-minute TTL, allow at most four hours, and expose its exact expiry.
- **FR-027**: The supported workflow MUST optimize a 2 GB Droplet through cached or bounded builds and fail visibly on resource exhaustion.
- **FR-028**: Every declared Compose service MUST become healthy before readiness can be true.
- **FR-029**: Outside-in probes MUST verify the complete anonymous, denied, authenticated, redirected, and successful route matrix.
- **FR-030**: Reports MUST redact secrets while binding source commit, archive digest, profile digest, service image identity, DNS identity, owner-CIDR digest, and lease identity.
- **FR-031**: Required tests and scanners MUST distinguish pass, fail, skipped, unavailable, and not-run; only pass may satisfy readiness.
- **FR-032**: Legacy DNS records MUST be inventoried and changed only through explicit exact-record migration or removal.
- **FR-033**: The live launch MUST remain a separately approved action after implementation and local readiness.
- **FR-034**: The temporary source branch used by a preview MUST be removable after exact-source bootstrap without affecting the running preview.
- **FR-035**: Replays MUST not create additional Droplets, records, credentials, or certificate requests.
- **FR-036**: All failures MUST produce actionable sanitized evidence and no silent suppression.

## Key Entities

- **Canonical Site Profile**: Integrity-bound Base2 brand, theme, modules, navigation, content policy, and preview policy.
- **Full Preview Policy**: Exact route matrix, certificate mode, protected surfaces, owner admission, TTL, and resource ceiling.
- **Owner Admission**: Verified host CIDRs and digests without embedding location history or credentials in public artifacts.
- **Preview Lease**: Exact source, provider resource, DNS records, expiry, state, and integrity digest.
- **DNS Record Binding**: Provider record ID plus exact domain, type, name, value, and ownership identity.
- **Live Evidence Bundle**: Redacted immutable proof for visual, route, security, health, cost, and teardown outcomes.

## Measurable Outcomes

- **SC-001**: Canonical Base2 visual tests pass at three viewport classes with zero unapproved screenshot differences.
- **SC-002**: All documented public and protected routes return their expected status both anonymously and with approved access.
- **SC-003**: All declared services are healthy and `/api/health` reports zero failed required checks.
- **SC-004**: Hostile allowlist, secret, DNS identity, lease, replay, and teardown matrices produce zero false-success results.
- **SC-005**: A complete create-to-destroy simulation ends with zero owned compute and DNS resources.
- **SC-006**: The final local gate reports zero failed, skipped, unavailable, or not-run required checks.
- **SC-007**: The separately approved live trial produces a complete evidence bundle and leaves zero resources after its review window.
- **SC-008**: Repository, build artifacts, reports, logs, and HTTP responses contain zero raw secret findings.
