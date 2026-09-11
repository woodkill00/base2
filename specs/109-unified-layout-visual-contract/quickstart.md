# Working on Feature 109

Use native WSL `/home/woodkill/code/base2` and branch
`109-unified-layout-visual-contract`; preserve prior Feature 108 work.

Planning validation:

```bash
python3 specs/109-unified-layout-visual-contract/validate_plan.py
python3 -m unittest discover -s specs/109-unified-layout-visual-contract -p 'test_validate_plan.py'
git diff --check
```

Start implementation at T001, not broad CSS edits. Baseline/route inventory first,
then failing tests and shared foundation. Stop for representative owner review at
T013. Use the existing `scripts/bash/assure.sh` workflow for supported affected checks.
Do not run full release/provider tests for planning-only Markdown changes.

Before release: exact-head repetition evidence and tool prerequisites, then the
mandated `scripts/python/run_complete_gate.py`. Private evidence directories require
unique attempt IDs. Live deployment needs its own exact source/budget/TTL authority;
this branch creation does not alter the currently running preview or its expiry.

Known follow-up boundary: disabled media stays disabled until separately approved.
Final acceptance is automated evidence plus explicit owner visual approval, not an
unchecked task list or a claimed 100% guarantee.

# Deployment and rollback switch

Both supported Compose build definitions pass `BASE2_SHARED_LAYOUT`, default true,
to the frontend Docker build. The Dockerfile exposes it as
`VITE_LAYOUT109_PREVIEW`. To roll back the visual integration without touching
accounts or data, set `BASE2_SHARED_LAYOUT=false` and rebuild through the existing
supported deployment entrypoint. This is a rebuild-time switch, not a runtime
authorization flag. Direct Vite diagnostic runs must explicitly set
`VITE_LAYOUT109_PREVIEW=true`; the layout Playwright harness does this itself.

The required complete gate and frontend CI run the layout browser matrix. Attempts
cannot reuse directories, and `evidence.json` records source digest/commit, platform,
case outcomes and attachment hashes. Per-case attachments record actual browser
version, fonts, viewport, profile and synthetic-fixture identity. A changed source
during a run fails the evidence reporter. These are synthetic UI checks, not proof
of live provider/API success. Owner visual acceptance remains a separate decision.
