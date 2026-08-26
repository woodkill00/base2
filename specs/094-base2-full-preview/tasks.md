# Tasks: Base2 Full-Stack Obsidian Preview

**Input**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, and `contracts/`
**Rule**: A task is complete only with its stated evidence; required unavailable/skipped checks are failures.

## Phase 1 - Contracts and failing tests

- [x] T001 Validate all Feature 094 documents contain no placeholders and pass prerequisite discovery.
- [x] T002 Add full-preview policy schema fixtures and schema tests.
- [x] T003 Add lease-v2 schema fixtures and schema tests.
- [x] T004 Add canonical-profile generation tests that initially require `base2-obsidian` in every target.
- [x] T005 Add profile-registry generation tests that reject manual-import drift and unknown selections.
- [x] T006 Add API service-index contract tests for `/api` and verify no sensitive fields.
- [x] T007 Add mode-selection tests for local, minimal-canary, full-preview, and unknown modes.
- [x] T008 Add rendered full-preview host/path matrix tests.
- [x] T009 Add public-port isolation and staging-only certificate tests.
- [x] T010 Add owner-CIDR hostile validation tests for IPv4 and IPv6.
- [x] T011 Add private credential/basic-auth validation and redaction tests.
- [x] T012 Add exact multi-record DNS transaction tests for create, duplicate, stale, rollback, and replay.
- [x] T013 Add lease-v2 transition, integrity, expiry, and identity tests.
- [x] T014 Add early-teardown regression proving no DNS deletion after an unexpired refusal.
- [x] T015 Add partial compute/DNS cleanup and reconciliation tests.
- [x] T016 Add outside-in probe contract tests for anonymous, denied, and authorized results.
- [x] T017 Add live-evidence schema/redaction tests.
- [x] T018 Add resource-pressure/build-mode tests for the 2 GB profile.

## Phase 2 - Canonical Base2 profile and visual system

- [x] T019 Create canonical `site_profiles/base2-obsidian.json` with all compatible core modules.
- [x] T020 Generate integrity-identical API, Django, and React profile copies.
- [x] T021 Generate the React profile registry and remove hand-maintained profile imports.
- [x] T022 Propagate profile identity through Compose build/runtime configuration.
- [x] T023 Apply profile theme before first paint while preserving accessible light/dark preference.
- [x] T024 Complete the approved Obsidian homepage composition on current components.
- [x] T025 Add Base2-specific branding assets and accessible alternative text.
- [x] T026 Add profile/source build markers without leaking internal data.
- [x] T027 Add deterministic desktop, tablet, and mobile Obsidian visual references.
- [x] T028 Add keyboard, focus, reduced-motion, and first-paint theme tests.
- [x] T029 Add loading, empty, validation, authentication, and error-state visual checks.
- [x] T030 Prove fixture profiles remain visually and semantically distinct.

## Phase 3 - API and guarded edge

- [x] T031 Implement the safe `/api` service index.
- [x] T032 Define the versioned full-preview route policy and exact expected responses.
- [x] T033 Add `dynamic-full-preview.yml` with public and protected surfaces.
- [x] T034 Make Traefik mode selection strict and fail closed on contradictions.
- [x] T035 Require owner allowlist plus edge authentication for every operator surface.
- [x] T036 Preserve Django and pgAdmin application authentication behind the edge.
- [x] T037 Enable Swagger only in explicit full-preview/local policy.
- [x] T038 Verify operator services and Docker socket have no direct public exposure.
- [x] T039 Add exact subdomain redirect and path-guard behavior.
- [x] T040 Add security headers, noindex policy, request IDs, and safe access logging.

## Phase 4 - Owner admission and private configuration

- [x] T041 Implement exact public-host CIDR validation with bounded cardinality and expiry.
- [x] T042 Implement private full-preview environment rendering from SecretRefs/generated secrets.
- [x] T043 Validate independent credentials and safe htpasswd representation per operator service.
- [x] T044 Add an exact, separately authorized owner-allowlist refresh operation.
- [x] T045 Add environment/report/process redaction scans.
- [x] T046 Document Vaultwarden fields and browser access without printing credentials.

## Phase 5 - DNS and lifecycle

- [x] T047 Implement exact required-host DNS planning and legacy-record inventory.
- [x] T048 Implement transactional DNS creation with bound record identities and rollback.
- [x] T049 Implement PreviewLeaseV2 atomic private state and integrity validation.
- [x] T050 Bind source, profile, Droplet, DNS, admission, certificate, budget, and expiry.
- [x] T051 Implement explicit early-teardown authority and a non-success unexpired refusal.
- [x] T052 Implement ordered compute-then-DNS teardown in one state machine.
- [x] T053 Implement partial-failure recovery, reconciliation, and verified zero-resource completion.
- [x] T054 Install one lease timer whose service uses the unified lifecycle operation.
- [x] T055 Prove replay and concurrent invocation are idempotent and locked.

## Phase 6 - Orchestration and evidence

- [x] T056 Add paired Bash/PowerShell full-preview entrypoints over the portable Python orchestrator.
- [x] T057 Preflight clean source, exact commit/archive/profile, resolver privacy, DNS, admission, budget, region, size, and staging TLS.
- [x] T058 Add bounded/cached build sequencing and actionable resource failure evidence.
- [x] T059 Wait for every declared service and capture safe diagnostics on failure.
- [x] T060 Implement authenticated outside-in route probes without exposing credentials.
- [x] T061 Implement live browser screenshot, console, request, identity, and interaction verification.
- [x] T062 Emit integrity-bound redacted readiness/live/teardown evidence.
- [x] T063 Add immediate replay proof with zero extra provider actions.
- [x] T064 Add exact temporary-source-branch cleanup verification.

## Phase 7 - Gates and delivery

- [x] T065 Run focused Python, React, profile-generation, Traefik, lifecycle, and evidence suites.
- [x] T066 Run three-viewport visual review and approve only intended references.
- [x] T067 Run hostile CIDR, credential, DNS, lease, teardown, replay, and secret matrices.
- [x] T068 Run Compose render and providerless complete create-to-destroy simulation.
- [x] T069 Run the full repository complete gate with zero required gaps.
- [x] T070 Run tracked/staged/history/generated/evidence secret scans with zero findings.
- [x] T071 Complete traceability from all 36 requirements and 8 success criteria to evidence.
- [x] T072 Commit, push, open a draft PR, validate required CI, review, and merge.
- [x] T073 Confirm merged-main local readiness and produce `ready_for_live_approval` without provider mutation.
- [x] T074 Launch the separately approved bounded live preview, validate it, and present the live site for owner review.

## Dependencies

- T001-T018 precede implementation.
- T019-T030, T031-T040, and T041-T046 precede live orchestration.
- T047-T055 precede any provider mutation.
- T056-T064 depend on the profile, edge, admission, and lifecycle phases.
- T065-T073 precede T074.
- T074 includes live review but final resource teardown remains required after the review window.
