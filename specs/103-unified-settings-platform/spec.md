# Feature Specification: Unified Account and Settings Platform

**Feature Branch**: `vscode-codex/103-unified-settings-platform`
**Created**: 2026-08-30
**Status**: Draft
**Input**: Build a reusable, secure, accessible, and visually assured settings system for every Base2-generated website.

## User Scenarios & Testing

### User Story 1 - Find and understand settings (Priority: P1)

An authenticated user opens one coherent settings center, searches or browses stable categories, sees current values and recommended actions, and can return through durable deep links on phone, tablet, or desktop.

**Independent Test**: Render the overview with representative capabilities and verify search, keyboard navigation, responsive list-detail behavior, current-value summaries, and old-route redirects.

**Acceptance Scenarios**:

1. **Given** a generated site with accounts enabled, **When** the user opens `/settings`, **Then** the overview exposes only supported categories with plain-language summaries.
2. **Given** at least fifteen searchable controls, **When** the user searches by label, synonym, or description, **Then** matching settings are reachable without losing keyboard focus.
3. **Given** a narrow or zoomed viewport, **When** a category is opened, **Then** navigation and content remain readable, operable, and free of horizontal page overflow.

### User Story 2 - Manage profile and preferences safely (Priority: P1)

A user manages profile, language, region, appearance, accessibility, and notification preferences with predictable save behavior and visible recovery from errors.

**Independent Test**: Update each typed preference, simulate conflicts and network failures, reload, and verify persisted or rolled-back state without exposing unsupported keys.

### User Story 3 - Understand and secure the account (Priority: P1)

A user reviews account health, MFA, recovery codes, sign-in methods, security events, devices, and sessions, then revokes unfamiliar access through recently authenticated operations.

**Independent Test**: Exercise session inventory/revocation, TOTP enrollment and recovery replacement, expired reauthentication, and unavailable passkey capability without leaking secrets.

### User Story 4 - Control privacy and data (Priority: P1)

A user can understand consent, inspect privacy-operation status, export or correct data, deactivate an account, and enter a separated deletion flow with explicit consequences.

**Independent Test**: Run queued, deferred, completed, failed, replayed, and integrity-failure paths for export/correction/deletion with owner and cross-tenant identities.

### User Story 5 - Use capability-specific settings (Priority: P2)

A generated Base2 site enables optional organization, developer, commerce, billing, scheduling, or social settings through a closed manifest contract; disabled capabilities do not render and cannot be invoked.

**Independent Test**: Generate every supported profile, compare navigation and API capability output, and directly request disabled routes to prove fail-closed behavior.

### User Story 6 - Receive trustworthy feedback (Priority: P1)

Every save, failure, security action, background operation, and unavailable dependency produces an accessible state message, durable audit evidence where sensitive, and actionable diagnostics without secrets.

**Independent Test**: Inject validation, authorization, network, database, worker, integrity, and stale-version failures and verify typed UI and server evidence.

### Edge Cases

- Capability changes while a settings route is open.
- Two tabs or devices update the same preference version.
- System theme, contrast, language, or time zone changes during a session.
- Unsupported locale, time zone, notification channel, or manifest field.
- External avatar URL attempts unsafe schemes, credentials, local addresses, or tracking parameters.
- Reauthentication expires between confirmation and mutation.
- A worker is unavailable after a durable privacy operation is queued.
- An organization owner attempts to remove the final owner or themselves unsafely.
- Long translations, 200% text, 400% zoom, reduced motion, touch, keyboard-only use, and screen-reader announcements.
- A settings API returns malformed, oversized, or unexpected fields.

## Requirements

### Functional Requirements

