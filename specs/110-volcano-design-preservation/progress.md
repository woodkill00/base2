# Reference recovery checkpoint — 2026-10-13

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
