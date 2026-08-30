#### Implementation Tasks (Write tests first where applicable)

- [x] T070 [P] [US2] Create Home components directory at c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\home\
- [x] T071 [P] [US2] Implement `HomeHero` in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\home\HomeHero.jsx
- [x] T072 [P] [US2] Implement `HomeFeatures` in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\home\HomeFeatures.jsx
- [x] T073 [P] [US2] Implement `HomeVisual` (lazy-load Illustration) in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\home\HomeVisual.jsx
- [x] T074 [P] [US2] Implement `HomeTrust` in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\home\HomeTrust.jsx
- [x] T075 [P] [US2] Implement `HomeFooter` in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\home\HomeFooter.jsx
- [x] T076 [US2] Compose sections on Home page in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\pages\Home.js (gradient/mesh background; glass-only containers; black backdrop)
- [x] T077 [P] [US2] Add ARIA labels and role="img" for inline SVGs in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\home\
- [x] T078 [P] [US2] Add search-style glass input in header (public variant) in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\glass\GlassHeader.tsx
- [x] T079 [P] [US2] Add assets (logo.svg, hero.svg/webp, feature icons, decorative-glass.svg, mesh-light.svg, mesh-dark.svg) in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\assets\

#### Tests for Home Page

- [x] T080 [P] [US2] Storybook composition: Home page in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\stories\home\HomePage.stories.jsx
- [x] T081 [P] [US2] RTL tests: sections render and keyboard navigation works in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\_\_tests\_\_\home\home-page.test.jsx
- [x] T082 [P] [US2] Playwright: verify black backdrop and glass visibility across sections in c:\Users\theju\Documents\coding\website_build\base2\react-app\e2e\home-style.spec.ts
- [x] T083 [P] [US2] Accessibility (jest-axe): focus-visible glow everywhere and contrast ≥ 4.5:1 in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\_\_tests\_\_\home\home-a11y.test.jsx

---

## description: 'Tasks for React Glass UI System + App Shell'

# Tasks: React Glass UI System + App Shell

Input: Design documents from specs/002-react-design/
Prerequisites: specs/002-react-design/plan.md (required), specs/002-react-design/spec.md (required for user stories), specs/002-react-design/research.md, specs/002-react-design/data-model.md, specs/002-react-design/contracts/

Tests: Tests are REQUIRED for this feature (RTL, jest-axe, Storybook interactions, Playwright) per specs/002-react-design/plan.md and specs/002-react-design/spec.md.
Organization: Tasks are grouped by user story to enable independent implementation and testing.

Checklist format (REQUIRED):

```text
 - [ ] T001 [P] [US1] Description with file path
```

Notes:

- [P] tasks can be done in parallel (different files, no dependency)
- [US1]/[US2]/[US3] labels appear only inside user story phases
- All task descriptions include repo-relative file paths

## Phase 1: Setup (Shared Infrastructure)

Purpose: Project initialization and baseline wiring for the React frontend.

- [x] T001 [P] Ensure frontend dependencies install cleanly in react-app/package.json
- [x] T002 [P] Ensure Storybook is runnable and configured in react-app/.storybook/preview.js
- [x] T003 [P] Ensure Playwright runner is configured in react-app/playwright.config.js
- [x] T004 [P] Confirm baseline test setup is present (RTL + jest-axe helpers) in react-app/src/setupTests.js
- [x] T005 Add feature pointers to quickstart in specs/002-react-design/quickstart.md

---

## Phase 2: Foundational (Blocking Prerequisites)

Purpose: Core styling and layout primitives that block all user stories.

CRITICAL: No user story work starts until this phase completes.

