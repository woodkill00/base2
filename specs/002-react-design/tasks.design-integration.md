---
description: 'Additional tasks for integrating Figma Home Page Design from junk/idea into React glass design system'
---

# Tasks: Design Integration — Build Home Page Design

**Input**: Design bundle under junk/idea (README.md, components in src/app/components/ and src/app/components/ui/)
**Prerequisites**: specs/002-react-design/plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Mandatory — RTL, jest-axe, Storybook, Playwright.

**Organization**: Tasks grouped by phases; include exact absolute file paths.

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
- [ ] T101 [P] RTL: Home page sections render and keyboard navigation works under c:\Users\theju\Documents\coding\website_build\base2\react-app\src\_\_tests\_\_\home\home-page.test.jsx
- [ ] T102 [P] Playwright: Verify black backdrop, glass fidelity, and calc sizing across sections in c:\Users\theju\Documents\coding\website_build\base2\react-app\e2e\home-style.spec.ts
- [ ] T103 [P] Accessibility (jest-axe): focus-visible and ≥4.5:1 contrast across design sections in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\_\_tests\_\_\home\home-a11y.test.jsx
- [ ] T104 [P] RTL: Verify `ImageWithFallback` loads vector-first and applies fallback cleanly in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\_\_tests\_\_\common\image-fallback.test.tsx
- [ ] T105 [P] Storybook: Verify `GlassModal` + sub-page modal interaction parity with design in c:\Users\theju\Documents\coding\website_build\base2\react-app\src\stories\glass\ModalDesignParity.stories.tsx

### Documentation & Attributions

- [ ] T106 [P] Add ATTRIBUTIONS note referencing shadcn/ui MIT and Unsplash license (design-only) in c:\Users\theju\Documents\coding\website_build\base2\docs\DEVELOPMENT.md and c:\Users\theju\Documents\coding\website_build\base2\specs\002-react-design\quickstart.md
- [ ] T107 [P] Link to design bundle README in c:\Users\theju\Documents\coding\website_build\base2\specs\002-react-design\plan.md and clarify no backend changes required

**Checkpoint**: Home page design integrated into glass system; stories and tests validate fidelity, accessibility, and layout discipline without raster dependencies.
