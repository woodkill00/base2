# Visual Port Map

## Source boundary

- Base/current main/merge base: `5320d3fac8decfb77df75c10b4633821f91cea78`
- Visual tip: `0132131292d584172a9b2fa173e439b540abed99`
- Relationship: visual tip is 231 commits ahead of exact current main; no right-side divergence.
- Net delta: 17 files, 4,513 insertions, 510 deletions.
- Rule: review and reimplement the net behavior on Feature 093. Do not merge the 231-commit branch as a unit.

## Explicit exclusion

`digital_ocean/scripts/bash/digital_ocean_base.sh` adds request-selected branch checkout, `fetch ... || true`, force branch recreation, and `reset --hard`. It is unrelated to visual behavior and conflicts with immutable, fail-closed deployment policy. It must not be ported. Feature 093 deployment work uses exact commit identity and the sole orchestrator.

## Port inventory

| Source path | Net change | Decision and required adaptation |
|---|---:|---|
| `react-app/src/styles/home.css` | +2458/-0 | Port visual intent into tokens, layouts, and component-scoped styles; do not retain an unstructured monolith. Preserve responsive/reduced-motion/contrast behavior through tests. |
| `HomeObsidianNavigation.jsx` | +1166 new | Port navigation concepts, keyboard model, section state, command surface, and theme affordances only after splitting into testable components. Every action must map to a real manifest route/function or explicit disabled state. |
| `HomeObsidianOps.jsx` | +114 new | Treat boot lines/commands/metrics as presentation fixtures, not real operational claims. Bind to manifest/content or label demo state. |
| `HomeThermalSecurity.jsx` | +91 new | Treat thermal/security logs as visual fixtures, never live security evidence. Bind to reviewed content or remove from nontechnical profiles. |
| `HomeHero.jsx` | +99/-78 | Port composition/type/CTA styling; replace the no-op secondary callback with an inventory-approved action. |
| `HomeFeatures.jsx` | +3/-1 | Port only the intentional section identity/spacing adjustment. |
| `HomeFooter.jsx` | +25/-123 | Port visual structure after footer/legal/social values come from the manifest and every link is valid. |
| `HomeVisual.jsx` | +40/-30 | Port graphic presentation with decorative semantics, reduced motion, and deterministic assets. |
| `About.jsx` | +51/-67 | Port presentation after copy/content is no longer hardcoded. |
| `ProjectsGrid.jsx` | +71/-39 | Port cards/grid only after projects have a real content source and empty/error states. |
| `ContactForm.jsx` | +51/-126 | Port styling/states onto the real validated durable form flow; do not port mock submission behavior. |
| `GlassHeader.tsx` | +8/-3 | Review title/navigation integration against manifest and public/private variants. |
| `Home.js` | +7/-3 | Port section composition only after modules/routes/actions are manifest-driven; the source contains a no-op secondary action. |
| `home-page.test.jsx` | +70 new | Translate semantic/component coverage onto the refactored current-main implementation. |
| `glass-header.extra.test.tsx` | +68/-9 | Preserve relevant public-header accessibility and behavior assertions. |
| `home-style.spec.ts` | +183/-31 | Rebuild as deterministic route/state/viewport/theme/motion tests; avoid brittle CSS-only markers. |

## Behavioral surfaces requiring explicit acceptance

- Section navigation, scroll/snap behavior, active section, keyboard focus, command palette, utility rail, color scheme, and mobile collapse.
- Hero primary and secondary actions.
- Content sections, project cards, contact submission, footer/legal/social links.
- Loading, empty, disabled, error, offline, permission, reduced-motion, light/dark, and narrow/wide states.
- No decorative “system status,” “security log,” or operational value may be represented as live evidence unless sourced from an authenticated real contract.

## Port checkpoints

1. Extract tokens and semantic layout from the net CSS delta.
2. Split navigation into state, commands, view, and accessibility contracts.
3. Connect all content/actions through site manifest and core content APIs.
4. Add deterministic component/page visual baselines.
5. Verify no commit from the source branch altered provider/deployment behavior in the port.
