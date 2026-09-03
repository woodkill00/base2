# Validation Quickstart: Universal Content and Data Workspace

Run from the native WSL checkout and use repository entrypoints. Planning validation is credential-free and creates no provider resources.

```bash
cd /home/woodkill/code/base2
python3 specs/104-universal-content-data-workspace/validate_plan.py
python3 specs/104-universal-content-data-workspace/test_validate_plan.py
git diff --check
```

During implementation, run focused tests first and then the supported repository gates:

```bash
cd /home/woodkill/code/base2
scripts/bash/test.sh
scripts/bash/complete-gate.sh
```

## Test-first checkpoints

1. Django model, validation, authorization, workflow, and reversible migration tests fail before canonical model implementation.
2. SQL parity, RLS, repository, API contract, worker, and failure-injection tests fail before FastAPI/worker implementation.
3. Generator/preset determinism and disabled-capability tests fail before manifest/compiler changes.
4. React unit, accessibility, interaction, and visual contract tests fail before UI implementation.
5. Import/export, media, search, saved-view, backup/restore, and compatibility tests pass before removing any placeholder behavior.
6. The full gate and implemented-system analysis are clean before publication is considered.

## Required evidence

- Exact commit and clean-tree record.
- Requirement/task/test/evidence traceability validation.
- Django and SQL migration parity plus forward/reverse proof.
- PostgreSQL tenant/RLS and cross-scope negative results.
- API/OpenAPI and generated-profile contract results.
- Worker restart, replay, dependency failure, and terminal-state results.
- Security negative suite and zero-finding tracked/history secret scans.
- JSON/CSV round-trip, duplicate-review, formula-neutralization, and interrupted-job results.
- Backup/isolated-restore integrity comparison.
- Representative and expanded accessibility/visual reports with explicit review sidecar.
- Complete-gate summary with no unresolved or silently skipped required check.

## Live boundary

A live DigitalOcean canary is not part of planning or ordinary implementation. If separately authorized, it must use `digital_ocean/orchestrate_deploy.py`, exact reviewed source, staging certificates, an explicit cost ceiling and lifetime, synthetic accounts/data, no production credentials, exact teardown, immediate teardown replay, and empty exact-owned provider inventory.
