# Analysis and issue ledger

Cycle 1: Shared GlassInput covers login, signup and two reset fields. Google
button defaults to outline/white. AppShell already routes page families through
the approved Volcano layout; replacing that shell would violate design approval.

Cycle 2 refinements: cover independently toggled reset fields, non-submit behavior,
field blur hiding, keyboard focus, accessible name/state, autocomplete, errors,
disabled state, narrow/zoom layout and all non-password shared consumers. No
account linking or password persistence. Google options tested at adapter boundary;
offline mocks cannot prove the external provider's pixels. No known blocking
planning gaps remain; execution evidence is still required.

| Issue   | Severity  | Reproduction / cause                         | Regression                          | Status |
| ------- | --------- | -------------------------------------------- | ----------------------------------- | ------ |
| U116-01 | usability | All four password fields lack reveal control | Shared control + page browser tests | open   |
| U116-02 | visual    | GoogleLogin omits theme, uses white default  | Adapter theme assertion             | open   |
| U116-03 | usability | Login/reset omit autocomplete hints          | Field attribute assertions          | open   |

Runtime/schema/trust boundaries are unchanged. Existing historical intermittent
failures remain recorded in Feature115; this feature does not claim to fix them.

Execution batch: test-first run reproduced four expected failures (three missing
password capabilities and one missing dark theme). After implementation, 12/12
focused tests passed. Adjacent auth tests then exposed three ambiguous broad
password selectors; selectors now use exact field names, without weakening any
behavior assertion. The same affected browser selector was corrected.

First browser run exposed a test-only locator lifetime error: after revealing,
the accessible button name correctly changes to Hide, but the test still queried
Show for its bounds. Stopped that dependent batch, retained failure captures,
and changed the bounds lookup to the correct state-specific accessible name.

U116-04 (usability, fixed): all nine mobile cases reproduced a 43.4375px target,
below the chosen 44px minimum because the existing fluid root font is under 16px.
Use max(44px, 2.75rem) and matching calc padding; keep the measured 44px assertion.
Desktop cases passed in all three engines. Also assert height and light preference.
The interrupted first run left its owned preview listener; exact PID cleanup
resolved the port admission block without reusing a stale build.

Corrected cross-browser batch passed all 18 cases. Inspected actual Chromium
390px light-preference and 1440px dark captures from journeys-run-1792384762470:
approved shell and red edge tabs preserved, reveal controls contained, no clipping.
Full frontend batch passed 374 tests. Coverage review caught the pointer handler
not exercised by unit tests (critical glass 99.71% lines versus required 100%).
Added a pointer-focus/default-prevention regression rather than lowering the floor.
Coverage from unchanged backend reports is preliminary only; complete gate must
produce current required evidence. Dirty-source gate admission was blocked before
execution when checking wrapper usage; no complete-gate pass is claimed.

Focused pointer coverage now has 100% lines/statements/functions for GlassInput
(its other branch combinations are exercised by existing glass tests). Typecheck
passed and lint has zero errors, with 24 existing declaration warnings.
Additional 200% text-zoom browser checks passed all six Chromium page/size cases.
T006/T007 still require the complete shared-consumer release gate. Current code
does not restyle provider-owned Google chooser screens or add account linking.
