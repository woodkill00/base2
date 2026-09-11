# Implementation checkpoint — 2026-09-11

Branch: `109-unified-layout-visual-contract`. This is a local opt-in prototype,
not a completed release. Build flag: `VITE_LAYOUT109_PREVIEW=true`; absent that
flag the existing layouts and Home controls remain in use.

## Implemented and exercised

- All 30 route patterns inventoried; six original captures saved under
  `.artifacts/layout-109/before-109/` before implementation.
- Shared AppShell left/main/right tracks, mobile drawers, measured header offsets,
  focus trap/restoration, Escape, inert background, scroll cleanup and skip link.
- Home, Dashboard and Settings prototype; duplicate app navigation removed,
  existing Obsidian tokens used and nested settings categories preserved.
- Home viewport-based spacing, fixed-height nested clipping and decorative-tab
  overflow repaired in the prototype. Default Home behavior is preserved.
- `candidate-109-8`: 27 Chromium cases passed across nine widths from 320 to 1920px.
  Screenshots were actually inspected. 49 focused unit/compatibility tests passed.
  ESLint passed for the changed component/page files.
- Private before/after gallery: `.artifacts/layout-109/review.html`.

## Remaining acceptance work

The task ledger stays open until each task's full evidence is available. T003–T012
still need full Home palette/movement/utility/footer parity, permission/module
shortcuts, breakpoint and route-change focus edge cases, overlay stacking,
functional/loading/error states and accessibility coverage. Current captures are
early design-review material, not completion of the formal T013 owner checkpoint.
Then T014–T028 cover remaining pages, RTL/theme/zoom, immutable source-bound visual
evidence, negative controls, CI/coverage, release gate, rollback and approved live review.

The global typecheck is not green: new inert/query-option typing problems were
corrected, but errors remain in untouched legacy test/type-support files. Track
these under T024; do not suppress them. The frontend browser fixture blocks external
network and uses synthetic data; it does not prove production API functionality.
No full release gate, deployment, cloud launch or inferred visual approval occurred.

Failure evidence remains in `.artifacts/layout-109/` and `/tmp/f109-*.log`.
Attempts 3/5 exposed nested clipping; attempt 6 isolated the decorative overflow.
Diagnostic attempt 4 matched no tests and is not passing evidence. A retry never
replaces an earlier failure. Final exact-source release evidence is still required.
