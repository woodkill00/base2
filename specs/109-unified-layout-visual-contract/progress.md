# Implementation checkpoint — 2026-09-11

## Current release status

PR #68 merged into `main` at `d58dc910d026fc42dc148111c1d2ccd487204d99`.
Its tree exactly matches tested candidate `2680b73532dc828b1643dd21558cc4eb6b5b3a06`.
The complete gate passed at
`.artifacts/complete-gate/20260911T155049Z-2404620/result.json`, including all 106
layout cases. All hosted PR checks passed and the source was clean before merge.
Current-source stability repetitions passed ten runs per registered suite.

A 60-minute restricted preview of the merged commit is being launched through the
supported entrypoint; owner live visual review and live acceptance are still
pending. Media remains disabled, not passed. The follow-up live-test alignment
is recorded in analysis cycle 8. Earlier progress sections below are historical;
their remaining-work statements are superseded by this status where evidence is
explicitly recorded. Lifecycle closeout and owner approval are not yet claimed.

## All-page integration update

Following the owner's direction to complete all pages, the opt-in layout now
resolves the current route automatically in AppShell. PublicShell delegates to
the same structure. This covers public/content/search, login/signup/recovery,
invitation, Dashboard/Settings and first-party admin/workspace/media/operations
pages, including not-found and disabled-module views. Existing guards and
redirects remain unchanged. Global navigation appears once, with module- and
permission-filtered destinations. Nested paths retain the selected parent link.

An all-page screenshot review found oversized titles inherited from Home; scoped
container-relative heading tokens now prevent this, with an explicit regression.
Typed declarations cover the existing JS authentication/navigation boundary;
they do not change credentials or authorization behavior.

Evidence: 88 Chromium cases in `all-pages-final-3`, covering the representative
nine-width matrix, guest/auth pages, German/Arabic content, authenticated tool
error states, `/account` redirect and five protected-route denial cases. The
browser report includes screenshot attachments. 56 focused compatibility/unit
tests pass. These service-unavailable fixtures prove layout resilience, not live
data flows; disabled optional modules are tested as disabled, not as active apps.
Existing legacy global typecheck failures remain outside the changed files.
Final visual review also restored the Administration and Accept Invitation titles
previously supplied by the removed header; the route-family suite now requires
exactly one main-region heading. The report is at
`.artifacts/layout-109/all-pages-final-3-report/index.html`.

Attempt-directory protection refuses reuse before running browsers. Its first
version also rejected worker imports; `all-pages-final` retains that failure
(2 failed / 86 not run), and the corrected runner checks reuse only at controller
startup while sharing one attempt ID with workers. No failure is relabeled green.
An explicit reuse attempt was rejected before browser startup; the existing HTML
report's SHA-256 was unchanged before and after rejection.

This extends implementation scope, not final visual approval. The build remains
opt-in until full Home-control parity and the remaining release gates are satisfied.
The earlier representative checkpoint below is retained as history.

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

# Release-gate repair checkpoint — 2026-09-11

The first complete gate on `0a6510e` failed, correctly preventing release:
Operations and Media source-bound reviews were stale, and critical-glass coverage
was below its strict floor. Its complete evidence is retained at
`.artifacts/complete-gate/20260911T151208Z-2331907/`.

Cycle 7 repairs add routed-mode, ResizeObserver, focus/resize, context event and
fallback unit cases. All 314 frontend tests now pass; critical-glass lines,
statements, functions and branches are each 100%. The existing coverage-policy
check passes without floor changes. No claim of exhaustive unknown-defect coverage
is implied.

Operations and Media release matrices now explicitly enable the deployed layout.
The Media matrix exposed and reproduced a real modal isolation bug: old selectors
omitted the shared header/rails/footer. The new regression and browser assertions
verify these are inert while the detail dialog is open and restored afterward.
Privacy footer touch targets are now 44px, footer items vertically centered, and
shared heading rules outrank page-local heading CSS. Legacy shell isolation stays
supported. Source-bound reviews now also watch shared CSS, route policy, runtime
and profile data.

Actual desktop/mobile Operations, degraded-state, Media and RTL dialog captures
were inspected. Intentional shared-shell baseline changes retain prior failure
artifacts under `operations-red-109`, `media-red-109`, and `media-review-109`.
`final-repair-layout` passed all 103 cases; `operations-verified-109` passed all
22 applicable cases (20 explicitly out-of-matrix states skipped).
`media-verified-109` passed all 24 applicable cases (12 explicitly out-of-matrix
modal cases skipped), without snapshot updates. Media review is bound to tested
source commit `4ca69d0452cc9d18407845f1efc55723f0470312` after final reflow checks.
The 200%-text capture ceiling caught an actual narrow-card defect. The repaired
text-aware 80rem container threshold reduced that Operations capture from 11106px
to 4877px, retaining the existing 5000px ceiling. CSS and drawer logic now agree
on actual available width and root text size. The final Operations/Media matrices
passed 22/24 applicable cases, `container-final` passed 103 layout cases, and an
additional Chromium scrolled-drawer check passed. Full frontend validation now
passes 315 tests with 100% critical-glass coverage; coverage policy passes.
Automated
visual acceptance remains separate from the owner's final design review.

# Release preparation checkpoint — 2026-09-11

Implemented Home advanced controls and rich footer integration, visible focus on
drawer-to-desktop resize, collapsed-details keyboard filtering, and responsive
footer sizing (including Arabic at 200% CSS zoom). Existing delayed Home snapping
does not run in shared-layout mode. Both supported Compose builds now propagate
the layout switch, with a deployment regression test and documented rollback.

Validation this batch:

- `release-full-1`: 90/90 Chromium page and control cases passed.
- `keyboard-red-1`: nine failures across three browsers reproduced focus/zoom bugs;
  retained. `keyboard-fix-2`: 12/12 cross-browser cases passed after repairs.
- `release-evidence-1`: 93/103 passed; early structural assertions exposed a fixture
  readiness race. `release-evidence-2`: 102/103 passed after waiting for the shell;
  remaining negative overflow fixture had zero height and did not create real
  scroll overflow. `negative-fix-2`: corrected nonzero geometry mutation passes.
- Full frontend suite: 308/308 tests, 72 files, coverage thresholds passed.
  Overall line coverage 78.23%; AppShell 87.5%. Browser-only integration evidence
  supplements, but does not numerically increase, unit coverage. New Home controls
  unit test passed separately. Typecheck and frontend lint passed.
- Plan/deployment validation: six tests passed; six analysis cycles recorded.

Evidence directories: `.artifacts/layout-109/<attempt>/` and corresponding
`<attempt>-report/`. New evidence reporter binds source, toolchain, rendering and
attachments, and rejects source drift. Frontend CI and complete-gate manifest now
include layout checks. No cloud resource was provisioned during this batch.

Still open: final combined run after the fault-fixture correction, detailed
changed-line coverage review, supported assurance selection verification, current
exact-head repetition evidence, complete release gate, owner visual acceptance,
merge, and bounded live verification. Task checkboxes retain full-acceptance scope;
implemented code must not be mistaken for completed lifecycle acceptance.
