---
description: 'Tasks for React Glass UI System + App Shell'
---

# Tasks: React Glass UI System + App Shell

**Input**: Design documents from specs/002-react-design/
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are mandatory and must be written first per constitution. Include RTL, accessibility (jest-axe), and Storybook interaction tests.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- [P]: Can run in parallel (different files, no dependencies)
- [Story]: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions (absolute paths)

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure for the frontend feature.

- [ ] T001 [P] Create glass styles directory at c:\Users\theju\Documents\coding\website_build\base2\react-app\src\styles\
- [ ] T002 [P] Create component library directory at c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\glass\
- [ ] T003 [P] Create Storybook stories directory at c:\Users\theju\Documents\coding\website_build\base2\react-app\src\stories\
- [ ] T004 Add spec README pointer in c:\Users\theju\Documents\coding\website_build\base2\specs\002-react-design\quickstart.md
- [ ] T005 Ensure npm dependencies installed in c:\Users\theju\Documents\coding\website_build\base2\react-app\package.json

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented.

- [ ] T006 Define CSS tokens (glass, spacing, motion, layout) in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\styles\tokens.css
- [ ] T007 [P] Add global glass base styles and `.dark` class handling in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\styles\glass.css
- [ ] T008 [P] Wire tokens and base styles in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\App.css
- [ ] T009 [P] Early theme hydration snippet in c:\Users\theju\Documents\coding\website_build\base2\react-app\public\index.html

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel.

---

## Phase 3: User Story 1 - Toggle Theme + Glass Fidelity (Priority: P1) 🎯 MVP

**Goal**: Persistent theme toggle and visible glass fidelity in the App Shell.

**Independent Test**: Toggle persists across reloads; glass acceptance checklist passes in light/dark; focus-visible glow visible; contrast ≥ 4.5:1.

### Testing Scenarios

- Cookie precedence: backend profile override → client `theme` cookie → `prefers-color-scheme` fallback.
- No localStorage usage; root theme class set before React mounts to prevent flicker.
- Set-Cookie attributes present: Secure=true, SameSite=Lax, Path=/, Domain=.woodkilldev.com, Expires≈180 days.
- Fallback when `backdrop-filter` is unsupported: semi-transparent background + border/shadow (no blur) retains fidelity.
- Focus-visible glow (3px) and contrast ≥ 4.5:1 validated across interactive elements.

### Tests for User Story 1 (MANDATORY — write first)

- [ ] T050 [P] [US1] RTL unit tests for ThemeToggle in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\_\_tests\_\_\theme-toggle.test.tsx
- [ ] T051 [P] [US1] Accessibility tests (jest-axe) for focus-visible and contrast in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\_\_tests\_\_\glass-a11y.test.tsx
- [ ] T052 [P] [US1] Storybook interaction tests for Header/ThemeToggle in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\stories\ThemeToggle.stories.tsx
- [ ] T063 [P] [US1] RTL tests: cookie precedence (backend override > client cookie > prefers-color-scheme) in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\_\_tests\_\_\theme-persistence.test.tsx
- [ ] T064 [P] [US1] RTL tests: ensure no localStorage usage and root theme class set pre-mount in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\_\_tests\_\_\theme-persistence.test.tsx
- [ ] T065 [P] [US1] Playwright e2e: verify Set-Cookie attributes (Secure, SameSite=Lax, Path=/, Domain=.woodkilldev.com, Expires≈180d) in c:\Users\theju\Documents\coding\website_build\base2\react-app\e2e\theme-cookie.spec.ts
- [ ] T066 [P] [US1] RTL/Storybook: simulate no `backdrop-filter` support and verify fallback styles (semi-transparent + border/shadow) in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\_\_tests\_\_\glass-fallback.test.tsx

### Implementation for User Story 1

- [ ] T010 [P] [US1] Implement `ThemeToggle` component in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\glass\ThemeToggle.tsx
- [ ] T011 [P] [US1] Add theme persistence util in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\services\theme\persistence.ts
- [ ] T012 [P] [US1] Implement animated sun/moon SVG in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\glass\icons\SunMoon.tsx
- [ ] T013 [US1] Integrate `ThemeToggle` into app header in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\glass\GlassHeader.tsx
- [ ] T014 [US1] Apply focus-visible 3px glow to interactive elements in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\styles\glass.css
- [ ] T015 [US1] Storybook: ThemeToggle and header stories (light/dark, hover/focus) in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\stories\ThemeToggle.stories.tsx

**Checkpoint**: User Story 1 independently testable via UI and Storybook.

---

## Phase 4: User Story 2 - Compose Screens with Glass Components (Priority: P2)

**Goal**: Reusable glass component library for screens: cards, buttons, inputs, tabs, modals, spinners, skeletons.

**Independent Test**: Each component renders in isolation with accessible states; Storybook stories demonstrate light/dark and interaction states without console warnings.

### Testing Scenarios

