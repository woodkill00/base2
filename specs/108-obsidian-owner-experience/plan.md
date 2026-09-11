# Implementation plan

## Constitution alignment

Spec → plan → tasks → failing tests → code. Canonical models remain in Django
common/models.py; API then React consume them. No new tables assumed. Preserve
cookie/CSRF authentication, network isolation, least privilege and staging-only
certificates. Keep Bash/PowerShell deployment wrappers compatible without
cross-shell composition. Supported deployment remains digital_ocean/orchestrate_deploy.py.

## Sequence

1. Inventory routes/states/tokens, auth and DB runtime context; freeze test matrix.
2. Reproduce signup/error and settings RLS failures before repairs.
3. Specify/test/implement narrow ensure-owner action after migrations; database
   uniqueness and atomic transactions enforce concurrency safety.
4. Consolidate shells/forms/status/navigation; migrate all first-party families.
5. Complete functional, integration, accessibility and deterministic visual tests.
6. Use scripts/bash/assure.sh affected checks during iteration. Complete release
   still delegates to run_complete_gate.py; auth/RLS/deployment changes escalate.
7. Separately authorized bounded preview verifies exact source, vendor login,
   owner access and screenshot review. Failures reopen tasks and targeted repair;
   final evidence must match repaired source. No idle 24-hour gate.

## Activation and rollback

Before activation configure private email/name/tenant/role and approved Vaultwarden
reference. Never reset existing owner password, bypass verification/MFA or elevate
privilege to make tests pass. Preserve databases before migrations and test rollback/
forward recovery on isolated data. Retain existing profile compatibility. Explicit
owner-readiness blocks on failed provisioning without secret-bearing error output.

Reports bind source/environment, required pass/fail/skip, route matrix, screenshots
and human approval. Existing durable notification machinery handles failures.
Keep provider lease teardown independent of test failure; no live TTL extensions
or resource changes are authorized by this plan.
