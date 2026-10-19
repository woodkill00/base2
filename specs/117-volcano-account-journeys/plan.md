# Implementation plan

Branch 117-volcano-account-journeys starts at 95fa12f, stacked on unmerged PR82.
Do not independently merge or deploy its parent. Preserve its review ancestry.
Native WSL checkout; no agents or paid resources.

1. Owner approved the session-migration scope. Selected design:
   short-lived access token in memory, existing HttpOnly refresh-cookie flow,
   verified session bootstrap, safe legacy token cleanup and tab notifications
   carrying no credentials. Confirm cookie/CSRF/tenant/revocation semantics first;
   do not assume cookie refresh alone proves logout across every access JWT.
   See migration.md for compatibility, logout barrier and rollback constraints.
2. Model/domain review precedes API changes: reuse canonical one-time verification
   tokens, existing mail adapter and audit model; add schema only if necessary.
   Implement a supported resend route with neutral output, bounded per-account/IP
   limits, concurrency/idempotency handling and real restricted-role DB tests.
3. Extend existing Volcano card/form/status components. Keep original menus,
   backgrounds and tokens. Do not style or impersonate Google's chooser.
4. Use explicit auth transition states and single-flight guards. Stop pending
   auth completions from restoring a logged-out session. Handle logout failures
   honestly, server revocation separately, and session expiry without redirect loops.
5. Replace timed success redirects with owner-controlled actions. Recovery paths
   must strip tokens from return URLs and never log credentials or reset links.
6. Test in cost order: focused component/API/security tests, restricted-role
   integration, browser states/screenshots, coverage, then one complete release
   gate on a clean candidate. Use existing supported runners and parity rules.
7. Publish with source-specific evidence and observe CI. Any real-provider trial
   requires new explicit resource/mail authority; offline mocks are not provider
   visual or inbox acceptance.

Budget: one batched audit (done), one targeted run per repair batch, serial heavy
suites, no full gate until scope, coverage and visual review are ready. Retain
first failures. The security decision is now approved; implementation has begun.