- **FR-001**: Base2 MUST provide one unified settings shell with overview, stable category routes, search, breadcrumbs, and responsive list-detail navigation.
- **FR-002**: Legacy `/account` behavior MUST redirect or deep-link without breaking bookmarked workflows.
- **FR-003**: Category visibility MUST derive from a closed, versioned capability contract shared by generator, API, and client.
- **FR-004**: Disabled or absent capabilities MUST expose no working navigation or mutation surface.
- **FR-005**: Preferences MUST use typed allowlisted fields, bounded values, explicit defaults, and schema versions; arbitrary user-supplied keys are forbidden.
- **FR-006**: Preference updates MUST use optimistic concurrency and return a typed conflict rather than overwrite newer state.
- **FR-007**: Multi-field forms MUST use explicit save; reversible single-setting controls MAY save immediately with visible rollback on failure.
- **FR-008**: The platform MUST support profile, appearance, accessibility, language, region, time zone, week start, and notification preferences.
- **FR-009**: Security settings MUST expose supported authenticators, recovery codes, sessions/devices, sign-in methods, and recent security events.
- **FR-010**: Sensitive security, privacy, ownership, credential, and destructive operations MUST require recent authentication.
- **FR-011**: Session revocation MUST distinguish the current session, support one-session and other-session revocation, and prevent cross-user access.
- **FR-012**: Recovery secrets MUST be shown once, excluded from logs/screenshots, and never returned by later reads.
- **FR-013**: Passkeys MUST remain visibly unavailable until a complete versioned WebAuthn ceremony is enabled; capability flags cannot claim unimplemented behavior.
- **FR-014**: Privacy settings MUST expose consent and the existing durable export, correction, and deletion workflows with status history.
- **FR-015**: Deactivation and permanent deletion MUST be separate, consequence-rich flows with deliberate confirmation and safe cancellation boundaries.
- **FR-016**: Notification preferences MUST distinguish mandatory security/transactional delivery from optional product/marketing delivery.
- **FR-017**: Every mutation MUST return a typed success or error result suitable for accessible feedback and diagnostics.
- **FR-018**: Sensitive changes MUST create redacted append-only audit events and appropriate security notifications.
- **FR-019**: Avatar handling MUST reject unsafe schemes and credentials; the server MUST never fetch arbitrary user-provided URLs.
- **FR-020**: Settings MUST respect system color scheme, contrast, reduced motion, and language by default without duplicating unnecessary system controls.
- **FR-021**: Settings MUST meet WCAG 2.2 AA and the declared Base2 browser, input, zoom, and responsive contracts.
- **FR-022**: Search MUST index only safe static metadata, support labels/synonyms/descriptions, and never send queries to an external provider.
- **FR-023**: Authentication material and sensitive data MUST never be stored in browser local or session storage by this feature.
- **FR-024**: Cookie mutations MUST retain HTTPS, CSRF, Secure, HttpOnly, SameSite, and narrow-scope protections.
- **FR-025**: Optional organization and developer settings MUST preserve tenant, role, final-owner, scope, and recent-auth boundaries.
- **FR-026**: All background operations MUST be durable, replay-safe, observable, bounded, and explicit when deferred.
- **FR-027**: The old fragmented settings UI MUST be removed only after route, data, and test parity is proven.
- **FR-028**: Every generated Base2 profile MUST pass capability, build, interaction, accessibility, and visual contract tests.
- **FR-029**: Authenticated visual baselines MUST cover overview, profile, security, privacy, notifications, appearance, locale, error, loading, empty, confirmation, and destructive states.
- **FR-030**: Visual evidence MUST cover compact phone, DPR3 phone, short landscape, tablet, desktop, ultrawide, 200% text, 400% zoom, light, dark, high contrast, and reduced motion across supported engines where deterministic.
- **FR-031**: Tests MUST assert geometry, overflow, focus visibility, target size, readable contrast, announcements, and behavior in addition to screenshots.
- **FR-032**: Baseline changes MUST require an explicit review sidecar; tests MUST never silently approve new images.
- **FR-033**: Failures MUST be diagnosable through redacted artifacts and MUST NOT silently degrade to success.
- **FR-034**: Schema and API changes MUST include forward migration, compatibility, rollback, and restore validation.
- **FR-035**: Deployment validation MUST use the established orchestrator, staging-only certificates, bounded cost, exact teardown, and empty-provider reconciliation.

### Key Entities

- **UserPreferenceSet**: One versioned set of typed experience preferences for a user and site/tenant.
- **NotificationPreference**: Delivery choice for an allowlisted event family and channel, including mandatory classification.
- **SettingsCapability**: Static safe metadata declaring a supported category, route, feature version, and dependencies.
- **SecurityEventView**: Redacted user-owned projection of relevant append-only audit events.
- **PrivacyOperationView**: User-owned status projection for durable export, correction, or deletion.

## Success Criteria

- **SC-001**: Every declared requirement maps to at least one automated test and one implementation/evidence task.
- **SC-002**: Representative users can locate any enabled setting through navigation or search in three interactions or fewer.
- **SC-003**: All settings journeys complete without horizontal page overflow or obscured controls in the declared rendering matrix.
- **SC-004**: Automated accessibility checks have zero serious or critical findings, and manual keyboard/screen-reader scripts complete successfully.
- **SC-005**: All authorization, tenant-crossing, CSRF, replay, stale-version, unsafe-URL, and secret-output negative tests fail closed.
- **SC-006**: Focused changed-line coverage is at least 90%, with every security- and privacy-critical branch directly exercised.
- **SC-007**: Full repository gates, generated-profile matrices, and staging live acceptance pass with zero unresolved findings.
- **SC-008**: Canary teardown leaves zero Feature 103 provider resources and an idempotent replay performs zero additional provider actions.

## Explicit Boundaries

- This feature does not activate passkeys without a separately complete WebAuthn implementation.
- It does not create production deployments, production certificates, provider resources, or spending without the established separate lifecycle authority.
- It cannot guarantee the absence of unknown future defects; it guarantees complete specified traceability, strong negative testing, observable failures, and regression evidence for every discovered defect.
