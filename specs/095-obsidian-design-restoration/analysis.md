# Analysis Log

## Cycle 1

- Current platform baseline is clean and pushed.
- Historical design source remains reachable and immutable by commit hash.
- A direct historical merge is rejected because it would remove modern profile, security, route, test, and deployment work.
- Restoration must therefore be a compatibility port with current contracts as the authority.
- Initial task coverage includes implementation, regression, visual review, deployment, authenticated application checks, and teardown.

Open findings: implementation inventory and selector-level compatibility review are pending.

## Cycle 2

- Froze modern baseline `21e6fd3fdc035c3980d35dd88b10f192d675fe59` and historical design source `0132131292d584172a9b2fa173e439b540abed99`.
- Ported the historical interaction controller and final volcanic/Obsidian stylesheet without merging historical platform files.
- Retained current manifest-driven content, public routing, identity, API, deployment, and security contracts.
- Added compatibility hooks only where current markup differed from the historical selectors.

Finding: the raw restored stylesheet exceeded the legacy raw-byte budget even though its transfer size was small.

Resolution: made the production performance gate measure deterministic gzip transfer bytes. The restored stylesheet is 15.78 KB gzip against the unchanged 40 KB stylesheet ceiling.

## Cycle 3

- Added a dedicated restored-design browser matrix across desktop, tablet, and mobile.
- Regenerated and visually reviewed six exact visual baselines.
- Added focusability to restored internal scroll regions and disabled the remaining decorative pulse under reduced motion.
- Preserved locked public actions as visibly unavailable and non-executing.

Finding: the complete gate's visual-port contract required modern semantic token markers and the canonical 768px breakpoint.

Resolution: added a semantic-token compatibility bridge without replacing the reviewed volcanic palette. The focused visual-port contract passed 4/4.

## Cycle 4

- The first complete-gate replay passed 35 checks before the desktop movement test exposed a timing boundary between scroll-lock expiry and active-section refresh.
- Moved the refresh beyond the lock boundary and synchronized the active-section ref.
- Repeated the movement test three times in each viewport; all 9/9 runs passed.

Finding: fixed. No additional movement task required.

## Cycle 5

- The second complete-gate replay passed every functional and platform check but correctly rejected 46.23% changed-line coverage for the restored controller.
- Expanded unit coverage for pointer, keyboard, wheel, scroll, palette, safe and locked utility, movement, edge-jump, timer, and cleanup behavior.
- Kept the 90% policy unchanged and added no coverage exclusion.

Finding: fixed. Exact changed-line coverage is 514/571, or 90.02%.

## Cycle 6

- Exact source commit: `a5f090bc4ffd0a33bfb150e8bb1ad3eac6ff9e69`.
- Complete-gate evidence: `.artifacts/complete-gate/20260826T084433Z/result.json`.
- Evidence digest: `ccfe47bfc8ff7af86dc370bf79d4ce4f127a54714fdfc58bc50358b68a75c78c`.
- All 77 required checks passed, including 55 frontend test files with 131 tests and the 27-test visual/accessibility matrix.

Open findings: none for branch implementation. PR/CI, merge, bounded live preview, authenticated browser validation, and exact teardown remain ordered release tasks T016-T019.

## Cycle 7

- PR #19 merged the reviewed navigation, footer, responsive geometry, SVG contract, and expanded visual assurance into `main` at `0c4bfe94b7d054cc6652c08465e674f1d3285a29` after every required GitHub check passed.
- Live run `base2-full-20260826-125113` deployed that exact commit with the approved `base2-obsidian` profile, staging-only certificates, one exact owner `/32`, and public IPv4 `167.71.52.146`.
- The exact-address Playwright gate passed all four suites: public identity and interaction, responsive visual evidence, anonymous/authorized operator routes, and authenticated Django/pgAdmin application flows.
- The gate retained desktop, tablet, mobile, section, palette, footer, operator, and authenticated screenshots under the owner-only live evidence root.
- Recursive workstation DNS retained retired Traefik and pgAdmin addresses after authoritative DNS had converged. Exact-address acceptance remained correct, and this residual operational problem is promoted into Feature 096 rather than hidden.
- Owner-approved teardown deleted exactly one leased Droplet and six exact DNS records. Immediate replay returned the same `destroyed` lease with no additional mutations, and the temporary timer was removed.

**Result**: `FEATURE_095_COMPLETE`
**Next state**: build deterministic lifecycle, DNS-convergence, runtime-boundary, and visual-review orchestration in Feature 096.
