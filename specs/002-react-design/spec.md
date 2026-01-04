# Feature Specification: React Glass UI System + App Shell

**Feature Branch**: `[002-react-design]`  
**Created**: 2026-01-04  
**Status**: Draft  
**Input**: User description: "React glassmorphism design system and App Shell: cohesive glass UI components, calc-based layout, accessibility, and Storybook coverage."

## Clarifications

### Session 2026-01-04

- Q: Theme persistence & hydration → A: Use backend profile setting when authenticated; otherwise read a client cookie (`theme=light|dark`) on initial paint; if neither exists, fall back to `prefers-color-scheme`. Do not use localStorage.
- Q: Theme cookie attributes → A: Client-readable `theme` cookie with `Secure=true`, `SameSite=Lax`, `HttpOnly=false`, `Path=/`.
- Q: Theme cookie domain scope → A: Set cookie domain to `.woodkilldev.com` to cover all subdomains consistently.
- Q: Browser support & blur fallback → A: Support evergreen browsers (Chrome/Edge/Safari/Firefox). If `backdrop-filter` is unsupported, fallback to semi-transparent backgrounds with subtle border + shadow (no blur) to maintain fidelity.
- Q: Cookie expiration TTL → A: 180 days.

## User Scenarios & Testing _(mandatory)_

### User Story 1 - Toggle Theme + Glass Fidelity (Priority: P1)

Users can toggle between light and dark themes and see consistent glassmorphism across the app shell (header, sidebar, content, footer) with clear frosted translucency, backdrop blur, depth, hover elevation, and focus-visible glow.

**Why this priority**: Establishes the foundation of the design system and validates glass fidelity across core UI, enabling future screens to inherit consistent visuals.

**Independent Test**: Verify theme toggle persists and updates UI instantly; visually confirm glass acceptance checklist across app shell components.

**Acceptance Scenarios**:

1. **Given** the app loads, **When** the user toggles theme, **Then** the app shell updates instantly and glass effects remain perceivable in both themes.
2. **Given** keyboard navigation, **When** focus moves to interactive elements, **Then** a 3px neon glow is visible and contrast meets ≥ 4.5:1.

---

### User Story 2 - Compose Screens with Glass Components (Priority: P2)

Designers/developers can compose screens using a reusable glass component library (cards, buttons, inputs, tabs, modals, spinners, skeletons) without layout assumptions baked into components.

**Why this priority**: Enables scalable UI development and reuse; reduces duplication; supports a maintainable design system.

**Independent Test**: In isolation, render each component and confirm API contracts, accessibility states, and visual fidelity via Storybook.

**Acceptance Scenarios**:

1. **Given** the component library, **When** a `GlassCard` is rendered with `interactive` state, **Then** hover elevation increases and focus-visible shows a neon glow.
2. **Given** `GlassModal` open, **When** `onClose` is triggered by ESC or backdrop click, **Then** the modal closes and focus returns to the triggering element.

---

### User Story 3 - Calc-Driven Responsive App Shell (Priority: P3)

The layout shell sizes header, sidebar, content, and footer using CSS calc discipline and responsive constraints with no JavaScript layout math.

**Why this priority**: Guarantees predictable, efficient layout behavior and performance; reduces complexity and regressions.

**Independent Test**: Resize viewport and validate header/footer heights, sidebar width constraints, and content height all computed via CSS `calc()` with expected min/max bounds.

**Acceptance Scenarios**:

1. **Given** a desktop viewport, **When** width changes, **Then** the sidebar remains within 320–400px and reflects `calc(100vw * 0.25)` bounds.
2. **Given** content area, **When** height changes, **Then** content height equals `calc(100vh - header - footer)` and remains stable with minimal layout shift.

---

### Edge Cases

- Reduced-motion user preference: animations respect reduced motion and use transform-only for performance.
- Low-end devices: backdrop blur is present but performance remains acceptable; fallbacks do not remove glass fidelity.
- High-contrast requirements: ensure translucent glass still meets ≥ 4.5:1 contrast for key text and controls.
- Accessibility labels: inline SVG icons include `aria-label` and `role="img"`; missing icon labels are surfaced as defaults.
- Blur unsupported: when `backdrop-filter` is not available, use semi-transparent backgrounds with subtle borders and shadows; avoid heavy blur emulation overlays.

## Requirements _(mandatory)_

### Functional Requirements

**FR-001**: Provide a persistent theme toggle that switches between light and dark themes; preference persists across sessions and applies on initial load via a client cookie (`theme=light|dark`). On authenticated sessions, a backend profile setting supersedes the cookie. If neither is present, default to `prefers-color-scheme` and set the root theme class before React mounts. LocalStorage is not used. Cookie attributes: `Secure=true`, `SameSite=Lax`, `HttpOnly=false`, `Path=/`, `Domain=.woodkilldev.com`, `Expires=180 days`.