- [x] T006 Define/verify design tokens (glass + layout + motion + focus) in react-app/src/styles/tokens.css
- [x] T007 [P] Define global glass base styles and dark-mode variants in react-app/src/styles/glass.css
- [x] T008 [P] Define mesh/gradient background primitives for light/dark in react-app/src/styles/background.css
- [x] T009 [P] Ensure global style import order (tokens → background → glass → app) in react-app/src/App.css
- [x] T010 [P] Add early theme hydration script to set theme class before React mounts in react-app/public/index.html
- [x] T011 Wire style entrypoints (tokens/glass/background) in react-app/src/index.js
- [x] T012 [P] Add/verify Storybook global style loading matches app order in react-app/.storybook/preview.js
- [x] T013 Confirm API contracts unchanged for this feature (no new endpoints) by reviewing specs/002-react-design/contracts/openapi.yaml

Checkpoint: Foundation ready; user stories can proceed.

---

## Phase 3: User Story 1 - Toggle Theme + Glass Fidelity (Priority: P1) MVP

Goal: Users can toggle light/dark and see consistent glass fidelity across the shell.
Independent Test: Toggle theme; reload; theme persists via cookie; no flicker; focus-visible glow present; contrast meets 4.5:1 for key text.

### Tests for User Story 1 (write first)

- [x] T014 [P] [US1] Add RTL tests for theme toggle behavior in react-app/src/**tests**/glass-header.test.tsx
- [x] T015 [P] [US1] Add RTL tests for cookie persistence + prefers-color-scheme fallback in react-app/src/**tests**/app-shell.test.tsx
- [x] T016 [P] [US1] Add accessibility tests for focus-visible + basic landmarks (jest-axe) in react-app/src/**tests**/\_\_home/home-a11y.test.jsx
- [x] T017 [P] [US1] Add Storybook interaction coverage for theme toggle in react-app/src/stories/glass/GlassHeader.stories.tsx

### Implementation for User Story 1

- [x] T018 [US1] Implement deterministic theme resolution (cookie → system) in react-app/src/contexts/ThemeContext.js
- [x] T019 [US1] Wire ThemeProvider at app root in react-app/src/App.js
- [x] T020 [P] [US1] Implement/verify ThemeToggle control UI in react-app/src/components/glass/ThemeToggle.tsx
- [x] T021 [US1] Ensure focus-visible 3px glow tokens and styles apply across components in react-app/src/styles/glass.css
- [x] T022 [US1] Document theme persistence rules (cookie attributes, precedence) in specs/002-react-design/quickstart.md

Checkpoint: US1 is independently testable (toggle + persistence + a11y).

---

## Phase 4: User Story 2 - Compose Screens with Glass Components (Priority: P2)

Goal: A reusable glass component library plus a composed public Home page.
Independent Test: Render each component in Storybook with states; Home page renders with no API calls and passes basic a11y.

### Tests for User Story 2 (write first)

- [x] T023 [P] [US2] Add RTL tests for GlassButton variants and disabled state in react-app/src/**tests**/glass-button.test.tsx
- [x] T024 [P] [US2] Add RTL tests for GlassCard variants and interactive states in react-app/src/**tests**/glass-card.test.tsx
- [x] T025 [P] [US2] Add RTL tests for GlassModal open/close and focus return in react-app/src/**tests**/glass-modal.test.tsx
- [x] T026 [P] [US2] Add RTL tests for GlassSidebar drawer behavior in react-app/src/**tests**/glass-sidebar.test.tsx
- [x] T027 [P] [US2] Add Storybook stories for component library states in react-app/src/stories/glass/GlassButton.stories.tsx (and siblings: GlassCard/GlassInput/GlassModal/GlassSidebar/GlassHeader)
- [x] T028 [P] [US2] Add Home page render + keyboard nav tests in react-app/src/**tests**/home/home-page.test.jsx

### Implementation for User Story 2

