# Layout and acceptance contract

## Proposed geometry, to be ratified in the representative review

- Desktop at 1280 CSS px and above: both rails visible. Left holds global navigation;
  right holds useful page context/help, not invented live data or private guest content.
- 768–1279: labelled controls expose both rails; 320–767: off-canvas drawers, at most
  one modal rail open. Controls never disappear when a rail is collapsed.
- Test fixed widths 320, 390, 768, 1024, 1280, 1440 and 1920; include boundary neighbors
  767/768 and 1279/1280 for shared-shell transitions. These are CSS pixels, not claims
  of exhaustive physical-device coverage. Cover Chromium, Firefox and WebKit shared
  interactions; pin the screenshot browser/platform and fonts.
- Main content is centered within its allocated main track, not shifted by arbitrary
  page margins. Measured left/right available-space difference ≤2 CSS px when centered.
  Alignment of related card/form edges differs by ≤2 px. Intentional full-width tables
  use documented local overflow, not body overflow; body overflow tolerance ≤1 px.
- Header/footer/restriction banner participate in layout. Long content cannot overlap
  fixed controls. No whitespace-only viewport-height blocks on short pages.
- Rail scroll range reaches the final item; no jump/reset on ordinary selection,
  background updates or unrelated renders. Explicit route/anchor/reset actions follow
  the recorded policy; back/forward behavior is tested. Dragging/scrolling a menu does
  not unexpectedly snap it back or hide content. Empty panels have intentional states.

## Accessibility and interaction

One primary main landmark, labelled global navigation and context regions, logical
headings, skip links and visible focus. Modal drawers trap focus only while open,
Escape closes and focus returns to their trigger. Desktop rails never trap focus.
Verify zoom/reflow, long labels, RTL, reduced motion, contrast preferences, loading
and error recovery, touch input, keyboard traversal, route guards and sign-out.
No layout-only change may alter request permissions or disabled media behavior.

## Evidence and completion

Before/after screenshots for every route family, desktop/mobile, plus declared
state matrices and cross-browser shell interactions. Baseline mismatch, missing
rail, footer overlap, clipping and scroll-reset mutations MUST fail with named cases.
Owner reviews the representative slice before broad rollout and final family gallery
before design acceptance. Automated passes cannot stand in for those decisions.
Live restricted media cases must prove refusal and mark normal media workflows blocked.
After a failure: retain the original evidence, classify it, fix tasks/tests/code,
rerun the affected case in a new directory, then satisfy the applicable release gate.
