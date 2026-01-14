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

- [x] T001 [P] Create glass styles directory at c:\Users\theju\Documents\coding\website_build\base2\react-app\src\styles\
- [x] T002 [P] Create component library directory at c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\glass\
- [x] T003 [P] Create Storybook stories directory at c:\Users\theju\Documents\coding\website_build\base2\react-app\src\stories\
- [x] T004 Add spec README pointer in c:\Users\theju\Documents\coding\website_build\base2\specs\002-react-design\quickstart.md
- [x] T005 Ensure npm dependencies installed in c:\Users\theju\Documents\coding\website_build\base2\react-app\package.json

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented.

- [x] T006 Define CSS tokens (glass, spacing, motion, layout) in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\styles\tokens.css

- [x] T007 [P] Add global glass base styles and `.dark` class handling in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\styles\glass.css
- [x] T008 [P] Wire tokens and base styles in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\App.css
- [x] T009 [P] Early theme hydration snippet in c:\Users\theju\Documents\coding\website_build\base2\react-app\public\index.html

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

- [x] T050 [P] [US1] RTL unit tests for ThemeToggle in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\_\_tests\_\_\theme-toggle.test.tsx
- [x] T051 [P] [US1] Accessibility tests (jest-axe) for focus-visible and contrast in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\_\_tests\_\_\glass-a11y.test.tsx
- [x] T052 [P] [US1] Storybook interaction tests for Header/ThemeToggle in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\stories\ThemeToggle.stories.tsx
- [x] T063 [P] [US1] RTL tests: cookie precedence (backend override > client cookie > prefers-color-scheme) in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\_\_tests\_\_\theme-persistence.test.tsx
- [x] T064 [P] [US1] RTL tests: ensure no localStorage usage and root theme class set pre-mount in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\_\_tests\_\_\theme-persistence.test.tsx
- [x] T065 [P] [US1] Playwright e2e: verify Set-Cookie attributes (Secure, SameSite=Lax, Path=/, Domain=.woodkilldev.com, Expires≈180d) in c:\Users\theju\Documents\coding\website_build\base2\react-app\e2e\theme-cookie.spec.js
- [x] T066 [P] [US1] RTL/Storybook: simulate no `backdrop-filter` support and verify fallback styles (semi-transparent + border/shadow) in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\_\_tests\_\_\glass-fallback.test.jsx

### Implementation for User Story 1

- [x] T010 [P] [US1] Implement `ThemeToggle` component in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\glass\ThemeToggle.tsx
- [x] T011 [P] [US1] Add theme persistence util in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\services\theme\persistence.ts
- [x] T012 [P] [US1] Implement animated sun/moon SVG in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\glass\icons\SunMoon.tsx
- [x] T013 [US1] Integrate `ThemeToggle` into app header in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\glass\GlassHeader.tsx
- [x] T014 [US1] Apply focus-visible 3px glow to interactive elements in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\styles\glass.css
- [x] T015 [US1] Storybook: ThemeToggle and header stories (light/dark, hover/focus) in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\stories\ThemeToggle.stories.tsx

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

- [x] T053 [P] [US2] RTL tests for `GlassButton` variants in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\_\_tests\_\_\glass-button.test.tsx
- [x] T054 [P] [US2] RTL tests for `GlassModal` open/close + focus trap in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\_\_tests\_\_\glass-modal.test.tsx
- [x] T055 [P] [US2] Storybook interaction tests for all components in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\stories\glass\
- [x] T067 [P] [US2] RTL tests: blur fallback active on components when `backdrop-filter` unsupported in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\_\_tests\_\_\glass-components-fallback.test.tsx
- [x] T068 [P] [US2] Storybook interactions: verify light/dark with glass fallback toggles across components in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\stories\glass\GlassFallback.stories.tsx
- [x] T069 [P] [US2] Accessibility (jest-axe): contrast ≥ 4.5:1 in fallback mode for key text/controls in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\_\_tests\_\_\glass-a11y-fallback.test.tsx

### Implementation for User Story 2

