# Design Port Final Review Checklist — React Glass UI System + App Shell

**Purpose**: Final verification that the Figma-derived design bundle under `junk/idea/` has been correctly integrated into the `react-app/` glass UI system and App Shell.

## Design Port Review

- [x] Source design inventory documented in `react-app/src/styles/README-design-port.md`
- [x] Global style import order is `tokens.css` → `background.css` → `glass.css`
- [x] Mesh/gradient background is present in light/dark with reduced-motion guards
- [x] Sidebar + drawer sizing uses tokens and is capped at `20vw` (no JS layout math)
- [x] App Shell layout uses CSS `calc()` for header/footer/content heights and includes safe-area insets
- [x] Mobile drawer behavior: hidden-by-default, overlay click + ESC close, scroll lock, focus management
- [x] Header menu toggle exposes `aria-controls` + `aria-expanded` and uses inline SVG icon
- [x] Modal parity: overlay click close + ESC close + close button inline SVG; scroll lock + focus restoration
- [x] Storybook includes `GlassHeader` and `GlassSidebar` stories for public/app and mobile/desktop states
- [x] Jest tests pass with global 100% coverage thresholds enforced
