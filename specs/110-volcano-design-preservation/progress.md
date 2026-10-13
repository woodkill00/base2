# Reference recovery checkpoint — 2026-10-13

## Live review ready — 2026-10-14 Budapest

Backend repair PR #72 merged with history preserved to
`fda54744a2e1b8825cca00dab88e635984b3f998`; deployed tree matches validated candidate
`d9d919c`. Complete gate `20261013T223417Z-46790` passed, as did all 20 PR checks
and ten post-merge workflows. The preceding gate retained its failed exact-source
repetition-receipt check; the supported runner regenerated it before revalidation.

Old preview `base2-full-20261013-212358` was destroyed and provider inventory was
verified empty before replacement `base2-full-20261013-225415` launched. The new
preview is https://woodkilldev.com/, staging TLS only, expiry 2026-10-13T23:54:19Z
(01:54 Budapest October 14), workstation teardown around 01:55. Keep WSL running;
its transient teardown timer does not survive a workstation shutdown.

Public content list/search return 200; unpublished About returns the intended 404
and visible unpublished-content state, not the former 503. Mobile/desktop public
route matrices, original-design interactions, operator admission, Django/pgAdmin
logins, signup/settings/accessibility/privacy export, safe/hostile media admission,
saved Woodkill login and runtime verification all have passing live evidence.

Retain two live fixture failures: URL readiness was earlier than React's dashboard
commit, so the harness could click the departing menu; require the actual dashboard
heading before interaction. Revised media fixture setup previously provisioned the
original account; corrected the workstation helper to honor the validated revision,
with a pure hostile-input regression test, then the affected media test passed.
Neither fix changes deployed product code or styling. This closeout branch only
changes the live test readiness assertion and documentation.

Evidence: `.artifacts/feature110/public-content-*`; private run directories
`browser-f110-content-fixed`, `browser-f110-settings-ready-r1`, and
`browser-f110-media-revision-fixed`. Inspected actual mobile About and desktop
Appearance screenshots. Runtime confirms migrations, healthy checked services,
preferences audit and completed privacy export. Earlier failed attempts remain
retained; passing evidence is not proof against unknown defects.

Implementation/live verification is ready for owner review. Final owner visual
acceptance and expiry teardown remain separate; neither is claimed complete now.
The original native-test instability remains a disclosed historical environment
risk. The cause of the workstation restart has not been established.

## Current live checkpoint — supersedes historical pending statuses below

PRs #70 and #71 merged; deployed main is
`07f85cec30aa3f65d55bde5afc9bbe14b109f315`. PR #71 preserved reviewed ancestry.
Final full gate `20261013T210403Z-908786` passed 120/120 checks; all 20 hosted
PR checks and ten post-merge workflows passed. Original design images unchanged.

Preview `base2-full-20261013-212358` is live at https://woodkilldev.com/ with
staging TLS, lease expiry 2026-10-13T22:24:01Z and workstation teardown scheduled
around 22:25Z. WSL must remain running for its teardown timer. Prior failed
preview was deleted before this launch; no duplicate was retained.

Saved owner login and runtime verification passed. Live browser round passed
7/8 scenarios, including Django/pgAdmin secondary logins and media admission.
The remaining scenario hit an ambiguous status locator, not a failed save.
Two content-specific locators corrected it; the complete affected signup/settings/
privacy journey passed in 24.7 seconds with a fresh bounded test fixture.
Evidence: `/tmp/f110-live-{owner-login,browser,settings-r1,runtime}.log` and
private preview `browser-f110-final` / `browser-f110-settings-r1` captures.
Discord notification delivery was confirmed.

NOT fully complete: actual screenshot review exposed public CMS pages returning
503 despite passing shell-layout checks. Sanitized read-only diagnosis confirmed
`InsufficientPrivilege` in the public-content repository using the restricted API
role. See `/tmp/f110-live-content-diagnostic.log`. Secure backend repair scope
has been requested from the owner; no broad database grants were added. Owner
review and public-content functional acceptance remain open. Existing intermittent
local native-test crashes remain disclosed, not proven permanently resolved.

