---
description: 'Tasks for React Glass UI System + App Shell'
---

# Tasks: React Glass UI System + App Shell

**Input**: Design documents from specs/002-react-design/
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests will be included only where explicitly requested; this feature emphasizes Storybook and accessibility checks.

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

### Implementation for User Story 1

- [ ] T010 [P] [US1] Implement `ThemeToggle` component in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\glass\ThemeToggle.jsx
- [ ] T011 [P] [US1] Add theme persistence util in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\services\theme\persistence.js
- [ ] T012 [P] [US1] Implement animated sun/moon SVG in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\glass\icons\SunMoon.jsx
- [ ] T013 [US1] Integrate `ThemeToggle` into app header in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\glass\GlassHeader.jsx
- [ ] T014 [US1] Apply focus-visible 3px glow to interactive elements in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\styles\glass.css
- [ ] T015 [US1] Storybook: ThemeToggle and header stories (light/dark, hover/focus) in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\stories\ThemeToggle.stories.jsx

**Checkpoint**: User Story 1 independently testable via UI and Storybook.

---

## Phase 4: User Story 2 - Compose Screens with Glass Components (Priority: P2)

**Goal**: Reusable glass component library for screens: cards, buttons, inputs, tabs, modals, spinners, skeletons.

**Independent Test**: Each component renders in isolation with accessible states; Storybook stories demonstrate light/dark and interaction states without console warnings.

### Implementation for User Story 2

- [ ] T016 [P] [US2] Create `GlassCard` in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\glass\GlassCard.jsx
- [ ] T017 [P] [US2] Create `GlassButton` in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\glass\GlassButton.jsx
- [ ] T018 [P] [US2] Create `GlassInput` in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\glass\GlassInput.jsx
- [ ] T019 [P] [US2] Create `GlassTabs` in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\glass\GlassTabs.jsx
- [ ] T020 [P] [US2] Create `GlassModal` in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\glass\GlassModal.jsx
- [ ] T021 [P] [US2] Create `GlassSpinner` in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\glass\GlassSpinner.jsx
- [ ] T022 [P] [US2] Create `GlassSkeleton` in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\glass\GlassSkeleton.jsx
- [ ] T023 [US2] Implement inline SVG icon pattern with aria labels in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\glass\icons\README.md
- [ ] T024 [US2] Storybook: Stories for all components with light/dark, hover/focus, disabled/error in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\stories\glass\

**Checkpoint**: Components independently testable; stories render with no console warnings.

---

## Phase 5: User Story 3 - Calc-Driven Responsive App Shell (Priority: P3)

**Goal**: App Shell layout using CSS `calc()` for header, sidebar, content, footer; responsive constraints without JS layout math.

**Independent Test**: Resize viewport; verify header/footer heights, sidebar width, and content height computed via `calc()` with min/max bounds.

### Implementation for User Story 3

- [ ] T025 [P] [US3] Implement `GlassHeader` in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\glass\GlassHeader.jsx
- [ ] T026 [P] [US3] Implement `GlassSidebar` (5 items) in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\glass\GlassSidebar.jsx
- [ ] T027 [P] [US3] Implement `AppShell` and content grid in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\glass\AppShell.jsx
- [ ] T028 [US3] Apply layout tokens and calc discipline in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\styles\tokens.css
- [ ] T029 [US3] Storybook: AppShell composition and responsive grid in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\stories\AppShell.stories.jsx

**Checkpoint**: App Shell independently testable; layout validates via calc-only sizing.

---

## Phase 6: Integration

**Purpose**: Wrap target pages and ensure no auth/routing regressions.

- [ ] T030 [US2] Integrate components into dashboard in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\pages\Dashboard.jsx
- [ ] T031 [US2] Integrate components into settings in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\pages\Settings.jsx
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
- [ ] T043 [P] Quickstart validation and checklist in c:\Users\Users\theju\Documents\coding\website_build\base2\specs\002-react-design\quickstart.md
- [ ] T044 [P] Prepare deploy script usage notes (update-only + all tests) in c:\Users\theju\Documents\coding\website_build\base2\docs\DEPLOY.md
- [ ] T045 [P] After push, run deploy script update-only with all tests in c:\Users\theju\Documents\coding\website_build\base2\digital_ocean\scripts\powershell\deploy.ps1

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

### Independent Test Criteria (per story)

- US1: Theme toggle persists; glass acceptance checklist passes; focus-visible glow and contrast.
- US2: Each component renders in isolation; ARIA labels present; stories pass without warnings.
- US3: Layout sizes via `calc()`; sidebar 320–400px bounds; content height equals `calc(100vh - header - footer)`.

### Suggested MVP Scope

- US1 only: Theme toggle + glass fidelity in App Shell.
