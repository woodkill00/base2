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

- Decision: Persist theme via client cookie `theme=light|dark`; backend profile (authenticated) overrides; fallback to `prefers-color-scheme`. Apply root theme class before React mounts. Do not use localStorage.
- Rationale: Aligns with governance (no sensitive storage), enables cross-subdomain consistency, and prevents flicker without SSR.
- Alternatives considered: localStorage (rejected: governance/policy), SSR or HttpOnly cookie (rejected: not using SSR; client needs read access).

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
- Backdrop blur via `backdrop-filter`; if unsupported, fallback to semi-transparent backgrounds with subtle border + shadow (no blur).
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

### Cookie & Browser Support Details

## Home Page (Public) — Decisions

- Decision: Public App Shell (Header + Content + Footer, no sidebar) with calc-first sizing and mesh/gradient background to enhance glass visibility.
- Rationale: Spec requires public landing experience without auth or API; avoids layout regressions and keeps performance high.
- Alternatives considered: Sidebar variant on Home (rejected: spec says no sidebar); flat sections (rejected: glass-only sections).

- Decision: Sections and compositions
  - Hero: centered `GlassCard` with clamp-based `h1`, description, primary/secondary CTAs, optional glass input; idle float + hover elevation + CTA pulse.
  - Feature Grid: 3–6 `GlassCard` items using `repeat(auto-fit, minmax(calc(300px - 2rem), 1fr))` grid; icons 24x24; hover lift; keyboard focusable.
  - Visual/Illustration: abstract glass UI illustration (SVG/WebP), lazy-loaded, framed by a glass container; no layout dependency.
  - Trust/Value Props: 4–6 small glass pills/cards; text-only or icon+text.
  - Footer: glass container with minimal links and SVG social icons.
- Rationale: Matches wireframe; demonstrates glass system comprehensively.

- Decision: Assets
  - Vector-only (SVG/WebP); no raster icons or stock photography.
  - Use provided prompts (Nano-Banana) to generate hero illustration, background meshes (light/dark), decorative glass shapes.
- Rationale: Performance and fidelity; governance forbids raster icons.

- Unknowns resolved for implementation: - Decision: Hero copy and CTA labels — use placeholders - Title: "Elegant Glass Interface" - Subtitle: "Fast, accessible, and visually compelling UI system" - Primary CTA: "Get Started" - Secondary CTA: "Learn More"
  Rationale: Allows shipping without blocking on product wording; easy to update later.
  Alternatives considered: Await final copy — rejected to avoid blocking feature delivery.

      - Decision: Illustration selection and dimensions — initial defaults
      		- Format: SVG (preferred) or WebP fallback
      		- Dimensions: 1200×600 (responsive scale within glass frame)
      	Rationale: Matches typical hero aspect, keeps assets crisp; responsive within tokens.
      	Alternatives considered: Raster PNG/JPEG — rejected by governance; different aspect ratios — can be iterated later.

      - Decision: Background mesh palette specifics — derive from theme tokens
      		- Light: subtle mesh using `rgba(255,255,255,0.25)` frosted overlays + pastel accents
      		- Dark: subtle mesh using `rgba(0,0,0,0.4)` frosted overlays + neon accents
      	Rationale: Aligns with glass tokens; avoids introducing new global palettes.
      	Alternatives considered: External design kit palettes — deferred; ensure consistency first.

- Decision: Cookie attributes: Secure=true, SameSite=Lax, HttpOnly=false, Path=/, Domain=.woodkilldev.com, Expires=180 days.
- Rationale: Safe defaults for a non-sensitive theme preference; cross-subdomain consistency; reasonable TTL.
- Alternatives considered: Session-only cookie (rejected: user convenience); host-only domain (rejected: subdomain inconsistency); longer TTL (365d) or shorter (90d) — balanced at 180d.
