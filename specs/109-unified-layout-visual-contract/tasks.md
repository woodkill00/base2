# Ordered implementation tasks

All tasks below are pending. Complete a task only with its stated evidence.
Sequential predecessor references define a safe execution order; no agent fan-out
or cloud resources are implied. Representative owner approval is an explicit hold.

## Discovery and failing contracts

- [ ] T001 [FR-001 FR-007] (depends: none) Inventory routes, nested states, modules and locales from `react-app/src/routes/` and SettingsCenter; create `route-inventory.md` with current shell and missing-slot evidence.
- [ ] T002 [FR-004 FR-012] (depends: T001) Capture private before screenshots and create `defects.md` in this feature directory; classify spacing, centering, duplication, overflow and missing menus with reproducible case IDs.
- [ ] T003 [FR-002 FR-003] (depends: T002) Ratify `contracts/layout-acceptance.md` and proposed auth/guest/right-context policies; record any owner-approved omission in `layout-decisions.md`, defaulting to both rails otherwise.
- [ ] T004 [FR-001 FR-003 FR-010] (depends: T003) Add failing inventory tests for missing route policy, unknown nested/module routes and unapproved exceptions in `react-app/src/__tests__/layout-policy.test.ts`.
- [ ] T005 [FR-002 FR-004 FR-005 FR-006] (depends: T004) Add failing shared-shell tests in `react-app/src/__tests__/app-shell.test.tsx` for two rails, unique landmarks, focus/drawer lifecycle, alignment and scroll-state ownership.
- [ ] T006 [FR-008 FR-012] (depends: T005) Add regression cases preserving guest/permission filtering, sign-out, settings semantics and restricted-preview refusal in `react-app/e2e/layout/`; failures must identify the exact boundary.

## Shared foundation and representative slice

- [ ] T007 [FR-001 FR-003] (depends: T006) Implement reviewed route-policy configuration under `react-app/src/config/` and exhaustive route matching; reject missing policy rather than silently choosing a rail-free layout.
- [ ] T008 [FR-002 FR-004] (depends: T007) Consolidate global structure in `components/glass/AppShell.tsx` and `components/public/PublicShell.jsx`; implement shared slots and tokens without creating a third competing shell.
- [ ] T009 [FR-005 FR-006] (depends: T008) Implement shared rail controls, breakpoint transitions, focus restoration and explicit scroll policy in `react-app/src/components/glass/`; prove no snapping or focus loss.
- [ ] T010 [FR-002 FR-007] (depends: T009) Integrate header, footer, restriction notice, dialogs and toast offsets through shared CSS; test short/long content and overlay stacking without per-route spacing hacks.
- [ ] T011 [FR-002 FR-004 FR-009] (depends: T010) Migrate `pages/Home.js`, `pages/Dashboard.jsx` and `pages/SettingsCenter.jsx` to the shared structure, preserving nested settings navigation and removing duplicate global bars.
- [ ] T012 [FR-005 FR-007 FR-008 FR-010] (depends: T011) Exercise the representative routes with synthetic auth/data, all declared shell breakpoints, keyboard/touch, deep links and loading/error/disabled states in `e2e/layout/`.
- [ ] T013 [FR-009 FR-011] (depends: T012) Present private before/after representative gallery and record owner approval or revision tasks in `layout-decisions.md`; do not begin broad rollout until accepted.

## Remaining route families

- [ ] T014 [FR-001 FR-003 FR-008] (depends: T013) Migrate login/signup/recovery/invitation/verification pages through the approved guest layout; prove public-safe menus and unchanged authentication/redirect behavior.
- [ ] T015 [FR-001 FR-004 FR-007] (depends: T014) Migrate public content, collections, search, contact and enabled-module pages under `pages/public/`; cover localized, empty, long-content and not-found states.
- [ ] T016 [FR-001 FR-002 FR-008] (depends: T015) Migrate first-party AdminConsole, ContentWorkspace, MediaLibrary and OperationsCenter with correct permission filtering and explicit restricted-preview states, not privileged vendor reskinning.
- [ ] T017 [FR-004 FR-005 FR-007] (depends: T016) Test theme/profile compatibility, RTL, long labels, 200% zoom/text and mobile safe areas in `e2e/layout/`; correct shared tokens rather than overwriting unrelated theme identities.
- [ ] T018 [FR-001 FR-002 FR-007] (depends: T017) Audit the complete inventory for nested shell duplication, undocumented omissions, dead links and body overflow; remove superseded layout CSS/components only after consumer checks.

## Durable visual assurance and release

- [ ] T019 [FR-010 FR-011 FR-012] (depends: T018) Implement deterministic cases/readiness and immutable attempt directories in the existing Playwright harness; bind screenshots to source, profile, theme, fonts, fixtures and browser version.
- [ ] T020 [FR-004 FR-005 FR-006 FR-007 FR-010] (depends: T019) Add geometry/scroll/focus/overflow assertions and desktop/mobile family screenshots; execute shared interactions in Chromium, Firefox and WebKit with documented platform limits.
- [ ] T021 [FR-001 FR-010 FR-012] (depends: T020) Prove negative controls: remove a rail, add an unknown route, force overflow/scroll reset and break focus; tests must fail with actionable case-specific evidence, then restore fixtures.
- [ ] T022 [FR-011 FR-012] (depends: T021) Review actual screenshot differences, fix discovered defects, and update only intentional reviewed baselines; retain original failures and record owner-approved design decisions separately from automation.
- [ ] T023 [FR-010 FR-013] (depends: T022) Wire route coverage and visual contracts into `scripts/config/complete-gate-v1.json` and supported CI/assurance selection; prove adding a new page cannot bypass the required layout inventory.
- [ ] T024 [FR-008 FR-013] (depends: T023) Run affected unit, browser, accessibility, auth and restricted-mode tests plus changed-line coverage; validate clean exact source, tools and current repetition evidence before the expensive release gate.
- [ ] T025 [FR-012 FR-013] (depends: T024) Run the mandated complete gate once the prerequisites pass; classify any failure, refine repair tasks and rerun only with valid correction/evidence, never suppressing failures or lowering floors.
- [ ] T026 [FR-008 FR-014] (depends: T025) Verify local rollback of the layout commits and preservation of routes/guards/data in the supported test environment; record recovery steps in `quickstart.md` without live data mutation.
- [ ] T027 [FR-010 FR-011 FR-014] (depends: T026) With launch authority, deploy exact source using the supported bounded preview path; capture live desktop/mobile families, verify interactions and protections, and obtain final owner visual review.
- [ ] T028 [FR-012 FR-013 FR-014] (depends: T027) Record final passed/failed/blocked scope, remaining issues and owner decision in `closeout.md`; verify lease teardown/resource absence when due before claiming lifecycle closeout.