This round used three full release gates (pass, ancestry failure, corrected pass)
and two preview attempts (first removed, second live). Test-only closeout changes
are separate from the deployed product commit. No claim of unknown-defect absence.

## Latest validated composition checkpoint

### Hosted-security correction

Local full gate on 2695c5d passed all 120 checks in 717 seconds; PR #70 is published.
Hosted application/visual checks passed, but pip-audit/SBOM blocked merge on Python
dependency advisories. Patched API/Django/provider/inspector pins and added JWT,
OAuth client/PKCE and lock-consistency regressions. JWT tests failed on the old
version and passed after upgrade. Fresh API, Django and provider audits report
zero findings; the inspector closed-set audit is also clean. Its actual pinned
container build and isolation/signed-spool/two-UID acceptance passed, preserving
the platform-specific hashes. See `/tmp/f110-*-audit-repaired*.log`,
`/tmp/f110-inspector-{build,container,spool}.log` and private Feature 110 artifacts.
OAuthLib 4.0's provider-side breaking changes were reviewed; Base2 uses the client
dependency and its composition test passes. No auth redesign or gate waiver.

Fresh ClamAV updater health passed the existing 24-hour/signature checks, allowing
a full preview attempt after release acceptance. No cloud resource created.
Current-source final gate and hosted revalidation remain pending after this batch.

### Approved dependency repair — awaiting exact-source release gate

Tailwind/PostCSS 4.3.3 and Axios 1.20.0 plus patched transitive dependencies remove
all current audit findings. Three CSS compatibility regressions were reproduced
and repaired without changing any PNG: sibling spacing, rem line height and native
file-selector metrics. Final matrices passed 69 Volcano, 22 Operations, 24 Media,
24 Workspace, 15 Ember compatibility and 10 Northstar settings cases; deliberate
project/state skips remain explicit. All 326 frontend tests passed with coverage,
Storybook built, TypeScript passed and lint has zero errors (24 existing warnings).
The reference integrity contract passes all three checks. Operations evidence
correctly rejected the prior source binding (five negative-contract tests passed);
refresh it only after the completed visual review. Full gate, publication, live
verification and owner review remain pending. No cloud resource was launched.
VOL-07 remains a disclosed intermittent runtime risk, not a resolved root cause.

### Release blocker — final round 2

Exact candidate `a603bfd6cb0164e19f863378cb915eea1d6fec31` completed the full
gate with **119 passed, 1 failed, 0 blocked** in 822 seconds. The only failed
check is `frontend-production-audit`: 11 dependency findings (9 high, 2 moderate).
Evidence: `.artifacts/complete-gate/20261013T175414Z-636889/result.json` and
`frontend-production-audit.log`. This is NOT a release pass. The frontend attempt
first exited without a terminal summary; its single policy-bounded retry passed
all 323 tests. Both attempts remain retained in `frontend-test.log`; the underlying
environment cause is not fixed.

All local browser matrices and coverage gates passed. Original Home reference
images remain unchanged. Changes are committed locally, but Feature 110 has not
been pushed, merged or deployed. Read-only DigitalOcean inventory returned zero
Base2 preview droplets and zero managed preview A/AAAA records. Discord is healthy.

Registry/advisory verification found braces latest 3.0.3 with no published fix for
GHSA-vfj7-8cjw-p6xm. Tailwind 3.4.19 depends on this build-tool chain; npm proposes
a breaking Tailwind 4 migration. Axios has a same-major update available. Do not
run audit fix --force, exclude development dependencies, waive the gate or change
original screenshots to hide a migration regression. A broader dependency-hardening
batch needs owner direction before proceeding. Preserve the current candidate as
the design reference and rollback point.

Release completion batch: Docker/Compose now select the approved Volcano layout.
Operations 22, Media 24 and Workspace 24 applicable browser checks pass after
closed-panel geometry, compact account wrapping and touch-target corrections.
Original Home reference integrity, TypeScript and focused lint pass. Intentional
route-shell captures were inspected before acceptance; all eight original Home
references remain unchanged. Full gate, final exact-source coverage, publication
and live verification remain pending. No new cloud resource exists.
Earlier checkpoint descriptions below refer to their named historical source.

