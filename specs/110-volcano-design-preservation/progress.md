# Reference recovery checkpoint — 2026-10-13

Status: representative local review ready; NOT all-page completion or release.
Branch: `110-volcano-design-preservation`. V006 owner confirmation is pending.

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

Remaining: owner reference confirmation, all-page extension, full affected state/
coverage and release validation. No full gate run for this incomplete review slice.
An integrity guard catches image replacement; changing both manifest and images
still requires code/owner review. It is not a cryptographic approval service.
