# Tasks and issue ledger

- [x] T001 Confirm clean source, approvals, preserved October 26 scan and prior live gaps.
- [x] T002 Refresh audits and resolve patched registry versions/digests; map consumers.
- [x] T003 Add failing pin/behavior regressions and update the complete dependency batch.
- [x] T004 Validate telemetry and frontend compatibility, media decoder/isolation and built-image scans.
- [ ] T005 Verify antivirus freshness, guarded launch prerequisites and cleanup readiness without provisioning.
- [ ] T006 Renew valid visual evidence without redesign; run full local gate and current audits.
- [ ] T007 Publish and merge after hosted checks; preserve reviewed ancestry and verify main.
- [ ] T008 Admit exact merged source and run one authorized automated-only live trial.
- [ ] T009 Inspect screenshots/runtime results, tear down, verify inventory and record residuals.

## Analysis 1

Previous CI 40317607507: Undici high finding affects frontend tooling; telemetry
API 1.44.0 has unbounded tracestate parsing; media runtime contains three Brotli
packages with one critical advisory. These are deployment blockers, not exceptions.
Evidence: `.artifacts/oct29-preflight-security/`. Fresh sweep: `.artifacts/f120/`.
Include API input/lock, Django/tooling manifests if affected, all npm workspaces,
builder/verifier/runtime stages, Python ABI and hash-bound decoder wheels.
Source-bound visual manifests and exact-source admission are adjacent consumers.
No pending observation window is required. Prior live audit-order test remains
unverified live despite its repaired local/CI coverage. Preserve this distinction.

## Analysis 2

Refinement adds pre-provision antivirus freshness and final-image scanning, since
a source-only scan cannot prove packaged OS libraries or live readiness. Require
negative telemetry input and existing hostile-media tests, no scanner suppressions,
no baseline replacement, no automatic retry of privileged operations. Any newly
found root failure joins this ledger before further expensive validation.

## Analysis 3

Fresh October 30 sweep confirms the original roots and additional Undici
advisories covered by the same patched version. Root tooling lock also contains
vulnerable ajv, fast-uri, js-yaml, lodash, picomatch and yaml; update compatible
transitives in this batch and audit root/frontend/E2E separately. E2E audit clean.
Resolved amd64 Chainguard runtime 54ad02f5… and dev 9ebf8de7… directly from the
registry; runtime is Python 3.15.1 (same decoder ABI). Keep immutable digests.
Pin regression failed on Undici before repair. Telemetry dependency installation
and pip check pass after aligning API/SDK/exporters to 1.45.1 with 0.66b1
instrumentation. Add valid-propagation and bounded hostile-header regression.

## Analysis 4 / focused validation

Root/frontend/E2E npm and API/Django/tooling Python audits meet policy. Focused
telemetry, startup, derivative and isolation tests pass; dependency policy has
7 passes. Frontend has 442 passing tests in 92 files; production and Storybook
builds pass. Actual media-image decoder, two-UID signed-spool and updater
lifecycle acceptance pass. No application UI/style or baseline edits were made;
coverage impact is dependency behavior, exercised by these suites and the
pending complete gate, rather than new application branches.

Image scan meets the existing high/critical gate with no suppressions. Residual:
medium CVE-2026-114583 in Python 3.15 tarfile, no fix version reported; no tarfile
consumer found in the media handlers. Retain and monitor, not a zero-risk claim.
Evidence: `.artifacts/f120/image-scan.json` (database built October 29).

The generic definition URL HEAD probe returned 403; this is not evidence that
the supported updater fails. One bounded real FreshClam run using official
ClamAV 1.5.4 and the repository configuration successfully installed signed daily
28168 (October 29 06:24 UTC), within the real-clock 24-hour freshness bound.
Its exact diagnostic container/volume were removed. Offline updater acceptance
uses a fixed reference clock and is not represented as real-clock freshness.
Live readiness must still check current definitions on the actual deployed stack.
Evidence: `.artifacts/f120/freshclam-real.log`. No paid deployment has occurred.
