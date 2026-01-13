---
description: 'Task list for React Glass Portfolio SPA'
---

# Tasks: React Glass Portfolio SPA

**Input**: Design prompt for a single-page portfolio with glassmorphism, Tailwind, Framer Motion
**Prerequisites**: plan.md and spec.md not provided; tasks derived from prompt requirements

**Tests**: Not requested. Independent test criteria provided for each user story. No test tasks included.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- Frontend app located in `react-app/`
- Source code under `react-app/src/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Initialize styling/animation tooling and base theme/glass utilities

- [x] T001 Add Tailwind CSS and Framer Motion dependencies in react-app/package.json
- [x] T002 Create Tailwind config with dark-mode 'class' and glass utilities in react-app/tailwind.config.js
- [x] T003 [P] Create PostCSS config for Tailwind in react-app/postcss.config.js
- [x] T004 [P] Integrate Tailwind directives (@tailwind base, components, utilities) in react-app/src/index.css
- [x] T005 [P] Create tokens stylesheet with clamp() design scales in react-app/src/styles/tokens.css
- [x] T006 Wire global tokens import in entry file in react-app/src/index.js

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure required by all sections (theme, layout, shared UI)

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T007 Create theme context with localStorage persistence in react-app/src/contexts/ThemeContext.js
- [x] T008 [P] Create glass UI primitives: GlassCard in react-app/src/components/glass/GlassCard.tsx
- [x] T009 [P] Create glass UI primitives: GlassButton in react-app/src/components/glass/GlassButton.tsx
- [x] T010 [P] Create ThemeToggle (sun/moon, glass pill) in react-app/src/components/glass/ThemeToggle.tsx
- [x] T011 [P] Create SectionContainer.jsx with clamp-based spacing in react-app/src/components/SectionContainer.jsx
- [x] T012 [P] Add Framer Motion variants helper in react-app/src/lib/motion.js
- [x] T013 [P] Scaffold App layout (Header/Footer placeholders, section anchors) in react-app/src/App.js
- [x] T014 [P] Add SEO meta tags and dark/light theme-color in react-app/public/index.html
- [x] T015 [P] Add focus-visible ring/glass glow styles in react-app/src/index.css
- [x] T016 Extend Tailwind theme with color tokens and typography/spacing scales in react-app/tailwind.config.js

**Checkpoint**: Foundation ready — user story implementation can now begin in parallel

---

## Phase 3: User Story 1 — Header, Theme & Hero (Priority: P1) 🎯 MVP

**Goal**: Default dark mode, fixed top glass navbar with prominent theme toggle; full-viewport hero with centered glass card, title "Woodkill Dev", subtitle, frosted search bar and blue glass "Explore" button; smooth fade-up + blur-in effects

**Independent Test**: Load page in a fresh browser profile — dark theme renders by default; toggle to light mode and refresh — selection persists; hero fills viewport (between clamp(80vh,100vh,90vh)); tab focus has visible glass glow; keyboard can activate toggle and Explore

### Implementation for User Story 1

- [x] T017 [P] [US1] Implement fixed Header with glass navbar in react-app/src/components/glass/GlassHeader.tsx
- [x] T018 [P] [US1] Integrate ThemeToggle with ThemeContext in react-app/src/components/glass/ThemeToggle.tsx
- [x] T019 [P] [US1] Create search input + Explore button in react-app/src/components/home/HomeHero.jsx
- [x] T020 [P] [US1] Implement Hero section with centered glass card in react-app/src/components/home/HomeHero.jsx
- [x] T021 [US1] Add Framer Motion fade-up + blur-in to Hero in react-app/src/components/home/HomeHero.jsx
- [x] T022 [US1] Wire Header and Hero into Home page in react-app/src/pages/Home.js

**Checkpoint**: Header + Hero fully functional with persistent theming

---

## Phase 4: User Story 2 — About & Skills (Priority: P1)

**Goal**: About section with profile image in glass circular frame, bio text, skills as glass chips (horizontal scroll on mobile, grid on desktop), accessible labels/roles

**Independent Test**: On mobile viewport, skills list scrolls horizontally with inertial scrolling; on desktop, grid shows 3-4 columns using clamp gaps; focus states visible; section animates in on scroll

### Implementation for User Story 2

- [x] T023 [P] [US2] Implement About section with glass profile frame in react-app/src/components/portfolio/About.jsx
- [x] T024 [P] [US2] Implement skills chips within About in react-app/src/components/portfolio/About.jsx
- [x] T025 [US2] Add motion and ARIA labelling to About in react-app/src/components/portfolio/About.jsx
- [x] T026 [US2] Wire About section into Home layout in react-app/src/pages/Home.js

**Checkpoint**: About section independently shippable

---

## Phase 5: User Story 3 — Projects Grid (Priority: P1)

**Goal**: Responsive projects grid (1-col mobile → 3-col desktop) of glass cards; thumbnails with glass overlay, tech tags as glass badges; hover: scale(1.05) and stronger blur/rgba; smooth 0.3s ease transitions

**Independent Test**: Resize from 360px to 1440px — grid reflows 1→2→3 columns; hover effect triggers scale and overlay intensification; keyboard tab reveals focus outlines on cards and badges

### Implementation for User Story 3

- [x] T027 [P] [US3] Create ProjectCard with glass overlay + hover in react-app/src/components/portfolio/ProjectCard.jsx
- [x] T028 [P] [US3] Create ProjectsGrid responsive layout in react-app/src/components/portfolio/ProjectsGrid.jsx
- [x] T029 [US3] Provide sample projects data inline in react-app/src/components/portfolio/ProjectsGrid.jsx
- [x] T030 [US3] Integrate Projects into Home sections in react-app/src/pages/Home.js

**Checkpoint**: Projects grid independently shippable

---

## Phase 6: User Story 4 — Contact & Social (Priority: P2)

**Goal**: Glass form container with floating label inputs, glass submit button, social icons as glass orbs; ARIA-compliant form with validation feedback

**Independent Test**: Keyboard-only user can navigate fields; invalid submission shows accessible errors; social orbs have descriptive labels; section entrance animates with motion

### Implementation for User Story 4

- [x] T031 [P] [US4] Implement ContactForm with floating labels in react-app/src/components/portfolio/ContactForm.jsx
- [x] T032 [P] [US4] Implement SocialOrbs icons row inline in react-app/src/components/portfolio/ContactForm.jsx
- [x] T033 [US4] Wire Contact section into Home layout in react-app/src/pages/Home.js
- [x] T034 [US4] Add validation + aria-invalid states to form in react-app/src/components/portfolio/ContactForm.jsx
- [x] T035 [US4] Add motion variants for Contact entrance in react-app/src/components/portfolio/ContactForm.jsx

**Checkpoint**: Contact independently shippable

---

## Phase N: Polish & Cross-Cutting Concerns

**Purpose**: Finishing touches and improvements across sections

- [x] T036 [P] Optimize clamp scales and theme tokens in react-app/tailwind.config.js
- [x] T037 Extract constants/tokens to dedicated file in react-app/src/styles/tokens.css
- [x] T038 [P] Accessibility pass (focus rings, contrast) in react-app/src/index.css
- [x] T039 [P] Update portfolio README with run/build steps in react-app/README.md
- [x] T040 Performance touch-ups (preload/prefetch as needed) in react-app/public/index.html

---

## Dependencies & Execution Order

### Phase Dependencies

- Setup (Phase 1): No dependencies — can start immediately
- Foundational (Phase 2): Depends on Setup completion — BLOCKS all user stories
- User Stories (Phase 3+): Depend on Foundational completion
  - Recommended sequence by priority: P1 → P2
  - Stories remain independently testable
- Polish (Final Phase): Depends on completion of desired user stories

### User Story Dependencies

- User Story 1 (P1): Starts after Foundational — no other story dependency
- User Story 2 (P1): Starts after Foundational — independent of US1
- User Story 3 (P1): Starts after Foundational — independent of US1/US2
- User Story 4 (P2): Starts after Foundational — independent of others

### Within Each User Story

- Shared UI/components first, then composition in App
- Motion/animations layered after structural components
- Validate a11y (roles, focus, labels) before polish

### Parallel Opportunities

- All [P]-marked tasks can run concurrently (different files)
- After Foundational, US1–US4 can be staffed in parallel

---

## Parallel Examples

### Parallel Example: User Story 1

- Tasks in parallel:
  - T017 [US1] Header.jsx
  - T019 [US1] SearchBar.jsx
  - T020 [US1] Hero.jsx

### Parallel Example: User Story 2

- Tasks in parallel:
  - T023 [US2] About.jsx
  - T024 [US2] SkillsChips.jsx

### Parallel Example: User Story 3

- Tasks in parallel:
  - T027 [US3] ProjectCard.jsx
  - T028 [US3] ProjectsGrid.jsx

### Parallel Example: User Story 4

- Tasks in parallel:
  - T031 [US4] ContactForm.jsx
  - T032 [US4] SocialOrbs.jsx

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1 (Header + Hero + Theme)
4. STOP and VALIDATE: Confirm persistence, accessibility, and motion
5. Deploy/demo if ready

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add US1 → Test independently → Deploy/Demo (MVP)
3. Add US2 → Test independently → Deploy/Demo
4. Add US3 → Test independently → Deploy/Demo
5. Add US4 → Test independently → Deploy/Demo

---
