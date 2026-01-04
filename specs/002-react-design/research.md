# Phase 0 Research — React Glass UI System + App Shell

**Branch**: 002-react-design
**Date**: 2026-01-04

## Unknowns & Decisions

### 1) TypeScript Adoption

- Decision: Stay on JavaScript for this feature; defer TS migration.
- Rationale: Minimize scope; CRA setup is JS; contracts unchanged.
- Alternatives considered: Incremental TS adoption in components — rejected for now due to scope and time.

### 2) Tailwind Usage Policy

- Decision: Use CSS variables and component-scoped styles; do not add/remove Tailwind. If Tailwind utilities exist, they may be used sparingly without introducing global overrides.
- Rationale: Guardrail: no Tailwind replacement/removal; existing lockfile includes Tailwind; current app uses CRA CSS.
- Alternatives: Full Tailwind adoption — rejected (scope, risk, guardrail).

### 3) Theme Persistence & Early Hydration

- Decision: Persist theme via `localStorage` key `theme` and apply `.dark` class on initial render using a minimal inline script to avoid flicker.
- Rationale: Common pattern; fast; no backend changes.
- Alternatives: Cookie + server-side render — rejected (no SSR in CRA).

### 4) Glass Tokens & Layout Discipline

- Decision: Define CSS variables for glass (colors, blur, border, shadow) and layout tokens using `calc()` per spec (header/footer/sidebar/content).
- Rationale: Ensures consistency and guardrail compliance.
- Alternatives: JS layout math — rejected by hard guardrails.

### 5) Icon System (SVG)

- Decision: Inline SVG icons with `aria-label` and `role="img"` for accessibility.
- Rationale: Guardrail: no raster; accessibility requirements.
- Alternatives: Icon fonts or raster sprites — rejected.

### 6) Accessibility & Reduced Motion

- Decision: Use `prefers-reduced-motion` to reduce animations; transform-only transitions; focus-visible 3px neon glow.
- Rationale: WCAG 2.1 AA; performance and user comfort.
- Alternatives: Complex motion — rejected.

## Best Practices & Patterns

- CSS variables for theming and glass tokens; `.dark` toggles variable values.
- Backdrop blur via `backdrop-filter`; ensure fallbacks maintain translucency.
- Use `calc()` for all sizing; avoid JS-based measurement.
- Storybook stories demonstrate states: light/dark, hover/focus, disabled/error.
- RTL tests for keyboard navigation and focus-visible behavior.

## Consolidated Decisions

- Decision: JS-only components; no TS for this feature.
- Rationale: Keep scope contained; deliver design system quickly.
- Alternatives considered: TS migration.

- Decision: No API changes; contracts document "no new endpoints".
- Rationale: Frontend-only feature; guardrails prohibit backend/auth changes.
- Alternatives: Add endpoints — rejected.