- **FR-001**: Provide a persistent theme toggle that switches between light and dark themes; preference persists across sessions and applies on initial load via a client cookie (`theme=light|dark`). On authenticated sessions, a backend profile setting supersedes the cookie. If neither is present, default to `prefers-color-scheme` and set the root theme class before React mounts. LocalStorage is not used.
- **FR-001**: Provide a persistent theme toggle that switches between light and dark themes; preference persists across sessions and applies on initial load via a client cookie (`theme=light|dark`). On authenticated sessions, a backend profile setting supersedes the cookie. If neither is present, default to `prefers-color-scheme` and set the root theme class before React mounts. LocalStorage is not used. Cookie attributes: `Secure=true`, `SameSite=Lax`, `HttpOnly=false`, `Path=/`.
- **FR-001**: Provide a persistent theme toggle that switches between light and dark themes; preference persists across sessions and applies on initial load via a client cookie (`theme=light|dark`). On authenticated sessions, a backend profile setting supersedes the cookie. If neither is present, default to `prefers-color-scheme` and set the root theme class before React mounts. LocalStorage is not used. Cookie attributes: `Secure=true`, `SameSite=Lax`, `HttpOnly=false`, `Path=/`, `Domain=.woodkilldev.com`.
- **FR-002**: Implement an app shell with header, sidebar, content, and footer sized using CSS `calc()` with the following targets: header ≈ `calc(100vh * 0.08)` (min 64px), footer ≈ `calc(100vh * 0.08)` (min 56px), sidebar ≈ `calc(100vw * 0.25)` constrained between 320–400px, content = `calc(100vh - header - footer)`.
- **FR-003**: Deliver a reusable glass component library including `GlassCard`, `GlassButton`, `GlassInput`, `GlassTabs`, `GlassModal`, `GlassSpinner`, and `GlassSkeleton` with clear, minimal APIs and ARIA support.
- **FR-004**: Meet WCAG 2.1 AA: keyboard navigation everywhere, focus-visible 3px neon glow, accessible labels for inline SVG icons, and contrast ≥ 4.5:1 for key text and controls.
- **FR-005**: Provide loading states: skeletons and shimmer effects that maintain glass fidelity and avoid layout jank.
- **FR-006**: Publish Storybook stories for all components and compositions (AppShell, Modal open, Responsive grid) demonstrating light/dark, hover/focus, disabled/error (where applicable) without console warnings.
- **FR-007**: Enforce CSS calc–first layout discipline; no JavaScript-based layout calculations where CSS `calc()` is possible.
- **FR-008**: Use only vector icons (SVG); no raster icons are introduced.
- **FR-009**: Do not change authentication flows, token storage, routing behavior, or backend/API contracts; frontend-only visual and structural changes.
- **FR-010**: Satisfy the visual acceptance checklist: frosted translucency, backdrop blur, border + shadow depth, hover elevation, focus neon glow, dark mode fidelity, no solid/opaque containers.

### Constraints and Assumptions

- No introduction of new state management libraries; reuse existing patterns.
- No silent global CSS overrides; component-scoped styles and explicit tokens.
- Glassmorphism palette aligns with: Light frosted `rgba(255,255,255,0.25)`, Dark frosted `rgba(0,0,0,0.4)`.
- Layout respects safe-area insets via `calc(100vh - env(safe-area-inset-top) - env(safe-area-inset-bottom))` where applicable.

### Key Entities _(include if feature involves data)_

- **Theme Preference**: Represents the user’s selected theme (`light` or `dark`); persists across sessions; applied at hydration to avoid flicker.
  - Persistence mechanism: client cookie read at initial paint; backend profile (post-auth) overrides; fallback to `prefers-color-scheme`. No localStorage.
  - Cookie attributes: `Secure=true`, `SameSite=Lax`, `HttpOnly=false`, `Path=/`, `Domain=.woodkilldev.com`, `Expires=180 days`.

## Success Criteria _(mandatory)_

### Measurable Outcomes

- **SC-001**: Theme toggle updates the app shell and components with visible glass fidelity in under 1 second; preference persists across reloads.
- **SC-002**: App shell layout remains responsive: sidebar stays within 320–400px bounds across desktop widths; header/footer height targets hold with ≤ 5% layout shift during resize.
- **SC-003**: 95% of interactive elements exhibit a visible 3px focus glow and pass keyboard navigation checks across primary screens.
- **SC-004**: All component and composition stories render without errors or console warnings; reviewers can verify hover, focus, disabled, and error states.
- **SC-005**: Accessibility checks pass (WCAG 2.1 AA): contrast ≥ 4.5:1 for key text/controls; all inline SVGs include accessible labels and roles.
- **SC-006**: Visual acceptance checklist passes in both light and dark themes; no opaque containers are used.