- [x] T016 [P] [US2] Create `GlassCard` in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\glass\GlassCard.tsx
- [x] T017 [P] [US2] Create `GlassButton` in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\glass\GlassButton.tsx
- [x] T018 [P] [US2] Create `GlassInput` in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\glass\GlassInput.tsx
- [x] T019 [P] [US2] Create `GlassTabs` in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\glass\GlassTabs.tsx
- [x] T020 [P] [US2] Create `GlassModal` in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\glass\GlassModal.tsx
- [x] T021 [P] [US2] Create `GlassSpinner` in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\glass\GlassSpinner.tsx
- [x] T022 [P] [US2] Create `GlassSkeleton` in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\glass\GlassSkeleton.tsx
- [x] T023 [US2] Implement inline SVG icon pattern with aria labels in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\glass\icons\README.md
- [x] T024 [US2] Storybook: Stories for all components with light/dark, hover/focus, disabled/error in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\stories\glass\

**Checkpoint**: Components independently testable; stories render with no console warnings.

---

### Home Page (Public) — Implementation (User Story 2)

**Goal**: Implement the Public Home Page (`/`) using glass components with a black backdrop, gradient/mesh background, and no API calls.

**Independent Test**: Home page renders without API; sections present and accessible; glass visible in both themes; no flat sections; no JS layout math.

#### Implementation Tasks (Write tests first where applicable)

- [ ] T070 [P] [US2] Create Home components directory at c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\home\
- [ ] T071 [P] [US2] Implement `HomeHero` in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\home\HomeHero.jsx
- [ ] T072 [P] [US2] Implement `HomeFeatures` in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\home\HomeFeatures.jsx
- [ ] T073 [P] [US2] Implement `HomeVisual` (lazy-load Illustration) in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\home\HomeVisual.jsx
- [ ] T074 [P] [US2] Implement `HomeTrust` in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\home\HomeTrust.jsx
- [ ] T075 [P] [US2] Implement `HomeFooter` in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\home\HomeFooter.jsx
- [ ] T076 [US2] Compose sections on Home page in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\pages\Home.js (gradient/mesh background; glass-only containers; black backdrop)
- [ ] T077 [P] [US2] Add ARIA labels and role="img" for inline SVGs in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\home\
- [ ] T078 [P] [US2] Add search-style glass input in header (public variant) in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\glass\GlassHeader.tsx
- [ ] T079 [P] [US2] Add assets (logo.svg, hero.svg/webp, feature icons, decorative-glass.svg, mesh-light.svg, mesh-dark.svg) in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\assets\

#### Tests for Home Page

- [ ] T080 [P] [US2] Storybook composition: Home page in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\stories\home\HomePage.stories.jsx
- [ ] T081 [P] [US2] RTL tests: sections render and keyboard navigation works in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\_\_tests\_\_\home\home-page.test.jsx
- [ ] T082 [P] [US2] Playwright: verify black backdrop and glass visibility across sections in c:\Users\theju\Documents\coding\website_build\base2\react-app\e2e\home-style.spec.ts
- [ ] T083 [P] [US2] Accessibility (jest-axe): focus-visible glow everywhere and contrast ≥ 4.5:1 in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\_\_tests\_\_\home\home-a11y.test.jsx

**Checkpoint**: Public Home Page independently testable and compliant with spec.

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

- [x] T056 [P] [US3] Playwright e2e checks for calc sizes and sidebar bounds in c:\Users\theju\Documents\coding\website_build\base2\react-app\e2e\app-shell.spec.ts
- [x] T057 [P] [US3] Performance measurement: Lighthouse/Web Vitals layout shift ≤ 5% in c:\Users\theju\Documents\coding\website_build\base2\react-app\scripts\perf\layout-shift.spec.ts

### Implementation for User Story 3

- [x] T025 [P] [US3] Implement `GlassHeader` in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\glass\GlassHeader.tsx
- [x] T026 [P] [US3] Implement `GlassSidebar` (5 items) in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\glass\GlassSidebar.tsx
- [x] T027 [P] [US3] Implement `AppShell` and content grid in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\glass\AppShell.tsx
- [x] T028 [US3] Apply layout tokens and calc discipline in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\styles\tokens.css
- [x] T029 [US3] Storybook: AppShell composition and responsive grid in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\stories\AppShell.stories.tsx

