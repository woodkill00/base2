# Repair plan and budget

Start: clean `622101dd67909769913b5e92adfdbaaed8314d92`; branch
`110-volcano-design-preservation`, native WSL Base2 checkout.
Retain PR #69 fixes. `origin/main` is `d58dc91`, rejected visual rollout PR #68.

Reference: retained pre-109 Home path, corresponding to `c4fde5f` presentation.
Capture it with the existing baseline flag before source edits. Reuse the exact
HomeObsidianNavigation, GlassHeader, HomeFooter and existing Volcano CSS, rather
than copying or approximating them. Remove Home's substitution with SharedLayout.

Batch 1: two viewport reference cases, four visual states each, one red run and
one corrected run; focused Home/navigation unit checks, typecheck and screenshots.
Stop for owner reference confirmation before broad composition changes. Do not
run the expensive release gate for a deliberately incomplete representative slice.

Batch 2 after confirmation: shared original-menu composition for other route
families, protected navigation and modal isolation, responsive/locale/zoom checks,
retained visual references, affected coverage, clean-source full release gate.
Publication/deployment follows evidence and applicable authority, not test success
alone. Use bounded preview and automatic teardown only after review.

## Approved dependency repair

Upgrade the Tailwind compiler/PostCSS integration to the patched current major,
retaining JavaScript theme/plugin configuration and explicit v3 appearance
compatibility where needed. Do not rewrite components or regenerate frozen images.
Update vulnerable same-major HTTP, source-map and test-network dependencies via
the lockfile, then verify the entire resolved graph. Cover Vite/Storybook, generated
profiles, browser targets, CSS ordering/preflight, dark preference and custom glass
utilities. Original Home comparisons are the early rejection gate; deployment
and the complete gate wait until targeted compatibility and coverage are ready.
Rollback is ba858c7 plus its lockfile; no database migration is involved.

Migration requirements: Tailwind 4's supported browser floor is Safari 16.4,
Chrome 111 and Firefox 128 (upstream upgrade guide). Keep CI's real browser matrix
and document this floor for generated children. Existing integer space-x/space-y
utilities retain v3 sibling margins and reversals; new arbitrary spacing follows
v4 semantics. Explicit rem text leading preserves Base2's fluid-root rounding.
New source should prefer gap-based layouts; don't reinterpret existing layouts.
