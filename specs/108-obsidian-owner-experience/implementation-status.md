# Implementation checkpoint

Latest checkpoint, 2026-09-11: `655d9574d69f6aea75e46d76494c331ff9a21dfe`
passed all 114 required release groups and is the live bounded preview source.
Real owner login and restricted-role settings checks passed; live browser results
were five passed and one failed (synthetic privacy export stuck queued).
The R10-R13 repair batch in `repair-ledger.md` corrects dispatch selection/commit,
snapshot transaction ordering and the tenant-scoped operator diagnostic. Focused
regressions, complete API coverage collection and real restricted-role PostgreSQL
export/pool reuse acceptance pass. Corrected-source release and live export
acceptance remain due. Earlier checkpoints below are historical, not current status.

Implemented: signup Axios validation/network/internal-error regressions, password
policy help and accessible field descriptions; transaction-scoped tenant binding
for preference/notification reads and writes; shared Obsidian shell/card/input/
button tokens and light preference compatibility; optional private owner bootstrap
in the full preview deployment with preservation/conflict/environment tests.

Owner bootstrap uses the existing canonical API auth schema and hashing code.
It creates no admin grants, MFA bypass or verified-email flag. Existing credentials
are never reset. Provisioning serializes on profile to prevent concurrent name or
email collisions. The private JSON input is passed on stdin and removed remotely.

Validation so far: 32 focused backend/deployment checks passed. Initial complete
frontend run: 290 passed, one normalized-error compatibility regression found and
repaired. New browser matrix covers 17 public/auth routes at mobile and desktop,
plus signup field validation; screenshots captured privately. Existing authenticated
and vendor acceptance must still run on the final exact-source deployment.

Not complete: full route/state inventory, complete authenticated visual matrix,
baseline owner approval, local restricted-role migration alignment, final release
gate, live owner/restart/recreation checks,
deployment and teardown evidence. Tasks remain open until their full acceptance
is met; this checkpoint is not feature closeout.

The dedicated `base2/woodkill` Vaultwarden login is now resolved into private
operator storage and passed the unchanged password policy. No gateway or Facebook
credential was substituted. No secret is included in repository evidence.

Release analysis found cross-theme style leakage: shared experience overrides are
now restricted to Obsidian, preserving the original other-theme shell classes.
All 21 existing account browser checks and four Obsidian experience checks pass
without updating visual baselines. All 40 assurance tests pass after isolating a
synthetic release unit test from the host browser cache. An isolated PostgreSQL
acceptance rerun passed after an earlier native process exit 139; this is not proof
that the native crash cause is resolved, and final release validation remains due.

Further release analysis found changed-line coverage below the unchanged 90% gate
and stale Operations/media/workspace visual baselines. Added private-file/stdin,
oversize, malformed, symlink, public-permission and invalid-identity owner tests,
plus deployment transfer-admission tests. Focused results: 23 owner tests and 19
preview entrypoint tests pass. No coverage threshold was lowered.

Visual review found a transient primary-button contrast failure, residual purple
media surfaces, and light-mode fixtures that changed only the OS preference while
the new Obsidian default stayed dark. Corrected button state contrast, bound media
surfaces/placeholders to shared tokens, and set explicit light user preferences in
the three release matrices. Regenerated design baselines are implementation-review
candidates, not a claim of final owner visual approval. Operations evidence now
also binds the shared experience CSS, CSS entrypoint and theme persistence sources.