Candidate `72f3a1f` is committed locally, not published, merged or deployed.
Final current-source results: 323 frontend tests passed; TypeScript and focused
lint passed; 69 Chromium browser checks passed in 40.9 seconds, with stable source
binding at `.artifacts/layout-109/volcano-final-composition-110/evidence.json`.
All eight original Home images match without reference replacement. Changed
executable lines are 78/78 covered (100%); critical glass/theme coverage is 100%
for lines, statements, functions and branches. Other backend reports used by the
coverage preflight are historical and do not constitute a fresh full release gate.

Release is NOT complete. Operations/media success-state matrices and their shared
source-bound review manifests, broader profile/browser acceptance, production
activation, the full release gate and publication remain pending. The native Node
crash recorded in VOL-07 remains an intermittent environment risk despite later
passes. No cloud resources were created. Details below retain earlier rounds.

Status: original-design route composition implemented in local preview; NOT release complete.
Branch: `110-volcano-design-preservation`. V006 owner confirmation received 2026-10-13.

Home's retained original composition is selected with `VITE_VOLCANO110_PREVIEW=true`.
This is not enabled in Docker/Compose. Main and deployment remain unchanged.
No new provider resource, merge or publication occurred in this repair batch.

## Evidence

- Original captures: eight Home/left/right/palette PNGs at 390 and 1440px, bound by
  `reference.json`. Home CSS, header and footer were not rewritten.
- `volcano-original-110`: initial baseline creation wrote files, correctly causing
  the source-drift reporter to reject the run despite passing browser scenarios.
- `volcano-original-verified-110`: preserved 11-pixel mobile utility-label timing
  difference. Freeze CSS motion during reference captures only; no content masking,
  geometry alteration, or comparison-tolerance increase.
- `volcano-reference-check-110`: original reference passed without image updates.
- `volcano-rejected-design-red-110`: both widths fail against generic production
  layout because the gradient/original navigation is missing.
- `volcano-restored-110`: both restored cases pass all eight original screenshot
  comparisons, with no baseline updates and no source drift.
- 17 existing Home/navigation/accessibility unit tests pass. TypeScript and focused
  ESLint pass. Two reference-integrity/deployment-isolation tests pass.
- The unit environment warns that window.scrollTo is unimplemented; real-browser
  checks exercise menus. This is not a claim that all scroll states are certified.

Artifacts: `.artifacts/layout-109/<attempt>/` and `<attempt>-report/`.
Reference gallery: `review.html`. Screenshots contain synthetic local data only.

Owner also confirmed changes must extend the approved design rather than replace
it. This rule is now in AGENTS.md. Original reference PNGs remain unchanged.

Extension batch: optional permission-filtered route adapter reuses original menus;
new VolcanoLayout composes original header/footer/background around route content,
retains account controls and page context, and isolates media dialogs. New route
palette focus containment restores inert/background state on closure.

`volcano-all-routes-110` passed 62 browser cases (38.3 seconds), including 22 guest
routes and 8 authenticated routes at both sizes plus all 8 original Home images.
These are synthetic unavailable-service fixtures, not successful live API flows.
39 focused Home/navigation/media tests passed. Broader frontend round: 318 passed,
2 failed because the new test location helper used an output element with implicit
status role, colliding with real status messages. Fixture corrected to a div;
rerun required. Mobile admin review found edge tabs too near body copy: reserved
route-only gutters added; Home stays untouched. New captures required for that edit.

Final focused coverage collection retry passed all 321 frontend tests. The critical
glass/theme subset is 100% for lines/statements/functions/branches; whole frontend
lines are 79.18%. First native crash remains recorded as unresolved intermittent
runtime risk; the successful diagnostic retry is not a fix. Committed changed-line
coverage still needs measurement. Both light/200% zoom repairs passed; signup and
RTL captures were visually inspected. Home reference files were never updated.

Remaining: all-page interaction/success/error states, responsive/theme/profile
review, affected coverage, source binding/production activation, release gate and
publication. No complete release gate or deployment has run for this batch.
An integrity guard catches image replacement; changing both manifest and images
still requires code/owner review. It is not a cryptographic approval service.
