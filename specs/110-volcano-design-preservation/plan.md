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
