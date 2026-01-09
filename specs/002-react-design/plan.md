# Implementation Plan: React Glass UI System + App Shell

**Branch**: `[002-react-design]` | **Date**: 2026-01-04 | **Spec**: specs/002-react-design/spec.md
**Input**: Feature specification from `/specs/002-react-design/spec.md`

**Note**: Filled by `/speckit.plan`; augmented per clarifications (theme persistence via cookie + backend override, blur fallback).

## Summary

- Deliver a cohesive glassmorphism design system and calc-driven App Shell in React.
- Theme persistence: backend profile overrides; else client `theme` cookie; fallback `prefers-color-scheme`; no localStorage.
- Blur fallback: when `backdrop-filter` unsupported, use semi-transparent background + border/shadow (no blur).
- No backend/API changes; frontend-only visual and structural improvements with Storybook coverage and accessibility.

## Technical Context

**Language/Version**: React 18 with TypeScript; Node 18 for tooling  
**Primary Dependencies**: React, Storybook, Tailwind utilities (policy-limited), CSS variables, Playwright, React Testing Library, jest-axe  
**Storage**: N/A (frontend-only feature; cookie for non-sensitive theme)  
**Testing**: RTL + jest-axe (components), Storybook interactions, Playwright (e2e/responsive calc checks)  
**Target Platform**: Web (evergreen browsers: Chrome/Edge/Safari/Firefox)  
**Project Type**: Web application (frontend React; backend Django + FastAPI present but unchanged)  
**Performance Goals**: Layout shift ≤ 5% during resize; instant theme switch (<1s)  
**Constraints**: WCAG 2.1 AA; calc-first layout (no JS layout math); no localStorage; theme via cookie/backend override  
**Scale/Scope**: Component library (GlassCard/Button/Input/Tabs/Modal/Spinner/Skeleton) + AppShell; no API changes

Additional Decisions:

- Theme persistence order: backend profile (authenticated) > client cookie (`theme=light|dark`) > `prefers-color-scheme` fallback.
- Cookie attributes: Secure=true, SameSite=Lax, HttpOnly=false, Path=/, Domain=.woodkilldev.com, Expires=180 days.
- Blur fallback: no heavy filters; use semi-transparent backgrounds + border/shadow.
- Tailwind policy: utilities permitted; no global overrides; no plugin additions; do not replace existing CSS tokens.

## Constitution Check

_GATE: Must pass before Phase 0 research. Re-check after Phase 1 design._

- Test-First Development: PASS — tasks enforce tests-first for components, stories, and e2e.
- Environment Parity (Compose-first): PASS — no new services; uses existing Compose topology.
- Single-entrypoint operations: PASS — deployment via digital_ocean/scripts/powershell/deploy.ps1 with flags.
- Observability as a feature: PASS — artifacts reviewed post-deploy; no sensitive data; theme cookie documented.
- Frontend security governance: PASS — no tokens in localStorage; theme cookie non-sensitive; session/refresh remain HttpOnly.

Re-check Post-Design: Confirm Storybook coverage and calc-only layout remain compliant; verify accessibility and blur fallback.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
react-app/
├── src/
│   ├── components/
│   │   └── glass/                # Glass components
│   ├── app/
│   │   └── AppShell/             # Calc-driven layout shell
│   └── styles/                    # CSS variables + tokens
├── stories/                       # Component + composition stories
└── tests/                         # RTL + Storybook interactions

django/                            # unchanged domain source of truth
api/                               # unchanged FastAPI mirror contract
```

**Structure Decision**: Web application with React frontend; backend unchanged. Components under `react-app/src/components/glass`, AppShell under `react-app/src/app/AppShell`.

## Complexity Tracking

No violations required. Theme cookie is non-sensitive and adheres to governance; no new services or plugins.
