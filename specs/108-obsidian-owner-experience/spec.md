# Feature 108: Obsidian experience and reusable owner access

Branch: `108-obsidian-owner-experience`. Baseline: `6d17e3f`.
Status: planning; implementation and live acceptance pending.

## User stories and acceptance

### US1 — Consistent usable pages (P1)

As a visitor, I see the homepage's Obsidian Volcano design throughout Base2.
Given any first-party route, when I navigate or submit a form at supported
viewports, then shared identity, readable errors and usable controls remain.
Independent acceptance: route/state screenshot and keyboard interaction matrix.

### US2 — Working account journeys (P1)

As a user, I can register, verify, sign in, manage preferences and sign out.
Given invalid signup data, I see actionable safe validation instead of raw 422.
Given an authenticated preference change, it persists without crossing user or
tenant boundaries. Independent acceptance: browser plus runtime-role DB tests.

### US3 — Reusable operator login (P1)

As the operator, I can use my privately configured Woodkill account after launch.
Given an existing database, provisioning preserves the existing identity and
security settings; given a new empty preview database, it creates the configured
account once. Independent acceptance: repeated/concurrent provisioning and
restart/redeploy/recreation tests.

## Scope and defaults

All first-party routes, localized variants, settings sections, enabled feature
packs and loading/empty/error/dialog/menu states are included. Disabled modules
remain inaccessible. Vendor interfaces (Django admin, pgAdmin, Swagger, Flower,
Traefik) retain their design; their entry and applicable authentication are tested.

The requested display name is woodkill; the supplied email is private deployment
configuration, not a default baked into generated sites. Existing email login
remains unless an existing username contract is discovered. The account receives
least-privilege application access, not automatic operator/vendor/superuser roles.

Stable credentials do NOT preserve data after database destruction. This feature
recreates login on an empty preview DB; existing DB identity/data are preserved.
Durable data restoration needs an explicitly approved encrypted restore workflow.
No production deployment, cloud spending or credential retrieval occurs in planning.

## Requirements

- **FR-001** Inventory every route, settings section, role, module and interactive state with a verification owner and test mapping.
- **FR-002** Apply canonical Obsidian Volcano tokens/shared shells to all first-party pages while retaining supported contrast/theme preferences and generated profile portability.
- **FR-003** Verify responsive scrolling, keyboard/focus, 200% zoom, localization/long text, reduced motion and WCAG 2.2 AA contrast; required controls must not clip.
- **FR-004** Explain signup password policy before submission and show actionable field/server validation without weakening server policy.
- **FR-005** Correctly normalize Axios and normalized errors, validation, auth, throttling, server and offline failures; preserve safe field associations and correlation IDs without exposing internals.
- **FR-006** Verify registration, verification, login/logout, recovery, invitation and configured MFA/session flows, including expiry, replay, unauthorized access and disabled modules.
- **FR-007** Repair preference persistence with correct transaction-scoped actor/tenant context; preserve RLS, audit, optimistic concurrency and cross-user/tenant isolation.
- **FR-008** Add opt-in environment-bound idempotent owner provisioning after migrations through canonical auth/models; no public default account/password.
- **FR-009** Resolve an approved private Vaultwarden reference just in time; no secrets in Git, images, arguments, logs, reports or screenshots; missing secrets fail visibly and safely.
- **FR-010** Repeated provisioning preserves password, verification, MFA, roles and disabled status. Ambiguous collisions fail closed; concurrent launches cannot duplicate owners; rotation is explicit.
- **FR-011** Verify restart/redeploy/empty-DB recreation; distinguish recreated login from restored data. Owner-readiness fails if required bootstrap fails.
- **FR-012** Separate synthetic mutation/lockout/reset tests from the real owner; owner acceptance is bounded non-destructive login/read/logout only.
- **FR-013** Maintain deterministic route/state screenshots with settled fonts/data/time/motion and human baseline approval; do not hide defects with blanket masks or auto-approve changes.
- **FR-014** Make functional/accessibility/visual coverage standard for future affected routes, with route inventory drift detection and generated-profile checks.
- **FR-015** Propagate failures as nonzero exits and sanitized durable reports/notifications with bounded retries; skipped critical checks cannot produce green readiness.
- **FR-016** Reuse Feature 107 exact-source risk-based assurance and complete release authority, rollback, bounded preview TTL/cost and staging-only certificates.

## Success criteria

Every requirement has positive/negative executable evidence on the final source.
Every required route/state has functional and visual evidence with explicit human
design review. No known critical/high security issue or unexplained required
failure remains. Report coverage and limitations, never guarantee unknown defects
are impossible. Missing providers or owner review remain pending, not passed.