- [x] T029 [P] [US2] Implement GlassCard component in react-app/src/components/glass/GlassCard.tsx
- [x] T030 [P] [US2] Implement GlassButton component in react-app/src/components/glass/GlassButton.tsx
- [x] T031 [P] [US2] Implement GlassInput component in react-app/src/components/glass/GlassInput.tsx
- [x] T032 [P] [US2] Implement GlassModal component in react-app/src/components/glass/GlassModal.tsx
- [x] T033 [P] [US2] Implement GlassHeader component (public/app variants) in react-app/src/components/glass/GlassHeader.tsx
- [x] T034 [P] [US2] Implement GlassSidebar component (drawer + desktop) in react-app/src/components/glass/GlassSidebar.tsx
- [x] T035 [US2] Compose public Home sections using glass components in react-app/src/pages/Home.js
- [x] T036 [P] [US2] Implement HomeHero section in react-app/src/components/home/HomeHero.jsx
- [x] T037 [P] [US2] Implement HomeFeatures/HomeVisual/HomeTrust/HomeFooter in react-app/src/components/home/HomeFeatures.jsx, react-app/src/components/home/HomeVisual.jsx, react-app/src/components/home/HomeTrust.jsx, react-app/src/components/home/HomeFooter.jsx
- [x] T038 [US2] Add Home page Storybook composition in react-app/src/stories/home/HomePage.stories.jsx

**Checkpoint**: Components independently testable; stories render with no console warnings.

---

### Home Page (Public) — Implementation (User Story 2)

**Goal**: Implement the Public Home Page (`/`) using glass components with a black backdrop, gradient/mesh background, and no API calls.

**Independent Test**: Home page renders without API; sections present and accessible; glass visible in both themes; no flat sections; no JS layout math.

#### Implementation Tasks (Write tests first where applicable)

- [x] T070 [P] [US2] Create Home components directory at c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\home\
- [x] T071 [P] [US2] Implement `HomeHero` in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\home\HomeHero.jsx
- [x] T072 [P] [US2] Implement `HomeFeatures` in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\home\HomeFeatures.jsx
- [x] T073 [P] [US2] Implement `HomeVisual` (lazy-load Illustration) in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\home\HomeVisual.jsx
- [x] T074 [P] [US2] Implement `HomeTrust` in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\home\HomeTrust.jsx
- [x] T075 [P] [US2] Implement `HomeFooter` in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\home\HomeFooter.jsx
- [x] T076 [US2] Compose sections on Home page in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\pages\Home.js (gradient/mesh background; glass-only containers; black backdrop)
- [x] T077 [P] [US2] Add ARIA labels and role="img" for inline SVGs in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\home\
- [x] T078 [P] [US2] Add search-style glass input in header (public variant) in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\glass\GlassHeader.tsx
- [x] T079 [P] [US2] Add assets (logo.svg, hero.svg/webp, feature icons, decorative-glass.svg, mesh-light.svg, mesh-dark.svg) in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\assets\

#### Tests for Home Page

- [x] T080 [P] [US2] Storybook composition: Home page in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\stories\home\HomePage.stories.jsx
- [x] T081 [P] [US2] RTL tests: sections render and keyboard navigation works in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\_\_tests\_\_home\home-page.test.jsx
- [x] T082 [P] [US2] Playwright: verify black backdrop and glass visibility across sections in c:\Users\theju\Documents\coding\website_build\base2\react-app\e2e\home-style.spec.ts
- [x] T083 [P] [US2] Accessibility (jest-axe): focus-visible glow everywhere and contrast ≥ 4.5:1 in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\_\_tests\_\_home\home-a11y.test.jsx

#### Design Port Additions (Build Home Page Design)

- [x] T089 [P] [US2] Add home page assets folder and document usage/ownership in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\assets\home\README.md (source references, if any, live under c:\Users\theju\Documents\coding\website_build\base2\junk\idea\src\app\components\)
- [x] T090 [US2] Ensure Home page makes zero API requests and uses only glass components + CTAs to /signup and /login in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\pages\Home.js, using layout/content intent from c:\Users\theju\Documents\coding\website_build\base2\junk\idea\src\app\components\hero.tsx and footer.tsx
- [x] T091 [US2] Implement hero layout constraints (min-height 50vh; max width 960px via calc) in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\home\HomeHero.jsx, porting structure from c:\Users\theju\Documents\coding\website_build\base2\junk\idea\src\app\components\hero.tsx
- [x] T092 [P] [US2] Add micro-interactions (idle float, hover elevation/glow, CTA hover pulse) with reduced-motion safety in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\home\HomeHero.jsx, porting behavior from c:\Users\theju\Documents\coding\website_build\base2\junk\idea\src\app\components\hero.tsx
- [x] T093 [P] [US2] Ensure all home UI icons are inline SVG with role/aria-label defaults in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\home\, porting icon patterns from c:\Users\theju\Documents\coding\website_build\base2\junk\idea\src\app\components\hero.tsx, features.tsx, trust-section.tsx

