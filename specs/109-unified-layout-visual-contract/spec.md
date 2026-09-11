# Feature 109: Unified Obsidian layout and visual contract

**Feature Branch**: `109-unified-layout-visual-contract`
**Created**: 2026-09-11
**Status**: Planned; implementation and owner visual acceptance pending
**Input**: Fix inconsistent spacing/centering and missing left/right menus across
Base2 pages; verify actual rendered results and prevent recurrence.

## Scope

First-party Base2 layout, navigation, responsive behavior and visual assurance only.
Preserve the current Obsidian design as the starting reference, but do not reproduce
its existing defects. No backend feature redesign, new database, auth-policy change,
antivirus bypass, provider expansion or vendor-product reskinning. Django admin,
pgAdmin, Swagger, Flower and Traefik are distinct vendor surfaces: preserve their
existing protected access and smoke tests, not a promise to inject Base2 menus.
This branch starts at `c4fde5f4898718e1f619fa23cffa2edafdb5e910`, preserving Feature
108; it does not merge or certify completion of that feature.

## User scenarios and testing

### US1 — Consistent navigation and page structure (P1)

As a user moving between Home, Dashboard and Settings, I see the same recognizable
header, left navigation, right context panel and footer, with useful page content
between them. Independent acceptance: review these three pages side by side and
navigate between them without losing menu access or duplicating headers.

- Given a desktop layout, every applicable route displays both rails by default.
- Given a narrow screen, each rail remains accessible through a labelled control.
- Given an anonymous user, public navigation remains useful without exposing private
  account information or implying access to protected actions.

### US2 — Readable, fluid layouts across pages and devices (P1)

As a user reading forms, cards, lists and long pages, I see deliberate alignment,
consistent spacing and usable scrolling. Independent acceptance: exercise long
menus/content, keyboard controls, touch scrolling and zoom without clipped controls,
scroll jumps, overlapping footer/header or inaccessible page content.

### US3 — Reviewable evidence and regression prevention (P1)

As the owner, I can compare before/after results for each page and approve the design.
As a maintainer, I cannot silently add an unclassified route or accept a broken
baseline. Independent acceptance: remove a required rail or introduce clipping and
prove the checks fail with a route-specific diagnostic and visual evidence.

## Functional requirements

- **FR-001**: Every first-party route, nested route, locale variant and enabled-module
  state MUST have an explicit layout policy; unknown routes MUST fail inventory checks.
- **FR-002**: Desktop pages MUST share header, left rail, main region, right rail and
  footer; there MUST be one primary main region and no duplicate global navigation.
- **FR-003**: Omitting either rail MUST require a documented owner-approved exception;
  login/signup are not implicitly exempt. Anonymous rails MUST use public-safe content.
- **FR-004**: Layout MUST preserve Obsidian identity and use consistent alignment,
  readable widths and spacing, including user theme and contrast preferences.
- **FR-005**: Both rails MUST remain accessible at narrow widths and support keyboard,
  touch, focus restoration, Escape and correct modal/nonmodal semantics.
- **FR-006**: Rail and page scrolling MUST remain stable across ordinary interaction,
  resize and navigation under an explicit scroll-restoration policy.
- **FR-007**: Short, long, loading, empty, error and disabled pages MUST remain usable
  without unintended overflow, clipped controls or header/footer overlap.
- **FR-008**: Existing route guards, navigation destinations, authentication, forms,
  privacy operations and server-side restricted-preview controls MUST remain intact.
- **FR-009**: Review MUST start with Home, Dashboard and Settings as a representative
  slice; owner approval of that slice MUST precede broad visual rollout.
- **FR-010**: Every route family MUST have responsive visual and interaction evidence,
  with exhaustive layout-policy membership and explicit state coverage.
- **FR-011**: Visual baselines MUST be inspected and approved, not blindly regenerated;
  accepted changes MUST bind to source, theme, profile, fixture and browser inputs.
- **FR-012**: Failures MUST identify route, state, viewport and assertion, retain first
  evidence and distinguish product failures, test drift and unavailable capabilities.
- **FR-013**: Validation MUST batch related fixes, check prerequisites before expensive
  gates, reuse valid evidence only, and retain mandatory release/security requirements.
- **FR-014**: Final live review MUST use a bounded exact-source preview with teardown;
  readiness MUST distinguish automated passing checks from owner design approval.

## Edge cases

Deep links/refresh/back/forward; nested Settings navigation versus global rails;
module-disabled and permission-denied routes; localized labels and RTL; 200% text/zoom;
mobile keyboard/safe areas; long unbroken text; table/chart overflow; drawers with
dialogs/toasts/banners; font loading; restricted media pages; slow or failed requests;
theme changes and reduced motion; empty right-panel context; signed-out transitions.

## Success criteria

- All discovered first-party routes classified, zero unexplained rail omissions.
- Owner approves the representative slice and final route-family review explicitly.
- Required layout/functional/accessibility checks pass on declared supported targets;
  no known blocking visual defects remain, with evidence for fixes and negative tests.
- No increased permission/credential exposure or weakened existing media restrictions.
- No claim that finite browser tests prove perfection on every possible device.
