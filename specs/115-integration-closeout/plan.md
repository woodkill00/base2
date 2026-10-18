# Plan

Start from clean main b859e54ae957d6e26b56c4d6a3f884b7a53f516f, native WSL.
Branch: 115-integration-closeout. No active paid preview; previous authority used.
Use the existing local Docker images and supported runner paths, serial heavy
suites, synthetic recipients/records and exact owned cleanup. No new agents.

1. Reconcile Feature114 using the 32fd45a gate/live receipts and b859e54 hosted
   checks. Keep historical evidence historical, not valid for changed inputs.
2. Audit email, OAuth, database, visual and alert consumers in one bounded sweep.
   Add reproductions and update analysis before fixing each related batch.
3. Extend existing acceptance entrypoints; retain Bash/PowerShell parity for
   operational commands. Default runs must not read real provider credentials.
4. Exercise restricted roles with real PostgreSQL/Redis. Use no public listeners
   or owner account changes. Tests must enter their named failure states.
5. Inspect captures without changing theme sources. Audit route inventory,
   backend coverage and exact test identifiers; record exclusions honestly.
6. Run focused contracts/unit tests, affected containers/database/browser suites,
   coverage review, then one required complete gate on a clean committed source.
   Repeat only after a relevant correction; retain every first failure.
7. Publish/observe CI through existing policy. Ask before a fresh paid trial,
   real mailbox sends or new external notification configuration. Preserve TLS
   staging, spending/TTL bounds and independent provider cleanup verification.

Budget: one discovery sweep, one focused run per repair batch plus one documented
diagnostic retry if justified, heavy suites serial. No full gate until the
implementation/coverage review is ready. No new runtime dependencies by default.

Booking repair: migration 0035 supplies a fixed PostgreSQL reservation capability
with a pinned search path and revoked PUBLIC execution. The API role may read
tenant-scoped event data and execute that capability, not mutate event or booking
tables directly. Django continues its transactional canonical reservation path;
both paths must retain matching expiry, replay and capacity semantics. Rollback
revokes the API SELECT grant and drops the function/policy; it leaves RLS enabled
to avoid weakening any future unrelated policy. Test migration reversal and
concurrent reservations before release. This does not enable the optional events
module in the default deployed profile.