**Checkpoint**: Public Home Page independently testable and compliant with spec.

---

## Phase 5: User Story 3 - Calc-Driven Responsive App Shell (Priority: P3)

Goal: App shell layout uses CSS calc discipline (no JS layout math) and is responsive.
Independent Test: Resize viewport; sidebar respects bounds; content height uses calc(100vh - header - footer); mobile drawer works.

### Tests for User Story 3 (write first)

- [x] T039 [P] [US3] Add RTL tests for AppShell structure and layout class wiring in react-app/src/**tests**/pages-glass.test.jsx
- [x] T040 [P] [US3] Add Playwright checks for responsive behavior in react-app/e2e/app-shell-layout.spec.ts
- [x] T041 [P] [US3] Add Playwright checks for sidebar drawer behavior in react-app/e2e/app-shell-sidebar.spec.ts

### Implementation for User Story 3

- [x] T042 [P] [US3] Implement AppShell layout wrapper (public/app variants) in react-app/src/components/glass/AppShell.tsx
- [x] T043 [US3] Enforce calc-based sizing tokens (header/footer/sidebar/content) in react-app/src/styles/tokens.css
- [x] T044 [US3] Ensure page routes use AppShell variants correctly in react-app/src/App.js
- [x] T045 [US3] Add AppShell Storybook composition and responsive controls in react-app/src/stories/glass/AppShell.stories.tsx

Checkpoint: US3 is independently testable via Playwright + Storybook.

---

## Phase 6: Integration (Cross-Story)

Purpose: Ensure target pages and global wiring are stable and do not change auth or backend/API behavior.

- [x] T046 Integrate AppShell + GlassHeader/GlassSidebar on authenticated pages in react-app/src/pages/Dashboard.jsx
- [x] T047 Integrate AppShell + GlassHeader/GlassSidebar on authenticated pages in react-app/src/pages/Settings.jsx
- [x] T048 Confirm auth flows are unchanged (no token/routing behavior changes) by reviewing react-app/src/contexts/AuthContext.js

---

## Final Phase: Polish & Cross-Cutting Concerns

Purpose: Cross-cutting hardening, docs, and operational safety.

- [x] T049 [P] Run and document local validation commands (lint/test/build/storybook) in docs/TESTING.md
- [x] T050 [P] Update developer notes for telling public vs protected routes in docs/DEVELOPMENT.md

### Additional tasks imported from junk/woodkilldev-speckit-tasks.md

- [x] T051 [P] Remove standalone "..." placeholders from react-app/src/contexts/ThemeContext.js
- [x] T052 [P] Remove standalone "..." placeholders from react-app/src/components/ErrorBoundary.jsx
- [x] T053 Add repo-wide guard to prevent "..." placeholder commits by documenting a grep check in docs/TESTING.md

## Phase 9: Figma Home Page Design Integration (Build Home Page Design)

**Purpose**: Port the Figma-based home page bundle under `junk/idea` into the existing React glass design system without introducing raster dependencies or deviating from guardrails.

**Source Design**: c:\Users\theju\Documents\coding\website_build\base2\junk\idea\ (see README.md, components under `src/app/components/` and `src/app/components/ui/`)

### Design Review & Mapping

