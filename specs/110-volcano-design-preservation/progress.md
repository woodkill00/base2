# Reference recovery checkpoint — 2026-10-13

## Latest validated composition checkpoint

### Approved dependency repair — awaiting exact-source release gate

Tailwind/PostCSS 4.3.3 and Axios 1.20.0 plus patched transitive dependencies remove
all current audit findings. Three CSS compatibility regressions were reproduced
and repaired without changing any PNG: sibling spacing, rem line height and native
file-selector metrics. Final matrices passed 69 Volcano, 22 Operations, 24 Media,
24 Workspace, 15 Ember compatibility and 10 Northstar settings cases; deliberate
project/state skips remain explicit. All 326 frontend tests passed with coverage,
Storybook built, TypeScript passed and lint has zero errors (24 existing warnings).
The reference integrity contract passes all three checks. Operations evidence
correctly rejected the prior source binding (five negative-contract tests passed);
refresh it only after the completed visual review. Full gate, publication, live
verification and owner review remain pending. No cloud resource was launched.
VOL-07 remains a disclosed intermittent runtime risk, not a resolved root cause.

### Release blocker — final round 2

Exact candidate `a603bfd6cb0164e19f863378cb915eea1d6fec31` completed the full
gate with **119 passed, 1 failed, 0 blocked** in 822 seconds. The only failed
check is `frontend-production-audit`: 11 dependency findings (9 high, 2 moderate).
Evidence: `.artifacts/complete-gate/20261013T175414Z-636889/result.json` and
`frontend-production-audit.log`. This is NOT a release pass. The frontend attempt
first exited without a terminal summary; its single policy-bounded retry passed
all 323 tests. Both attempts remain retained in `frontend-test.log`; the underlying
environment cause is not fixed.

All local browser matrices and coverage gates passed. Original Home reference
images remain unchanged. Changes are committed locally, but Feature 110 has not
been pushed, merged or deployed. Read-only DigitalOcean inventory returned zero
Base2 preview droplets and zero managed preview A/AAAA records. Discord is healthy.

Registry/advisory verification found braces latest 3.0.3 with no published fix for
GHSA-vfj7-8cjw-p6xm. Tailwind 3.4.19 depends on this build-tool chain; npm proposes
a breaking Tailwind 4 migration. Axios has a same-major update available. Do not
run audit fix --force, exclude development dependencies, waive the gate or change
original screenshots to hide a migration regression. A broader dependency-hardening
batch needs owner direction before proceeding. Preserve the current candidate as
the design reference and rollback point.

Release completion batch: Docker/Compose now select the approved Volcano layout.
Operations 22, Media 24 and Workspace 24 applicable browser checks pass after
closed-panel geometry, compact account wrapping and touch-target corrections.
Original Home reference integrity, TypeScript and focused lint pass. Intentional
route-shell captures were inspected before acceptance; all eight original Home
references remain unchanged. Full gate, final exact-source coverage, publication
and live verification remain pending. No new cloud resource exists.
Earlier checkpoint descriptions below refer to their named historical source.

Candidate `72f3a1f` is committed locally, not published, merged or deployed.
Final current-source results: 323 frontend tests passed; TypeScript and focused
lint passed; 69 Chromium browser checks passed in 40.9 seconds, with stable source
binding at `.artifacts/layout-109/volcano-final-composition-110/evidence.json`.
All eight original Home images match without reference replacement. Changed
executable lines are 78/78 covered (100%); critical glass/theme coverage is 100%
for lines, statements, functions and branches. Other backend reports used by the
coverage preflight are historical and do not constitute a fresh full release gate.

Release is NOT complete. Operations/media success-state matrices and their shared
source-bound review manifests, broader profile/browser acceptance, production
activation, the full release gate and publication remain pending. The native Node
crash recorded in VOL-07 remains an intermittent environment risk despite later
passes. No cloud resources were created. Details below retain earlier rounds.

Status: original-design route composition implemented in local preview; NOT release complete.
Branch: `110-volcano-design-preservation`. V006 owner confirmation received 2026-10-13.

Home's retained original composition is selected with `VITE_VOLCANO110_PREVIEW=true`.
This is not enabled in Docker/Compose. Main and deployment remain unchanged.
No new provider resource, merge or publication occurred in this repair batch.

## Evidence

- Original captures: eight Home/left/right/palette PNGs at 390 and 1440px, bound by
  `reference.json`. Home CSS, header and footer were not rewritten.
- `volcano-original-110`: initial baseline creation wrote files, correctly causing
  the source-drift reporter to reject the run despite passing browser scenarios.
- `volcano-original-verified-110`: preserved 11-pixel mobile utility-label timing
  difference. Freeze CSS motion during reference captures only; no content masking,
  geometry alteration, or comparison-tolerance increase.
- `volcano-reference-check-110`: original reference passed without image updates.
- `volcano-rejected-design-red-110`: both widths fail against generic production
  layout because the gradient/original navigation is missing.
- `volcano-restored-110`: both restored cases pass all eight original screenshot
  comparisons, with no baseline updates and no source drift.
- 17 existing Home/navigation/accessibility unit tests pass. TypeScript and focused
  ESLint pass. Two reference-integrity/deployment-isolation tests pass.
- The unit environment warns that window.scrollTo is unimplemented; real-browser
  checks exercise menus. This is not a claim that all scroll states are certified.

Artifacts: `.artifacts/layout-109/<attempt>/` and `<attempt>-report/`.
Reference gallery: `review.html`. Screenshots contain synthetic local data only.

Owner also confirmed changes must extend the approved design rather than replace
it. This rule is now in AGENTS.md. Original reference PNGs remain unchanged.

Extension batch: optional permission-filtered route adapter reuses original menus;
new VolcanoLayout composes original header/footer/background around route content,
retains account controls and page context, and isolates media dialogs. New route
palette focus containment restores inert/background state on closure.

`volcano-all-routes-110` passed 62 browser cases (38.3 seconds), including 22 guest
routes and 8 authenticated routes at both sizes plus all 8 original Home images.
These are synthetic unavailable-service fixtures, not successful live API flows.
39 focused Home/navigation/media tests passed. Broader frontend round: 318 passed,
2 failed because the new test location helper used an output element with implicit
status role, colliding with real status messages. Fixture corrected to a div;
rerun required. Mobile admin review found edge tabs too near body copy: reserved
route-only gutters added; Home stays untouched. New captures required for that edit.

Final focused coverage collection retry passed all 321 frontend tests. The critical
glass/theme subset is 100% for lines/statements/functions/branches; whole frontend
lines are 79.18%. First native crash remains recorded as unresolved intermittent
runtime risk; the successful diagnostic retry is not a fix. Committed changed-line
coverage still needs measurement. Both light/200% zoom repairs passed; signup and
RTL captures were visually inspected. Home reference files were never updated.

Remaining: all-page interaction/success/error states, responsive/theme/profile
review, affected coverage, source binding/production activation, release gate and
publication. No complete release gate or deployment has run for this batch.
An integrity guard catches image replacement; changing both manifest and images
still requires code/owner review. It is not a cryptographic approval service.
