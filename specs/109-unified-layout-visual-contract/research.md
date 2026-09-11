# Repository findings

Read at branch base c4fde5f; this is local code inspection, not external research.

- `react-app/src/pages/Home.js` directly composes its home design and footer.
- `react-app/src/components/glass/AppShell.tsx` supports only a left sidebar, closed
  initially, and no right slot. Public variant removes its sidebar and footer.
- `react-app/src/components/public/PublicShell.jsx` independently renders header,
  a fixed-width padded main area and HomeFooter, with no rails.
- Dashboard and SettingsCenter consume AppShell, so their layouts cannot inherit
  Home's two-rail structure automatically. This is a confirmed structural mismatch.
- `react-app/src/routes/PublicRoutes.jsx` contains public, authenticated,
  permission-gated and enabled-module routes. LocalizedExperience needs equal review.
- Existing `app-shell.test.tsx`, AppShell stories and several separate Playwright
  matrices are useful starting points but do not establish universal two-rail coverage.
- Feature 108's live audit test expected an internal event code while the UI correctly
  showed human-readable text. New tests must target intended user-visible semantics.
- Exact-head stability evidence was absent before an expensive release run. Feature
  109 must preflight this prerequisite before spending time on the complete gate.

Decision: adapt/consolidate existing components instead of adding another competing
shell. Grid/Flexbox with shared tokens, minmax/clamp and selective calc; do not claim
calc alone guarantees responsiveness. Reuse SVG icons; keep appropriate raster media.
No new frontend library or cloud resource is needed for planning/prototype work.