- [x] T084 [P] Catalog design components used by the home page in c:\Users\theju\Documents\coding\website_build\base2\junk\idea\src\app\components\ (header, hero, features, visual-section, trust-section, footer, side-menu, sub-page-modal)
- [x] T085 [P] Document UI component mappings (shadcn/ui → glass equivalents) in c:\Users\theju\Documents\coding\website_build\base2\specs\002-react-design\plan.md
- [x] T086 [P] Note asset policy (vector-only) and license references (Unsplash photos not shipped) in c:\Users\theju\Documents\coding\website_build\base2\docs\DEVELOPMENT.md

### Implementation — Home Page Sections

- [x] T087 [P] Port `header.tsx` behavior into existing `GlassHeader` variant in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\glass\GlassHeader.tsx (ensure menu + search glass input if present)
- [x] T088 [P] Implement `HomeHero` from design (junk/idea/src/app/components/hero.tsx) into c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\home\HomeHero.jsx using glass primitives
- [x] T089 [P] Implement `HomeFeatures` from design (features.tsx) into c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\home\HomeFeatures.jsx with grid `repeat(auto-fit, minmax(calc(300px - 2rem), 1fr))`
- [x] T090 [P] Implement `HomeVisual` (visual-section.tsx) with lazy-loaded vector asset into c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\home\HomeVisual.jsx (prefer SVG/WebP)
- [x] T091 [P] Implement `HomeTrust` (trust-section.tsx) as glass pills/cards into c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\home\HomeTrust.jsx
- [x] T092 [P] Implement `HomeFooter` (footer.tsx) into c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\home\HomeFooter.jsx
- [x] T093 [P] Compose sections on the Home page in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\pages\Home.js respecting black backdrop + mesh background and calc-only layout discipline
- [x] T087 [P] Port `header.tsx` behavior into existing `GlassHeader` variant in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\glass\GlassHeader.tsx (ensure menu + search glass input if present)
- [x] T088 [P] Implement `HomeHero` from design (junk/idea/src/app/components/hero.tsx) into c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\home\HomeHero.jsx using glass primitives
- [x] T089 [P] Implement `HomeFeatures` from design (features.tsx) into c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\home\HomeFeatures.jsx with grid `repeat(auto-fit, minmax(calc(300px - 2rem), 1fr))`
- [x] T090 [P] Implement `HomeVisual` (visual-section.tsx) with lazy-loaded vector asset into c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\home\HomeVisual.jsx (prefer SVG/WebP)
- [x] T091 [P] Implement `HomeTrust` (trust-section.tsx) as glass pills/cards into c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\home\HomeTrust.jsx
- [x] T092 [P] Implement `HomeFooter` (footer.tsx) into c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\home\HomeFooter.jsx
- [x] T093 [P] Compose sections on the Home page in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\pages\Home.js respecting black backdrop + mesh background and calc-only layout discipline

### Implementation — Supporting Components & Utilities

- [x] T094 [P] Introduce `ImageWithFallback` utility (junk/idea/src/app/components/figma/ImageWithFallback.tsx) into c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\common\ImageWithFallback.tsx with vector-first policy
- [x] T095 [P] Verify `GlassButton`, `GlassInput`, `GlassCard`, `GlassTabs`, `GlassModal` support required variants/states from design; extend if needed in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\glass\
- [x] T096 [P] Optional: Implement `GlassSidebar` affordances to align `side-menu.tsx` behaviors in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\glass\GlassSidebar.tsx
- [x] T097 [P] Map critical `ui/*` primitives used by the design (button, input, card, dialog/tabs) to glass equivalents; record mapping table in c:\Users\theju\Documents\coding\website_build\base2\specs\002-react-design\plan.md
- [x] T094 [P] Introduce `ImageWithFallback` utility (junk/idea/src/app/components/figma/ImageWithFallback.tsx) into c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\common\ImageWithFallback.tsx with vector-first policy
- [x] T095 [P] Verify `GlassButton`, `GlassInput`, `GlassCard`, `GlassTabs`, `GlassModal` support required variants/states from design; extend if needed in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\glass\
- [x] T096 [P] Optional: Implement `GlassSidebar` affordances to align `side-menu.tsx` behaviors in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\components\glass\GlassSidebar.tsx
- [x] T097 [P] Map critical `ui/*` primitives used by the design (button, input, card, dialog/tabs) to glass equivalents; record mapping table in c:\Users\theju\Documents\coding\website_build\base2\specs\002-react-design\plan.md