**Checkpoint**: App Shell independently testable; layout validates via calc-only sizing.

---

## Phase 6: Integration

**Purpose**: Wrap target pages and ensure no auth/routing regressions.

- [x] T030 [US2] Integrate components into dashboard in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\pages\Dashboard.tsx
- [x] T031 [US2] Integrate components into settings in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\pages\Settings.tsx
- [x] T032 Preserve auth behavior and routing; verify no changes in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\services\auth\

---

## Phase 7: Accessibility & Performance Review

**Purpose**: Accessibility checks and performance sanity.

- [x] T033 [P] Focus-visible glow validation across components in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\styles\glass.css
- [x] T034 [P] Keyboard navigation and focus management validation in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\glass\
- [x] T035 [P] Reduced-motion support and transform-only animations in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\styles\glass.css
- [x] T036 [P] Contrast checks ≥ 4.5:1 for key text/controls in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\glass\

---

## Phase 8: Storybook Review

**Purpose**: Stories for all components and compositions; verify interaction states and no console warnings.

## Final Phase: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories.

```

## Phase 9: Figma Home Page Design Integration (Build Home Page Design)

**Purpose**: Port the Figma-based home page bundle under `junk/idea` into the existing React glass design system without introducing raster dependencies or deviating from guardrails.

**Source Design**: c:\Users\theju\Documents\coding\website_build\base2\junk\idea\ (see README.md, components under `src/app/components/` and `src/app/components/ui/`)

### Design Review & Mapping

- [ ] T084 [P] Catalog design components used by the home page in c:\Users\theju\Documents\coding\website_build\base2\junk\idea\src\app\components\ (header, hero, features, visual-section, trust-section, footer, side-menu, sub-page-modal)
- [ ] T085 [P] Document UI component mappings (shadcn/ui → glass equivalents) in c:\Users\theju\Documents\coding\website_build\base2\specs\002-react-design\plan.md
- [ ] T086 [P] Note asset policy (vector-only) and license references (Unsplash photos not shipped) in c:\Users\theju\Documents\coding\website_build\base2\docs\DEVELOPMENT.md

### Implementation — Home Page Sections

- [ ] T087 [P] Port `header.tsx` behavior into existing `GlassHeader` variant in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\glass\GlassHeader.tsx (ensure menu + search glass input if present)
- [ ] T088 [P] Implement `HomeHero` from design (junk/idea/src/app/components/hero.tsx) into c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\home\HomeHero.jsx using glass primitives
- [ ] T089 [P] Implement `HomeFeatures` from design (features.tsx) into c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\home\HomeFeatures.jsx with grid `repeat(auto-fit, minmax(calc(300px - 2rem), 1fr))`
- [ ] T090 [P] Implement `HomeVisual` (visual-section.tsx) with lazy-loaded vector asset into c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\home\HomeVisual.jsx (prefer SVG/WebP)
- [ ] T091 [P] Implement `HomeTrust` (trust-section.tsx) as glass pills/cards into c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\home\HomeTrust.jsx
- [ ] T092 [P] Implement `HomeFooter` (footer.tsx) into c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\home\HomeFooter.jsx
- [ ] T093 [P] Compose sections on the Home page in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\pages\Home.js respecting black backdrop + mesh background and calc-only layout discipline

### Implementation — Supporting Components & Utilities

- [ ] T094 [P] Introduce `ImageWithFallback` utility (junk/idea/src/app/components/figma/ImageWithFallback.tsx) into c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\common\ImageWithFallback.tsx with vector-first policy
- [ ] T095 [P] Verify `GlassButton`, `GlassInput`, `GlassCard`, `GlassTabs`, `GlassModal` support required variants/states from design; extend if needed in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\glass\
- [ ] T096 [P] Optional: Implement `GlassSidebar` affordances to align `side-menu.tsx` behaviors in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\glass\GlassSidebar.tsx
- [ ] T097 [P] Map critical `ui/*` primitives used by the design (button, input, card, dialog/tabs) to glass equivalents; record mapping table in c:\Users\theju\Documents\coding\website_build\base2\specs\002-react-design\plan.md

### Assets & Styling

- [ ] T098 [P] Add or update vector assets (logo.svg, hero.svg/webp, decorative shapes, mesh backgrounds) under c:\Users\theju\Documents\coding\website_build\base2\react-app\src\assets\ complying with vector-only policy
- [ ] T099 [P] Ensure backdrop blur fallbacks are active where `backdrop-filter` unsupported across new sections via c:\Users\theju\Documents\coding\website_build\base2\react-app\src\styles\glass.css

### Tests — Home Page Design

- [ ] T100 [P] Storybook: Add Home page composition story under c:\Users\theju\Documents\coding\website_build\base2\react-app\src\stories\home\HomePage.stories.jsx (light/dark + interactions)
- [ ] T101 [P] RTL: Home page sections render and keyboard navigation works under c:\Users\theju\Documents\coding\website_build\base2\react-app\src\__tests__\home\home-page.test.jsx
- [ ] T102 [P] Playwright: Verify black backdrop, glass fidelity, and calc sizing across sections in c:\Users\theju\Documents\coding\website_build\base2\react-app\e2e\home-style.spec.ts
- [ ] T103 [P] Accessibility (jest-axe): focus-visible and ≥4.5:1 contrast across design sections in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\__tests__\home\home-a11y.test.jsx
- [ ] T104 [P] RTL: Verify `ImageWithFallback` loads vector-first and applies fallback cleanly in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\__tests__\common\image-fallback.test.tsx
- [ ] T105 [P] Storybook: Verify `GlassModal` + sub-page modal interaction parity with design in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\stories\glass\ModalDesignParity.stories.tsx

### Documentation & Attributions

- [ ] T106 [P] Add ATTRIBUTIONS note referencing shadcn/ui MIT and Unsplash license (design-only) in c:\Users\theju\Documents\coding\website_build\base2\docs\DEVELOPMENT.md and c:\Users\theju\Documents\coding\website_build\base2\specs\002-react-design\quickstart.md
- [ ] T107 [P] Link to design bundle README in c:\Users\theju\Documents\coding\website_build\base2\specs\002-react-design\plan.md and clarify no backend changes required

**Checkpoint**: Home page design integrated into glass system; stories and tests validate fidelity, accessibility, and layout discipline without raster dependencies.

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

## Parallel Example: User Story 1

- Write RTL tests for `ThemeToggle`, cookie precedence, fallback styling in parallel (distinct test files).
- Implement `ThemeToggle`, persistence util, and header integration in parallel (separate files) before wiring in App Shell.

## Parallel Example: User Story 3

- Implement `GlassHeader`, `GlassSidebar`, and `AppShell` in parallel (separate components).
- Create Playwright calc-sizing e2e and performance spec in parallel with CSS token updates.

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

- [x] T046 [P] Add TypeScript to react-app: create c:\Users\theju\Documents\coding\website_build\base2\react-app\tsconfig.json and install devDependencies (typescript, @types/react, @types/react-dom, @types/jest).

- [x] T047 [P] Configure Storybook for TypeScript in c:\Users\theju\Documents\coding\website_build\base2\react-app\.storybook\ (if not auto-detected).

### Tailwind Usage Policy

- [x] T048 Document Tailwind usage policy (utilities allowed, no removal/replacement, no global overrides, no new plugins) in c:\Users\theju\Documents\coding\website_build\base2\specs\002-react-design\plan.md and c:\Users\theju\Documents\coding\website_build\base2\docs\DEVELOPMENT.md.
- [x] T049 Add a style guard: scan for global overrides and ensure component-scoped CSS variables/tokens in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\styles\.

### Independent Test Criteria (per story)

- US1: Theme toggle persists; glass acceptance checklist passes; focus-visible glow and contrast.
- US2: Each component renders in isolation; ARIA labels present; stories pass without warnings.
- US3: Layout sizes via `calc()`; sidebar 320–400px bounds; content height equals `calc(100vh - header - footer)`.

### Suggested MVP Scope

- US1 only: Theme toggle + glass fidelity in App Shell.
```
