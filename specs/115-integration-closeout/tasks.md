# Tasks

## Evidence and planning

- [x] T001 Verify clean source, policy, existing ledger, prior merge/live evidence and local Docker prerequisites (R01,R08).
- [x] T002 Reconcile completed Feature114 items, link current closeout and preserve unresolved incidents (R01,R07).
- [x] T003 Complete tasks -> analysis -> fixed/additional tasks cycle for all six outstanding workstreams (R01-R08).

## Email and OAuth

- [x] T004 Inventory verification/reset/contact endpoints, transport, outbox, token/session and notification boundaries (R02,R07; analysis cycle 8).
- [x] T005 Add missing real-database email outcome/expiry/replay/session regressions with isolated synthetic accounts (R02).
- [x] T006 Extend container budget/key acceptance for ownership, lifecycle, restart, exhaustion, corruption, lease expiry and non-reset initialization (R03).
- [x] T007 Test runner failure/timeout/cleanup/redaction; wire required acceptance into the supported release path (R03,R08).
- [x] T008 Characterize selected GIS versus unused code-flow activation, misconfiguration, denial and no-session failure behavior; fix proven security gaps without activating the unused path (R04).
- [x] T009 Prepare bounded real-mail outcome acceptance using an approved disposable account, never the reusable owner (R02,R08; live-acceptance.md).

## Real backend and visuals

- [x] T010 Map optional module models/repositories/routes to existing PostgreSQL acceptance and identify missing lifecycle cases (R06).
- [x] T011 Add restricted-role real-backend content/event/booking tests, duplicates, unauthorized access, recovery and exact cleanup (R06).
- [x] T023 Repair API expired-event admission and Django full-capacity replay, with shared negative/lifecycle regressions and real PostgreSQL verification (R06; C115-08/C115-09).
- [x] T024 Repair missing restricted-role booking authorization without blanket grants: bounded reservation capability, tenant-scoped reads, denied direct mutation, atomic capacity/replay, forward/reverse migrations and actual PostgreSQL tests (R06; C115-10).
- [x] T012 Add these cases to supported disposable acceptance entrypoints and CI without silently enabling modules on default Base2 (R06,R08; hosted execution remains T019).
- [x] T013 Reconcile route/state/viewport/role/visual coverage inventory against actual tests, not file presence (R05; cycle 10, explicit partial/pending exclusions retained).
- [x] T014 Add missing state-entry/geometry/accessibility tests and capture representative keyboard/zoom/RTL/long/error states (R05).
- [x] T015 Inspect captures and differences; preserve approved Volcano reference hashes, documenting any remaining exclusions (R05; cycles 6-8).

## Reliability and release

- [x] T016 Audit alert integration configuration and delivery receipts; test visible failures without new destinations or secret exposure (R07; cycle 10; external delivery explicitly deferred).
- [x] T017 Preserve and classify historical runtime faults, with bounded reproductions/diagnostic evidence and no speculative dependency upgrades (R07; cycles 8-10, unresolved intermittency retained).
- [x] T018 Perform final coverage/analysis cycle; add missing tasks until no known implementation/test gap remains (R01-R08; final closeout and explicit exclusions).
- [x] T019 Run required clean-source release gate, publish and verify hosted CI (R08; exact candidate 679a99b, cycle 9).
- [x] T020 Run only newly approved bounded live acceptance and obtain required human mailbox/OAuth confirmations (R02,R08; closeout.md).
- [x] T021 Verify exact teardown, preserved mail DNS and measured duration/cost evidence (R07,R08; closeout.md; billed cost unavailable, not fabricated).
- [ ] T022 Reconcile both ledgers with evidence, merge with review ancestry preserved and verify post-merge pipelines (R01,R08).
- [x] T025 Generate and validate current-head stability repetitions before the next complete gate; retain the first missing-evidence failure (C115-14,R07,R08; 679a99b).
- [x] T026 Validate operator launcher compatibility before any newly approved trial: required CLI arguments, sole fixture provisioning, private handoffs and no legacy organization mutation (C115-16/C115-17). Four local helper tests and all 14 live browser checks passed.

Owner approved both decisions on 2026-10-18: disposable Base2 account
`thejunkmailvoid+base2-test@gmail.com` for verification/reset mail and password
changes limited to that account; one fresh Frankfurt live trial, staging
certificates, maximum 60 minutes/USD 0.25, teardown afterward, only after local
checks and CI pass. This approval was consumed by run
`base2-full-20261018-044148`, which was destroyed after launcher incompatibility
blocked browser acceptance. Independent inventory confirms zero owned previews
and zero temporary address records. The owner subsequently approved one replacement
under the same limits, only after remaining non-live work and validation finish.
That replacement was used by `base2-full-20261018-230754` and automatically
destroyed at expiry before the owner completed mailbox interaction. A separately
approved final run, `base2-full-20261019-011101`, completed mailbox acceptance
and was explicitly destroyed early. No unused preview authority remains.
Google credentials/password and the reusable Woodkill account remain unchanged.

Owner clarification: verify contact submissions are received and stored; do not
add contact-email notifications in this feature. The owner believes no Base2
Discord webhook exists. The owner explicitly deferred Discord delivery to a later
task on 2026-10-18; keep it disabled. T016 retains local failure visibility and
configuration checks, but external delivery is outside current release acceptance.
Disabled alerts are not delivery evidence.

## Deferred follow-up (not part of Feature115 completion)

- [ ] D115-01 Enable and verify Base2 Discord failure-alert delivery in a separate
      approved feature. Confirm an existing private destination and owner authority;
      create its webhook and store it in Vaultwarden without committing or logging
      the URL/token. Wire the supported secret-file handoff with least privilege.
      Test disabled/missing/invalid credentials, timeout, rate limits, provider
      rejection, retry bounds, duplicate suppression, mention blocking and redaction.
      Send one authorized synthetic failure alert, verify its actual Discord receipt
      and owner-visible message, test recovery reporting, and document disable/rollback
      procedures. Enable only after these checks pass. No webhook creation or external
      send is authorized merely by recording this task.
