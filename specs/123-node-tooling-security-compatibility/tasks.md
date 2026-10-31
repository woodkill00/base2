# Tasks / issue ledger — 123

- [x] T001 Record actual moderate audit failures, dependency paths and supported fixes.
- [x] T002 Establish approved scope and preserve unrelated frontend/media work.
- [x] T003 Independently review fixed-version consumer architecture before adapting APIs.
- [x] T004 Add failing fixed-dependency and real-consumer regression coverage.
- [x] T005 Implement scoped dependencies, auditable consumer patches and fail-closed install.
- [x] T006 Validate focused behavior, install drift failures and compatible Node engines.
- [x] T007a Run clean installs, unchanged audits and locally available affected tools.
- [x] T007b Add mandatory bounded Storybook CI build and fail-closed CI contracts.
- [x] T008a Complete independent source review and focused-test rerun.
- [ ] T008b Exact-source Node 20 PR CI and real Storybook build pass.

## Retained failures and status

1. **Moderate dependency gate, locally repaired:** 17 nodes from two globbing advisories.
   The earlier high-only local audit was insufficient; actual CI correctly failed
   the unchanged moderate gate. Research evidence: `/tmp/base2-glob-repair/`.
2. **Major-version compatibility, confirmed:** isolated genuine fixed-package probes
   reject legacy callable default imports with TypeError. Legacy glob 7 also consumes
   matcher internals changed by minimatch 11. Do not force its dependency to 11.
3. **Verification boundary:** this task owns only tooling compatibility; no merge,
   deployment, UI redesign or screenshot approval. Full release acceptance remains
   separate from focused and local checks.

## Validation and retained diagnostics

- First Node-realm regressions reproduced three failures: the vulnerable lock,
  pattern expansion of eight entries despite a limit of four, and three directory
  reads after cancellation instead of one. Fifteen consumer controls passed.
- Installing genuinely fixed libraries before import adaptation exposed thirteen
  real consumer API failures. The intermediate dependency test also caught an npm
  override-selector issue; nesting the modern glob resolution under its actual
  parent removed the remaining old glob/minimatch. No global override was used.
- Final tooling suite: 27 passing; independent reviewer reran all 27 successfully.
  Initial fixture corrections (JSDOM versus Node realm and the actual React rule
  option name) are retained in the first diagnostic, not mislabeled product bugs.
- Clean `npm ci --legacy-peer-deps` with lifecycle scripts applies all three patches;
  isolated `--omit=dev` installation also succeeds without a development patcher.
  Missing/extra/tampered patches, wrong versions, changed source, skipped lifecycle
  application, missing patcher and partial development omission fail closed.
- Actual all-dependency `npm audit --audit-level=moderate` and production-only audit
  both report zero findings. No suppression, scanner adapter or threshold changed.
- Full frontend lint, TypeScript, production build and 564 tests in 101 files pass,
  in addition to the 27 tooling tests. Application coverage: 84.39% lines and
  75.12% branches; existing floors unchanged. New build/install helpers receive
  explicit negative tests; this is not a claimed helper coverage percentage.
- The real OpenAPI generation command passes. Its target was absent before the run,
  so an initial comparison could not run (not a semantic failure). A separate clean
  original-lock installation generates byte-identical output: SHA-256
  `e9bbcfbf9b2d0c87c6d405bc17e5d21bedd0a141bb496fb0fc49f83ce8fd7573`.
  Only this task's generated untracked output was removed afterward; clean-tree
  TypeScript passes again.
- **Storybook remains blocked locally:** the CLI exits before project configuration
  loads because the host denies `uv_interface_addresses`. A bare Node
  `os.networkInterfaces()` call reproduces the same prerequisite failure. No bypass
  or blind retry. Direct optional TypeScript-docgen checks pass but do not replace
  a full Storybook build. Existing full-scope frontend CI now has a mandatory
  ten-minute, telemetry-disabled build step; four new CI contracts plus the existing
  policy suite pass (25 combined tests).
- Detailed logs, source hashes, registry metadata, original failures and baseline
  comparison are in `/tmp/base2-tooling-migration/`. Source review accepts the bounded
  migration; exact-source Storybook/PR CI and complete release acceptance are pending.