- Blur fallback: when `backdrop-filter` unsupported, components render semi-transparent with border/shadow (no blur) consistently.
- Storybook interactions validate light/dark themes with fallback toggles; no console warnings.
- Accessibility in fallback mode: contrast ≥ 4.5:1 for key text/controls; focus-visible glow present.
- Modal behavior: ESC/backdrop click closes; focus returns to trigger; tabs switch via keyboard.
- Button variants show hover elevation and disabled states correctly under both themes.

### Tests for User Story 2 (MANDATORY — write first)

- [ ] T053 [P] [US2] RTL tests for `GlassButton` variants in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\_\_tests\_\_\glass-button.test.tsx
- [ ] T054 [P] [US2] RTL tests for `GlassModal` open/close + focus trap in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\_\_tests\_\_\glass-modal.test.tsx
- [ ] T055 [P] [US2] Storybook interaction tests for all components in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\stories\glass\
- [ ] T067 [P] [US2] RTL tests: blur fallback active on components when `backdrop-filter` unsupported in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\_\_tests\_\_\glass-components-fallback.test.tsx
- [ ] T068 [P] [US2] Storybook interactions: verify light/dark with glass fallback toggles across components in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\stories\glass\GlassFallback.stories.tsx
- [ ] T069 [P] [US2] Accessibility (jest-axe): contrast ≥ 4.5:1 in fallback mode for key text/controls in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\_\_tests\_\_\glass-a11y-fallback.test.tsx

### Implementation for User Story 2

- [ ] T016 [P] [US2] Create `GlassCard` in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\glass\GlassCard.tsx
- [ ] T017 [P] [US2] Create `GlassButton` in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\glass\GlassButton.tsx
- [ ] T018 [P] [US2] Create `GlassInput` in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\glass\GlassInput.tsx
- [ ] T019 [P] [US2] Create `GlassTabs` in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\glass\GlassTabs.tsx
- [ ] T020 [P] [US2] Create `GlassModal` in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\glass\GlassModal.tsx
- [ ] T021 [P] [US2] Create `GlassSpinner` in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\glass\GlassSpinner.tsx
- [ ] T022 [P] [US2] Create `GlassSkeleton` in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\glass\GlassSkeleton.tsx
- [ ] T023 [US2] Implement inline SVG icon pattern with aria labels in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\glass\icons\README.md
- [ ] T024 [US2] Storybook: Stories for all components with light/dark, hover/focus, disabled/error in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\stories\glass\

**Checkpoint**: Components independently testable; stories render with no console warnings.

---

## Phase 5: User Story 3 - Calc-Driven Responsive App Shell (Priority: P3)

**Goal**: App Shell layout using CSS `calc()` for header, sidebar, content, footer; responsive constraints without JS layout math.

**Independent Test**: Resize viewport; verify header/footer heights, sidebar width, and content height computed via `calc()` with min/max bounds.

### Testing Scenarios

- Sidebar width respects bounds 320–400px and `calc(100vw * 0.25)` across desktop widths.
- Content height equals `calc(100vh - header - footer)`; stable with minimal layout shift.
- Layout shift ≤ 5% measured via Lighthouse/Web Vitals; no JS layout math used.
- Safe-area insets respected with `env(safe-area-inset-*)` where applicable.

### Tests for User Story 3 (MANDATORY — write first)

- [ ] T056 [P] [US3] Playwright e2e checks for calc sizes and sidebar bounds in c:\Users\theju\Documents\coding\website_build\base2\react-app\e2e\app-shell.spec.ts
- [ ] T057 [P] [US3] Performance measurement: Lighthouse/Web Vitals layout shift ≤ 5% in c:\Users\theju\Documents\coding\website_build\base2\react-app\scripts\perf\layout-shift.spec.ts

### Implementation for User Story 3

- [ ] T025 [P] [US3] Implement `GlassHeader` in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\glass\GlassHeader.tsx
- [ ] T026 [P] [US3] Implement `GlassSidebar` (5 items) in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\glass\GlassSidebar.tsx
- [ ] T027 [P] [US3] Implement `AppShell` and content grid in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\glass\AppShell.tsx
- [ ] T028 [US3] Apply layout tokens and calc discipline in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\styles\tokens.css
- [ ] T029 [US3] Storybook: AppShell composition and responsive grid in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\stories\AppShell.stories.tsx

**Checkpoint**: App Shell independently testable; layout validates via calc-only sizing.

---

## Phase 6: Integration

**Purpose**: Wrap target pages and ensure no auth/routing regressions.

- [ ] T030 [US2] Integrate components into dashboard in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\pages\Dashboard.tsx
- [ ] T031 [US2] Integrate components into settings in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\pages\Settings.tsx
- [ ] T032 Preserve auth behavior and routing; verify no changes in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\services\auth\

---

## Phase 7: Accessibility & Performance Review

**Purpose**: Accessibility checks and performance sanity.

- [ ] T033 [P] Focus-visible glow validation across components in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\styles\glass.css
- [ ] T034 [P] Keyboard navigation and focus management validation in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\glass\
- [ ] T035 [P] Reduced-motion support and transform-only animations in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\styles\glass.css
- [ ] T036 [P] Contrast checks ≥ 4.5:1 for key text/controls in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\glass\

---

## Phase 8: Storybook Review

**Purpose**: Stories for all components and compositions; verify interaction states and no console warnings.

