# Implementation plan

Branch: `109-unified-layout-visual-contract`. Spec: [spec.md](spec.md).

## Constitution and boundaries

Follow `.specify/memory/constitution.md`: spec → tests → code, existing container
topology, no changes to canonical Django models or API contracts assumed. Existing
React/Vite, CSS, Vitest, Playwright and accessibility tooling suffice. Do not replace
the current auth/permission boundaries with visibility checks. Existing secure
cookies, CSRF, restricted preview, staging certificates and vendor allowlists remain.
This planning request does not launch, extend, merge or tear down any resource.

## Architecture and sequence

1. Inventory PublicRoutes, LocalizedExperience and nested/settings/module routes;
   capture baseline screenshots and a defect ledger before editing layouts.
2. Establish a machine-readable route layout policy plus reviewed exceptions and
   a deterministic context-slot model. Both rails are the desktop default, including
   guest pages. Any focus-mode auth exception requires owner confirmation.
3. Consolidate `components/glass/AppShell.tsx`, `components/public/PublicShell.jsx`
   and Home composition into a single global structure, retaining appropriate
   public/app content and permission-filtered navigation. Keep nested Settings tabs
   distinct from global navigation; eliminate duplicated app headers.
4. Centralize geometry in shared CSS tokens: content widths, rail tracks, gaps,
   header/footer/banner offsets, breakpoints and safe areas. Use intrinsic layout;
   no route-specific arbitrary offsets to hide shared defects.
5. Prototype Home, Dashboard and Settings with synthetic data. Verify all states,
   show before/after evidence, obtain owner approval, then migrate remaining families.
6. Add exhaustive route-policy enforcement, deterministic screenshots and geometry/
   interaction assertions. Test missing rails and broken scrolling deliberately.
7. Run focused unit/browser checks and affected coverage first. Validate exact-head
   repetition evidence, clean source and tool prerequisites BEFORE the existing
   `scripts/python/run_complete_gate.py`. Use supported assurance cache only; avoid
   simultaneous heavy runs, blind retries and rereading entire logs.
8. After local evidence and separate launch authority, use the supported deployment
   entrypoint with exact source, bounded budget/TTL and independent cleanup. Compare
   live screenshots and user interactions to local evidence. Record owner acceptance.

## Testing and review

See [contracts/layout-acceptance.md](contracts/layout-acceptance.md). Layout membership
is exhaustive; state combinations use documented risk-based coverage rather than an
unbounded Cartesian product. Every family receives desktop/mobile review; shared
shell interactions exercise all breakpoints, keyboard/touch, zoom, RTL and preferences.
Assertions must wait for deterministic readiness, fonts and fixture data, not sleeps.
Do not mask navigation, text, errors or layout surfaces to make screenshots pass.
Do not overwrite failed-run artifacts on retries: use distinct immutable attempt paths.

## Rollout, rollback and deferred work

Small implementation commits: foundation, representative slice, remaining families,
assurance. Keep changes frontend-only unless a concrete incompatible contract is found;
record any such expansion and request direction before backend feature work.
Revert the exact layout commits if required, preserving user data and prior fixes;
test route/guard compatibility before and after rollback locally. No new DB migration.
Feature 108 broader acceptance and media enablement remain separate, not silently closed.
