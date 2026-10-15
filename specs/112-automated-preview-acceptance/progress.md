# Implementation checkpoint

## Final local acceptance

Implementation candidate: `c12ebde48e9a5665c87e50d37a4a822fc6d8bd2d`.
Final gate: `.artifacts/complete-gate/20261014T191551Z-982318/result.json`.
All 122 checks reached passed; none failed or blocked at completion. Started
19:15:51Z, finished 19:28:00Z on 2026-10-14 (12m10s). One permitted native retry:
`site-content-api` first exited -11 during coverage report generation, then passed.
Preserve its first-failure log; intermittent Python/toolchain instability remains
unresolved, and a retry is not evidence that its cause has been fixed.

All 13 new acceptance regressions and the 69 Volcano browser checks passed. No
design/baseline changes. Both complete-gate runs retained: the first passed all 122
without retry but predates the worker-directory correction. Final evidence above
is the relevant implementation acceptance. Full-gate count: 2; deployments: 0.

T001–T012 complete for local implementation scope. Branch is not published or
merged. CI changes await GitHub execution; live owner login, exact deployed build
comparison and provider cleanup await an authorized preview and private inputs.
Machine-local wrapper still needs the documented added inputs; no sync or helper
edits were performed. No claims of exhaustive pixel baselines for every content
page, live acceptance, native PowerShell execution, or absence of unknown defects.

This closeout modifies documentation only; full-gate evidence remains bound to
c12ebde, not relabeled for the subsequent documentation commit.

## Post-gate recovery correction

Candidate 87f0310 passed the complete local gate at
`.artifacts/complete-gate/20261014T190200Z-951654/result.json`. Subsequent review
found Playwright deletes/recreates its output root; a real worker regression
reproduced failure of the owner-only directory check before test startup.
Transient output now uses a `test-output` child directory, preserving private root
permissions. All 13 acceptance regressions pass, including actual worker startup
without a browser/network and rejection of fixture-only acceptance. TypeScript
passes. The first fixture configuration had a relative reporter-resolution issue;
fixed before reproducing the actual bug. Final exact-source gate must be rerun.

Feature 112 branches from main 556b9603. All implementation tasks T001–T011 are
complete; complete release gate T012 is pending. No paid preview, credentials,
notebook sync, publication, merge or live owner-login run occurred.

Targeted checks: 12 Node regression tests pass; real Playwright suite collection
proves all 11 required live cases exist. Listing alone intentionally exits nonzero
with blocked acceptance. Missing private inputs, stale/dirty source, baseline
override and old evidence directories fail before browser launch. TypeScript and
frontend lint pass (24 pre-existing declaration warnings, zero errors).

Final targeted Volcano run: 69 passed in 38.3 seconds after profile-aware route-state
assertions were added. Same existing eight pixel references are used locally/live;
no baseline or application design changes. Actual mobile blog capture inspected:
expected disabled-module page, preserved Volcano shell and footer. Other captures
remain supplemental evidence, not newly approved pixel baselines.

Measured Node coverage for the two new acceptance logic/reporter modules: 97.92%
lines, 85.92% branches, 77.78% functions (subprocess coverage included). Shared
reference assertions exercised by the real Chromium suite. This is not a claim
of complete live functional coverage or zero unknown defects.

Failure history retained: first test red due missing new module; list-only test
incorrectly expected success and was corrected; new import.meta use exposed a
Playwright TypeScript module-loader mismatch, repaired using a static JSON import.

Live acceptance remains blocked until an authorized preview and private owner
inputs are provided. The notebook wrapper needs the documented additional inputs;
it will fail closed instead of silently skipping tests. Cleanup remains a separate
existing lifecycle verification; browser reports explicitly say not-evaluated.

Final pre-gate analysis: A1–A5 implemented and regression-checked. Additional route
state weakness fixed. The owner-login body is collected and typechecked but cannot
be live-verified without private inputs/approved preview; it is not claimed passed.
Local full gate is still required. CI changes become externally verified only after
publication. No known unresolved implementation blocker in this bounded batch.

# 2026-10-15 final acceptance

PR76 merged the logout-test synchronization correction into main at
35fa5ec7b723d99a1fd54a3805a32950abcdcfc0. Its candidate6126863 passed all122
complete-gate checks without retries (20261015T011204Z-277578), all15 acceptance
regressions, PR CI and all ten post-merge workflows.

The owner separately approved one additional identical bounded trial. Run
base2-full-20261015-014656 deployed exact35fa5ec, passed eight route readiness
probes and all11 browser acceptance tests in3.5minutes with zero retries or missing
cases. The receipt confirms sourceClean/sourceStable. Both390/1440 approved
Volcano comparisons, real owner login/logout, operator access controls, Django and
pgAdmin logins, settings, responsive routes and safe/hostile media checks passed.
Inspected actual mobile command-palette and desktop operations screenshots; no
design or baseline change was introduced. pgAdmin briefly reported unhealthy
during first-start migrations, then recovered without intervention before readiness.

Exact early-approved teardown removed one droplet and six DNS records. The
integrity-checked lease is destroyed, its expiry timer is inactive, and provider
inventory returned zero droplets and zero managed DNS records. Both authorized
trials are destroyed. No preview is left running.

Private evidence root: ~/.local/state/base2-full-preview/base2-full-20261015-014656
(browser/acceptance.json, screenshots and leases/). Browser acceptance deliberately
does not certify lifecycle; lifecycle is evidenced by the separate teardown/store
and inventory observations. The first failed trial remains retained separately.

Residual limits: these checks cover the declared inventory, not every unknown
defect or user-device font environment. Native interpreter instability observed
earlier has no proven underlying root-cause fix; redundant reporting is removed,
and final gates passed without retries. Windows-native helper execution was not
tested; operational execution used WSL. Production certificates were never issued.

## Earlier live continuation (retained history)

PR75 merged as b0bc1d5e4f24a5cf5c45064728f5acb05911b999; all ten
post-merge workflows passed. Final premerge edb63ee passed122 local gate checks
with no retries (20261015T001952Z-216959). Hosted font mismatch corrected by
installing the approved Ubuntu font package, without baseline or design changes.

Live run base2-full-20261015-005003 reached live-verified and passed10/11 browser
cases. All visual references, operator logins, responsive routes and media checks
passed. Logout test raced server completion; one diagnostic waiting for HTTP204
proved logout and protected-route rejection. Failed acceptance remains retained
in private run/browser/acceptance.json. Follow-up T021 corrects synchronization.

Exact teardown removed one droplet and six DNS records. Provider inventory is
empty. No live preview remains. Full acceptance remains incomplete pending a
fresh approved bounded trial of the corrected test; diagnostic is not acceptance.
