# Implementation Plan: Unified Account and Settings Platform

**Branch**: `vscode-codex/103-unified-settings-platform` | **Date**: 2026-08-30 | **Spec**: `spec.md`

## Summary

Build one capability-driven settings center over Base2's existing identity and privacy foundations. Add versioned preference and notification models in Django, mirrored PostgreSQL/FastAPI contracts, then an adaptive React shell. Extend authenticated visual, accessibility, security, migration, and generated-site gates.

## Technical Context

**Language/Version**: Python 3.12, JavaScript/TypeScript, SQL
**Dependencies**: Django, FastAPI, PostgreSQL, React 18, Vite, Playwright, Vitest
**Testing**: pytest, Django tests, Vitest/jest-axe, Playwright, complete gate
**Target**: Containerized Linux, responsive browsers, ephemeral DigitalOcean preview
**Constraints**: No arbitrary keys, no client credential storage, staging-only certificates, explicit provider lifecycle authority

## Constitution Check

- Spec before plan/tasks/code: PASS.
- TDD and coverage impact: REQUIRED.
- Django before FastAPI before React: REQUIRED.
- Compose parity and repository entrypoints: REQUIRED.
- Script parity for operator commands: REQUIRED.
- Redacted observable artifacts: REQUIRED.
- No production certificates: REQUIRED.

## Architecture

1. Add canonical Django `UserPreferenceSet` and `NotificationPreference` entities.
2. Add equivalent API SQL migration and owner/tenant/version-aware repository.
3. Add capabilities, preferences, notifications, and security-events endpoints.
4. Map settings capabilities from the existing closed, versioned module manifest so a second capability vocabulary cannot drift.
5. Build overview/search/category navigation and typed controls.
6. Integrate existing profile, MFA/session, privacy, organization, and developer surfaces.
7. Add authenticated deterministic fixtures and visual/accessibility matrices.

## Security and failure design

- Owner and tenant checks on all reads/writes.
- Version precondition with non-mutating 409 conflicts.
- Closed enums and bounds; unknown keys rejected.
- Recent authentication and existing CSRF/cookie enforcement for sensitive actions.
- Redacted audit events and secret-free evidence.
- Safe HTTPS avatar parsing without server dereferencing.

## Delivery phases

1. Specification, research, model, contracts, traceability, and analysis.
2. Failing Django/API/manifest tests.
3. Models, SQL migration, repository, and API.
4. Failing React unit/accessibility/interaction tests.
5. Unified shell and category slices.
6. Authenticated visual and responsive matrices.
7. Complete gates, bounded canary, exact teardown, and closeout.

## Rollback

- Tables are additive and legacy routes remain until parity is proven.
- UI may revert while preference rows remain inert.
- Manifest defaults preserve existing profiles.
- Canary rollback uses the existing exact lease lifecycle.
