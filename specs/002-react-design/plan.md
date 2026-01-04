# Implementation Plan: React Glass UI System + App Shell

**Branch**: `[002-react-design]` | **Date**: 2026-01-04 | **Spec**: specs/002-react-design/spec.md
**Input**: Feature specification from `specs/002-react-design/spec.md`

**Note**: Generated via `/speckit.plan` workflow.

## Summary

Deliver a glassmorphism-forward design system and calc-driven App Shell for the React app, with reusable glass components, persistent theming, accessibility (WCAG 2.1 AA), Storybook coverage, and zero backend/auth contract changes. The technical approach uses CSS variables and `calc()` for layout, inline SVG icons (no raster), transform-only animations, and component-scoped styles without silent global overrides.

## Technical Context

**Language/Version**: JavaScript (React 18, Create React App) — TypeScript adoption NEEDS CLARIFICATION  
**Primary Dependencies**: React, react-router-dom, Storybook; Tailwind presence in lockfile — usage policy NEEDS CLARIFICATION (no replacement/removal per guardrail)  
**Storage**: N/A (frontend-only feature; theme preference via local persistence)  
**Testing**: React Testing Library, Storybook interaction tests, Playwright e2e (existing)  
**Target Platform**: Web SPA served via Nginx behind Traefik  
**Project Type**: Web application (frontend + backend present; this feature is frontend-only)  
**Performance Goals**: 60 fps animations; minimal layout shift (≤ 5% during resize); fast theme toggle (< 1s)  
**Constraints**: No JS layout math where CSS `calc()` applies; WCAG 2.1 AA; no raster icons; no backend/auth changes; `.dark` class theming  
**Scale/Scope**: Design system components (7 core), App Shell (4 regions), Storybook stories for components and compositions

## Constitution Check

_GATE: Must pass before Phase 0 research. Re-check after Phase 1 design._

- Test-First: Plan includes Storybook states and RTL tests for components; Playwright e2e remains intact.
- Environment Parity: No topology changes; SPA continues behind Traefik/Nginx.
- Container/Compose-first: No service additions; dev/prod parity unaffected.
- Single-entrypoint ops: No changes to deployment scripts; frontend updates use existing pipelines.
- Observability: No operational changes required; documentation updates included.

Status: PASS (no violations). Re-check post-design.

Post-Design Re-check:

- Confirmed no API/auth changes; contracts/openapi.yaml documents status.
- Documentation updated: `quickstart.md`, `data-model.md`, `research.md`.
- Tests planned via Storybook and RTL; e2e intact.

## Project Structure

### Documentation (this feature)

```text
specs/002-react-design/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── contracts/           # Phase 1 output
```

### Source Code (repository root)

```text
react-app/
├── src/
│   ├── components/        # New: glass components
│   ├── pages/
│   ├── services/
│   └── App.css            # Glass tokens; calc-based layout variables
└── stories/               # Storybook stories for components/compositions (location may be src)

backend (Django/FastAPI): no changes in this feature
```

**Structure Decision**: Implement within existing `react-app` project under `src/components` with Storybook stories alongside or under `src`. No backend changes; contracts directory documents “no API changes”.

## Complexity Tracking

No constitution violations to justify.