### Assets & Styling

- [x] T098 [P] Add or update vector assets (logo.svg, hero.svg/webp, decorative shapes, mesh backgrounds) under c:\Users\theju\Documents\coding\website_build\base2\react-app\src\assets\ complying with vector-only policy
- [x] T099 [P] Ensure backdrop blur fallbacks are active where `backdrop-filter` unsupported across new sections via c:\Users\theju\Documents\coding\website_build\base2\react-app\src\styles\glass.css
- [x] T098 [P] Add or update vector assets (logo.svg, hero.svg/webp, decorative shapes, mesh backgrounds) under c:\Users\theju\Documents\coding\website_build\base2\react-app\src\assets\ complying with vector-only policy
- [x] T099 [P] Ensure backdrop blur fallbacks are active where `backdrop-filter` unsupported across new sections via c:\Users\theju\Documents\coding\website_build\base2\react-app\src\styles\glass.css

### Tests — Home Page Design

- [x] T100 [P] Storybook: Add Home page composition story under c:\Users\theju\Documents\coding\website_build\base2\react-app\src\stories\home\HomePage.stories.jsx (light/dark + interactions)
- [x] T101 [P] RTL: Home page sections render and keyboard navigation works under c:\Users\theju\Documents\coding\website_build\base2\react-app\src\_\_tests\_\_\home\home-page.test.jsx
- [x] T102 [P] Playwright: Verify black backdrop, glass fidelity, and calc sizing across sections in c:\Users\theju\Documents\coding\website_build\base2\react-app\e2e\home-style.spec.ts
- [x] T103 [P] Accessibility (jest-axe): focus-visible and ≥4.5:1 contrast across design sections in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\_\_tests\_\_\home\home-a11y.test.jsx
- [x] T104 [P] RTL: Verify `ImageWithFallback` loads vector-first and applies fallback cleanly in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\_\_tests\_\_\common\image-fallback.test.tsx
- [x] T105 [P] Storybook: Verify `GlassModal` + sub-page modal interaction parity with design in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\stories\glass\ModalDesignParity.stories.tsx
- [x] T100 [P] Storybook: Add Home page composition story under c:\Users\theju\Documents\coding\website_build\base2\react-app\src\stories\home\HomePage.stories.jsx (light/dark + interactions)
- [x] T101 [P] RTL: Home page sections render and keyboard navigation works under c:\Users\theju\Documents\coding\website_build\base2\react-app\src\_\_tests\_\_\home\home-page.test.jsx
- [x] T102 [P] Playwright: Verify black backdrop, glass fidelity, and calc sizing across sections in c:\Users\theju\Documents\coding\website_build\base2\react-app\e2e\home-style.spec.ts
- [x] T103 [P] Accessibility (jest-axe): focus-visible and ≥4.5:1 contrast across design sections in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\_\_tests\_\_\home\home-a11y.test.jsx
- [x] T104 [P] RTL: Verify `ImageWithFallback` loads vector-first and applies fallback cleanly in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\_\_tests\_\_\common\image-fallback.test.tsx
- [x] T105 [P] Storybook: Verify `GlassModal` + sub-page modal interaction parity with design in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\stories\glass\ModalDesignParity.stories.tsx

### Documentation & Attributions

