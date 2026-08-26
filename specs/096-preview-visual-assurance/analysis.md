# Analysis Log

## Cycle 1 - Initial consistency and completeness

Findings:

1. A single operator command without an explicit mutation boundary could accidentally broaden authority.
2. Exact-address verification could hide broken public DNS if represented as one combined success.
3. Automatic expiry was underspecified without installation verification and reboot catch-up.
4. “Every device” is not a finite testable claim.
5. SVG-only wording would incorrectly reject photographs and screenshot evidence.

Corrections:

- Split read-only control receipts from existing separately authorized lifecycle mutations.
- Required independent DNS and exact-address receipts.
- Added exact expiry planning, armed-state verification, persistent catch-up, and observer reporting.
- Replaced universal-device language with a declared rendering contract and expandable matrix.
- Added classified raster exceptions and an SVG-required UI-artwork policy.

Open findings: task-level security, fault, and test coverage analysis remains.

## Cycle 2 - Authority and lifecycle review

Findings:

1. FR-001 omitted `launch`, contradicting the one-workflow user story.
2. A launch command without a closed configuration schema could become arbitrary-command authority.
3. Expiry arming after launch could fail and leave a verified but unbounded resource.
4. A timer pointing at a temporary feature checkout could break after branch deletion.
5. Cost, provider throttling, durable failure notification, and evidence retention were outcomes without ordered implementation tasks.

Corrections:

- Added schema-validated owner-only launch configuration and exact-main admission.
- Constrained launch to the existing guarded launcher and deterministic archive operation.
- Required immediate exact cleanup if expiry cannot be armed and verified.
- Required a stable expiry target across normal checkout changes.
- Added T071-T083 for provider reconciliation, throttling, cost, outbox, retention, hostile inputs, reboot, and output safety.

Open findings: DNS observation trust, timer installation authority, and visual matrix cost require further analysis.

## Cycle 3 - Trust, timer, and visual-cost review

Findings:

1. An unbound DNS observation file could falsely claim convergence.
2. TTL values are not available from every system resolver and must not be fabricated.
3. Timer installation is a system mutation and requires a fixed user-unit boundary; arbitrary unit content or sudo installation is unacceptable.
4. Running every viewport/browser/state combination on every pull request would create excessive latency without improving the fastest feedback loop.
5. Screenshot evidence can be nondeterministic when fonts, lazy content, or animations are unsettled.

Corrections:

- Added source/time/address/answer/digest provenance and explicit unknown TTL.
- Constrained installation to a fixed exact-run user timer; system-wide installation and request-supplied commands remain forbidden.
- Split representative PR coverage from an expanded required release matrix.
- Added font, lazy-content, animation, dimension, and byte stability requirements.

Open findings: interrupted launch recovery and all-controller-offline behavior require explicit treatment.

## Cycle 4 - Crash, outage, and cleanup review

Findings:

1. Process termination after Droplet creation but before lease creation can leave an exact-tag orphan even when ordinary exceptions clean up.
2. No software timer can perform wall-clock cleanup while the workstation, Pi, and every approved controller are offline.
3. Provider throttling during teardown must preserve resumable state rather than report destruction.
4. DNS cleanup can be partially complete and must resume from exact record state.

Corrections:

- Added a pre-mutation launch-intent journal and exact-tag reconciliation.
- Changed the objective from impossible universal wall-clock guarantee to exact eventual cleanup with explicit controller-coverage status.
- Added primary/backup/offline reporting, next-boot catch-up, bounded rate-limit recovery, and partial-cleanup tests.

Open findings: SVG safety, accessibility, baseline review, and cross-browser release coverage remain.

## Cycle 5 - Visual, accessibility, and asset review

Findings:

1. Extension-based SVG policy alone would admit script or external active content.
2. Visual screenshots do not replace accessibility, keyboard, touch, large-text, or contrast assertions.
3. Baseline update state needs an explicit review artifact rather than an implied filesystem change.
4. Chromium-only proof can miss engine-specific layout behavior.

Corrections:

- Added SVG content, viewBox, and semantic checks.
- Added accessibility and input-mode release contracts.
- Added review sidecars and deterministic contact sheets.
- Added supported Chromium/Firefox/WebKit release coverage while retaining the bounded PR matrix.

**Result**: `NO_UNRESOLVED_SPEC_OR_TASK_FINDINGS`
**Next state**: implement T008-T096 in dependency order and repeat analysis against the implemented system.

## Cycle 6 - Implemented-system analysis

Findings:

1. The initial responsive release matrix found real short-landscape footer collisions and a sub-24-pixel utility rail on compact screens.
2. WebKit mobile does not expose a reliable desktop keyboard shortcut, so treating it as keyboard-only coverage was nondeterministic.
3. Exact-pixel icon antialiasing varied by six pixels between otherwise identical mobile captures.
4. The first control-plane test set did not exercise enough hostile input and CLI routing to satisfy the changed-line coverage target.
5. Provider retry, artifact context, semantic SVG use, exact browser targeting, and evidence retention needed stronger implementation evidence.

Corrections:

- Added short-landscape safe zones, a fixed 24 CSS-pixel rail floor, and reduced-motion transition removal while retaining calculated responsive layout.
- Kept keyboard-only proof on desktop engines and tested the actual visible touch control on WebKit mobile.
- Added a narrowly scoped 20-pixel maximum diff only to the icon-bearing mobile utility snapshot; all geometry and behavior assertions remain exact.
- Expanded the focused suite to 32 tests covering hostile DNS/runtime/config/evidence inputs, CLI routing, exact teardown delegation, bounded retries, persistent expiry, outbox behavior, and retention safety.
- Added signed-lease exact-address derivation, browser/viewport/route/state artifact context, bounded 429 retry receipts, SVG accessible-name checks, fixed cost output, and cleanup restricted to old unapproved visual artifacts from destroyed runs.

Verification:

- Feature 096 focused suite: 32 passed.
- DigitalOcean suite: 308 passed across nine isolated coverage partitions.
- Feature 096 weighted Python line coverage: 92.0%.
- React unit suite: 131 passed; lint and production build passed.
- Existing visual harness: 49 passed, 4 intentionally skipped, zero failures after the reviewed baseline update.
- Expanded release matrix: 24 passed across compact, DPR3 phone, short landscape touch, tablet, 200% text, ultrawide, Firefox, and WebKit mobile profiles.
- Complete repository gate: passed at `20260826T144436Z`.
- Surface drift and SVG asset policy: zero findings.

**Result**: `NO_UNRESOLVED_IMPLEMENTATION_FINDINGS`
**Next state**: publish, merge, execute one bounded exact-main canary, verify evidence and expiry, then tear it down exactly.

## Cycle 7 - Live acceptance and durability refinement

Findings:

1. Run `base2-full-20260826-150100` proved that this host's `systemd-run --on-calendar` rejects the lease's fractional RFC 3339 timestamp. The launch failed closed and exact cleanup deleted one Droplet and six DNS records.
2. Run `base2-full-20260826-151700` passed all eight routes and the four exact-address browser suites, but its transient user timer disappeared when the WSL user manager session ended even though the in-transaction check had reported it active.
3. The first durable-unit host drill correctly rejected a quoted `WorkingDirectory=` value as a bad systemd setting.
4. The WSL system resolver retained two previous preview answers while the live provider records and Google Public DNS agreed on all six exact records.

Corrections:

- Converted the signed lease expiry to `YYYY-MM-DD HH:MM:SS UTC` only at the systemd adapter boundary, preserving the integrity-bound lease value.
- Replaced transient units with atomically written owner-only user service/timer files, `enable --now`, and verification of loaded, active, and enabled state.
- Added systemd-directive path validation separate from quoted `ExecStart` argument encoding.
- Added exact unit removal to teardown and failed-arm cleanup.
- Preserved DNS source separation: provider/public convergence is green, system-cache staleness is typed `DNS_STALE_RECURSIVE`, and exact-address browser proof remains independent.

Verification:

- Implementation PR #20 merged at `4b4e172c7bb20cb80d2205260e4ae5f3c7aab57b`; expiry calendar repair PR #21 merged at `434dfb7fdc2d557d7273e54373ecbd0aca24a950`; durable-unit repair PR #22 merged at final canary source `44c6358ba9c5c7b3d42be8d2c905eba38595c90c`.
- Focused control-plane suite: 32 passed after each repair. Complete DigitalOcean suite: 311 passed. The real harmless timer drill survived `systemctl --user daemon-reexec` and was removed exactly.
- Final run `base2-full-20260826-154400` deployed one Droplet, six DNS records, all eight routes, the `base2-obsidian` profile, and staging-only certificates under the USD 0.25 ceiling with an estimated USD 0.025 maximum.
- Its durable timer used owner-only mode `0600`, was loaded, active, and enabled from a fresh WSL session, and retained the same next elapse after user-manager daemon re-exec.
- Exact-address Playwright acceptance passed all four suites: public identity/interactions, responsive visual coverage, operator-host denial/owner access, and authenticated Django/pgAdmin login.
- The approved visual evidence bundle contains 45 artifacts, zero missing files, bundle digest `33d0b4b180ad867080090dfc5b866a737973d6c390cdf526829314ca3f627dc5`, and zero emitted secret values.
- DigitalOcean live records and Google Public DNS agreed on all six A records at `142.93.161.112` with no AAAA records. The WSL DNS proxy retained only the prior Traefik and Flower addresses and was reported as `DNS_STALE_RECURSIVE` rather than hidden.
- Exact teardown deleted one Droplet and six DNS records, removed both durable unit files, and left the timer absent. Immediate replay removed nothing further. Final provider inventory is empty with zero unresolved run IDs.
- PR #20 completed the full green CI matrix. The two narrow live-repair PRs passed all executable frontend, smoke, security, and policy checks; repeated backend/contract jobs experienced GitHub zero-step startup/queue failures, while their stronger local 311-test suite remained green.
- The first closeout complete gate encountered one unreadable file inside its disposable module-checkpoint temporary directory. The same 18-module/90-transition checkpoint passed immediately, and the complete gate then passed at `20260826T161333Z`; the anomaly did not recur or affect persistent state.

**Result**: `FEATURE_096_COMPLETE`
**Next state**: merge this evidence-only closeout; no preview resource or active expiry unit remains.
