# Implementation Plan: React Glass UI System + App Shell

**Branch**: `[002-react-design]` | **Date**: 2026-01-11 | **Spec**: specs/002-react-design/spec.md
**Input**: Feature specification from specs/002-react-design/spec.md

## Summary

Design and ship a cohesive glassmorphism UI system and calc-driven App Shell in the React frontend. This feature is frontend-only: no backend/auth or API contract changes. Theming persists via a client cookie with backend override when authenticated. Accessibility (WCAG 2.1 AA), Storybook coverage, RTL + Playwright tests, and CSS `calc()`-first layout discipline are mandatory.

## Technical Context

**Language/Version**: JavaScript (React 18), Node 18 (repo-default)  
**Primary Dependencies**: React, Storybook, React Testing Library, Playwright, jest-axe; backend present (Django, FastAPI) but unchanged for this feature  
**Storage**: N/A (frontend-only; theme stored via client cookie; backend profile override when authenticated)  
**Testing**: RTL + jest-axe (unit/accessibility), Storybook (visual contracts), Playwright (E2E), CI via deploy script AllTests  
**Target Platform**: Web (evergreen browsers: Chrome/Edge/Safari/Firefox)  
**Project Type**: Web application (frontend + backend present; this feature touches frontend)  
**Performance Goals**: Minimal layout shift (≤ 5%), instant theme toggle (< 1s), smooth animations with reduced-motion respected  
**Constraints**: CSS `calc()` layout discipline; no JS layout math; WCAG 2.1 AA; vector-only icons; no auth or API changes  
**Scale/Scope**: Public Home Page + reusable glass component library; no new API endpoints

## Constitution Check

_GATE: Must pass before Phase 0 research. Re-check after Phase 1 design._

- Test-First (TDD): Plan includes RTL/axe/Storybook/Playwright; CI enforces tests — PASS
- Environment Parity: Docker Compose topology used; dev mimics prod-like — PASS
- Container-First, Compose-First: Services run via Compose with health checks — PASS
- Single-Entrypoint Ops: Deploy/update/test via digital_ocean/scripts/powershell/deploy.ps1 — PASS
- Observability: Deploy produces artifacts under local_run_logs — PASS
- Architecture: Django is canonical domain model, FastAPI mirrors API, React as client — NO CHANGE — PASS
- Security: HTTPS enforced, defense-in-depth headers — unchanged — PASS
- TLS Policy: Traefik staging certificates only in prod-like simulation — PASS (no change requested)

No violations detected. Proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/002-react-design/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
└── tasks.md (Phase 2 tool)
```

### Source Code (repository root)

```text
backend/
├── django/
│   ├── common/
│   ├── users/
│   └── project/
├── api/        # FastAPI service
│   ├── routes/
│   ├── services/
│   └── tests/

frontend/
└── react-app/
    ├── src/
    │   ├── components/
    │   ├── pages/
    │   └── services/
    ├── e2e/
    └── storybook-static/

ops/
└── digital_ocean/
    ├── scripts/
    ├── contracts/ (infra)
    └── tests/

tests/
└── e2e/ (Playwright runner in react-app)
```

**Structure Decision**: Web app with existing backend and frontend; this feature modifies only `react-app` UI (components/pages) and associated tests/docs.

## Complexity Tracking

No constitutional violations; section not applicable.

## Design Integration (Phase 9)

- Source bundle: c:\Users\theju\Documents\coding\website_build\base2\junk\idea\
- Design README: c:\Users\theju\Documents\coding\website_build\base2\junk\idea\README.md
- Tasks: See c:\Users\theju\Documents\coding\website_build\base2\specs\002-react-design\tasks.design-integration.md
- Mapping: `shadcn/ui` primitives → glass components (`GlassButton`, `GlassInput`, `GlassCard`, `GlassTabs`, `GlassModal`)
- Asset policy: Vector-only (SVG/WebP). Unsplash photos noted in design ATTRIBUTIONS, but not shipped.

### UI Mapping Table (Design → Glass)

- header.tsx → GlassHeader.tsx (adds public search input when `title="Home"`)
- hero.tsx → HomeHero.jsx
- features.tsx → HomeFeatures.jsx
- visual-section.tsx → HomeVisual.jsx (vector-first assets: hero.svg, mesh backgrounds)
- trust-section.tsx → HomeTrust.jsx
- footer.tsx → HomeFooter.jsx
- ui/button.tsx → GlassButton.tsx
- ui/card.tsx → GlassCard.tsx
- ui/input.tsx → GlassInput.tsx
- ui/tabs.tsx → GlassTabs.tsx
- ui/dialog.tsx → GlassModal.tsx