- [x] T106 [P] Add ATTRIBUTIONS note referencing shadcn/ui MIT and Unsplash license (design-only) in c:\Users\theju\Documents\coding\website_build\base2\docs\DEVELOPMENT.md and c:\Users\theju\Documents\coding\website_build\base2\specs\002-react-design\quickstart.md
- [x] T107 [P] Link to design bundle README in c:\Users\theju\Documents\coding\website_build\base2\specs\002-react-design\plan.md and clarify no backend changes required
- [x] T106 [P] Add ATTRIBUTIONS note referencing shadcn/ui MIT and Unsplash license (design-only) in c:\Users\theju\Documents\coding\website_build\base2\docs\DEVELOPMENT.md and c:\Users\theju\Documents\coding\website_build\base2\specs\002-react-design\quickstart.md
- [x] T107 [P] Link to design bundle README in c:\Users\theju\Documents\coding\website_build\base2\specs\002-react-design\plan.md and clarify no backend changes required

**Checkpoint**: Home page design integrated into glass system; stories and tests validate fidelity, accessibility, and layout discipline without raster dependencies.

## Phase 9: Follow-on — Exact Parity with junk/idea (Public Home)

- [x] T054 Add error + component stack logging in ErrorBoundary componentDidCatch in react-app/src/components/ErrorBoundary.jsx

- [x] T055 Update CSP to allow Google OAuth domains (script-src/connect-src/frame-src) in traefik/dynamic.yml
- [x] T056 Validate CSP changes in docs by adding a troubleshooting section in docs/CONFIG.md

- [x] T057 [P] Move inline theme init from react-app/public/index.html to external script file react-app/public/theme-init.js
- [x] T058 Update index.html to reference theme-init.js in react-app/public/index.html

- [x] T059 Ensure production builds inject REACT_APP_GOOGLE_CLIENT_ID via deploy configuration in development.docker.yml
- [x] T060 Ensure production builds inject REACT_APP_GOOGLE_CLIENT_ID via deploy configuration in digital_ocean/app_spec.yaml

- [x] T061 Add cache guidance for index.html vs hashed assets (purge strategy) in docs/DEPLOY.md
- [x] T062 Add a mobile regression checklist (iOS Safari + Android Chrome + dark mode) in docs/RELEASE.md
- [ ] T063 (Deferred future feature; inactive) Build a first-party frontend reliability
      monitor instead of Sentry or another third-party telemetry service. Before any
      runtime enablement, specify and test data minimization, recursive secret and personal
      data redaction, authenticated owner-only access, tenant isolation, bounded retention,
      storage encryption, rate and volume limits, alert deduplication, network-egress/CSP
      boundaries, monitor failure isolation, deletion/export behavior, backup/restore, and
      visible degraded-state reporting. Activation requires a separate reviewed Spec-Kit
      feature and explicit approval; this deferred task grants no collection or external
      transmission authority.

---

## Dependencies & Execution Order

### Phase Dependencies

- Setup (Phase 1) → Foundational (Phase 2) → User Stories (Phase 3+) → Integration → Polish

User story dependencies:

- US1 depends on Phase 2 (tokens + early hydration)
- US2 depends on Phase 2; can proceed in parallel with US1 after Phase 2, but final UI review should include both
- US3 depends on Phase 2 and US2 components (AppShell composes header/sidebar/content)

Parallel opportunities:

- Within Phase 2, T006–T012 can be split across styling vs Storybook wiring
- Within each user story, tasks marked [P] can be assigned to different owners (tests, components, stories)

---

## Parallel Execution Examples

User Story 1 parallel bundle:

- T014, T015, T016, T017 (tests/stories)
- T020 (ThemeToggle UI) can proceed while T018/T019 is in progress

User Story 2 parallel bundle:

- T029–T034 (glass components) in parallel
- T023–T028 (tests/stories) in parallel
- T036–T037 (home sections) in parallel

---

## Implementation Strategy

MVP scope: Phase 1 + Phase 2 + US1 only.

Incremental delivery:

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

1. Land Foundation (Phase 1–2) and validate styling + theme hydration
2. Ship US1 (toggle + persistence + a11y) and validate independently
3. Ship US2 (component library + Home composition) and validate independently
4. Ship US3 (calc-driven AppShell) and validate independently
5. Apply Polish tasks (including Speckit production hardening backlog)
