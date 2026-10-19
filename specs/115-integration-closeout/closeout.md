# Integration acceptance closeout

Accepted runtime source: `1a77a1cfb92c0e7ef7e6b6ed78e93d23623e96b0`.
Subsequent closeout edits are documentation only, not a claim that another source
was deployed. Preserve review ancestry with a merge commit.

## Evidence and requirement reconciliation

- R01/R08: complete gate `20261018T224143Z-780548` passed; all 20 hosted
  checks passed on the accepted candidate. Final closeout commit validation and
  merge/post-merge status are recorded by the PR checks and closeout comment.
- R02: final run `base2-full-20261019-011101` passed all 14 live browser checks
  in 3.5 minutes. Owner confirmed verification-email receipt and successful
  verification; the database independently confirmed the verified flag. Owner
  completed reset and signed in with the new password using the exact disposable
  alias. The initial failed login used the separate regular account address.
  Old password and pre-reset refresh session independently returned 401. This
  does not claim immediate revocation of an already-issued access JWT.
- R03: isolated mail-container acceptance covers ownership, restart, exhaustion,
  expiry, corruption and link/permission rejection. Final live worker observation
  showed two Resend-accepted messages, no failed or pending messages; actual inbox
  outcomes are supported by owner confirmation, not inferred from acceptance.
- R04: selected GIS popup acceptance remains supported by Feature114's prior
  owner-confirmed live sign-in. Current live checks bind the configured Google
  client; they do not claim a new interactive Google sign-in. Dormant code flow
  remains disabled; its negative tests do not claim active PKCE acceptance.
- R05: 30 routes/13 families retain explicit representative/capture-only versus
  reviewed-comparison classifications. 102 journey tests, 73 Volcano checks and
  actual live mobile/desktop reference comparisons passed. No baseline was
  rewritten to clear failures. Disabled packs and all-state pixel combinations
  remain explicit exclusions, not tested claims.
- R06: restricted-role PostgreSQL content, scheduling, workspace, migration
  reversal/recovery and concurrent-booking acceptance passed. Mock browser
  fixtures remain complementary and do not replace real-backend checks.
- R07: local failure propagation/disabled-alert tests passed. Discord delivery
  is owner-deferred to D115-01 and disabled. Contact acceptance is stored payload,
  consent and retention; contact-email notifications are explicitly out of scope.

## Cleanup and bounded trials

First run `base2-full-20261018-044148` was destroyed after stale operator-helper
failures. Four focused helper tests now cover the corrected handoffs and absence
of obsolete fixture provisioning; complete live browser acceptance subsequently
passed. Run `base2-full-20261018-230754` passed its browser tests but expired before
owner mailbox interaction; its destroyed inventory was independently confirmed.

Final separately approved trial used one Frankfurt droplet `610363715`, staging
TLS and the original 60-minute/USD0.25 ceiling. Provisioned 2026-10-19 01:11:09 UTC;
early cleanup confirmed about 01:37 UTC, approximately 26 minutes. Actual billed
cost was not fetched and is not represented by the ceiling. Teardown deleted one
droplet and six temporary DNS records. Independent inventory showed zero owned
previews/address records, and the persistent sending-DNS plan remained ready with
no creates/conflicts. No receiving MX, extra destination or lease extension.

Private sanitized evidence is under `~/.local/state/base2-full-preview/`:
`feature115-confirmation-{launch,browser,runtime}.log`, run-scoped browser captures
and integrity-bound lease, and sanitized final mail-session state. No passwords,
email tokens or private URLs are included here. Owner confirmation and cleanup
are also recorded in PR81 comment 6257810427.

## Residual risks and non-claims

C115-18: gate `20261018T222528Z-742130` had 129 passes, one API collection failure
and one blocked coverage check. Python raised `SystemError: error return without
exception set` during OpenAPI generation. The exact partition passed 19 tests in
an isolated diagnostic; one documented unchanged-source full rerun passed. The
original failure remains preserved, with no retry-policy or assertion weakening.
Root cause remains unproven. Earlier capture/timing/native-runtime incidents also
remain recorded; passing checks do not prove unknown defects impossible.

Verification acceptance exercised the existing authenticated email-save path.
Signup does not automatically send verification. The reusable owner account and
Google password were not changed. Disabled passkeys, external invitation mail,
contact-email notifications and Discord delivery are not represented as tested.

T022's merge/post-merge portion remains pending until actual GitHub results exist;
use the final PR closeout comment for that terminal evidence rather than marking
future checks passed in advance. This document reconciles Feature114's carried
items against Feature115's evidence and explicit owner scope decisions.