- [ ] T037 [P] Run Storybook and fix warnings in c:\Users\theju\Documents\coding\website_build\base2\react-app\
- [ ] T038 [P] Add interaction stories and controls for components in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\stories\glass\
- [ ] T039 [P] Ensure stories cover modal open and responsive grid in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\stories\

---

## Final Phase: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories.

- [ ] T040 [P] Documentation updates in c:\Users\theju\Documents\coding\website_build\base2\specs\002-react-design\
- [ ] T041 Code cleanup and refactoring in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\glass\
- [ ] T042 Performance optimization across stories in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\
- [ ] T043 [P] Quickstart validation and checklist in c:\Users\theju\Documents\coding\website_build\base2\specs\002-react-design\quickstart.md
- [ ] T044 [P] Prepare deploy script usage notes (update-only + all tests) in c:\Users\theju\Documents\coding\website_build\base2\docs\DEPLOY.md
- [ ] T045 [P] After push, run deploy script update-only with all tests in c:\Users\theju\Documents\coding\website_build\base2\digital_ocean\scripts\powershell\deploy.ps1
- [ ] T060 [P] Validate Visual Acceptance Checklist across AppShell and components in c:\Users\theju\Documents\coding\website_build\base2\specs\002-react-design\checklists\requirements.md
- [ ] T061 [P] Observability artifact review post-deploy (logs, configs, health responses) in c:\Users\theju\Documents\coding\website_build\base2\local_run_logs\
- [ ] T062 [P] Performance verification: confirm layout shift metrics (CLS/Web Vitals) meet targets documented in c:\Users\theju\Documents\coding\website_build\base2\specs\002-react-design\plan.md

---

## Dependencies & Execution Order

### Phase Dependencies

- Setup (Phase 1): No dependencies - can start immediately.
- Foundational (Phase 2): Depends on Setup completion - BLOCKS all user stories.
- User Stories (Phases 3-5): Depend on Foundational - implement in priority order (P1 → P2 → P3) or parallel after Phase 2.
- Integration (Phase 6): Depends on user story completion where integrated.
- Accessibility/Performance (Phase 7): Independent but depends on components presence.
- Storybook Review (Phase 8): Depends on stories creation.
- Polish (Final): Depends on desired user stories being complete.

### User Story Dependencies

- User Story 1 (P1): Starts after Foundational; no dependencies on other stories.
- User Story 2 (P2): Starts after Foundational; independent, may integrate with US1 visually.
- User Story 3 (P3): Starts after Foundational; independent; relies on tokens for layout.

### Parallel Opportunities

- Setup tasks T001–T003 can run in parallel.
- Foundational tasks T006–T009 can run in parallel.
- Within US2, component tasks T016–T022 can run in parallel.
- Accessibility checks T033–T036 can run in parallel.
- Storybook tasks T037–T039 can run in parallel.

## Parallel Example: User Story 2

- Create `GlassCard`, `GlassButton`, `GlassInput`, `GlassTabs`, `GlassModal`, `GlassSpinner`, `GlassSkeleton` in parallel (distinct files).
- Write stories for each concurrently under src/stories/glass/.

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Setup + Foundational.
2. Implement theme toggle and header integration.
3. Validate glass fidelity across app shell.
4. Storybook validation, accessibility checks.

### Incremental Delivery

1. Add component library (US2) → Storybook coverage.
2. Implement App Shell (US3) → Responsive grid.
3. Integrate into pages (dashboard/settings) → No auth/routing changes.

### Deployment Notes

- After pushing to branch `002-react-design`, run deploy script with update-only and all tests:
  - Path: c:\Users\theju\Documents\coding\website_build\base2\digital_ocean\scripts\powershell\deploy.ps1
  - Flags: `-UpdateOnly -RunAllTests`

### TypeScript Setup (Phase 1 additions)

- [ ] T046 [P] Add TypeScript to react-app: create c:\Users\theju\Documents\coding\website_build\base2\react-app\tsconfig.json and install devDependencies (typescript, @types/react, @types/react-dom, @types/jest).
- [ ] T047 [P] Configure Storybook for TypeScript in c:\Users\theju\Documents\coding\website_build\base2\react-app\.storybook\ (if not auto-detected).

### Tailwind Usage Policy

- [ ] T048 Document Tailwind usage policy (utilities allowed, no removal/replacement, no global overrides, no new plugins) in c:\Users\theju\Documents\coding\website_build\base2\specs\002-react-design\plan.md and c:\Users\theju\Documents\coding\website_build\base2\docs\DEVELOPMENT.md.
- [ ] T049 Add a style guard: scan for global overrides and ensure component-scoped CSS variables/tokens in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\styles\.

### Independent Test Criteria (per story)

- US1: Theme toggle persists; glass acceptance checklist passes; focus-visible glow and contrast.
- US2: Each component renders in isolation; ARIA labels present; stories pass without warnings.
- US3: Layout sizes via `calc()`; sidebar 320–400px bounds; content height equals `calc(100vh - header - footer)`.

### Suggested MVP Scope

- US1 only: Theme toggle + glass fidelity in App Shell.
