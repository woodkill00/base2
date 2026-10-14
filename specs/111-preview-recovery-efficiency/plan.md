# Plan

Source: main f9440de2a87eaeac8599d8db1a8c6838fdb84809; native WSL checkout.
Branch: 111-preview-recovery-efficiency. No current provider resources.

## Batches and budget

1. Early durable lease and truthful interrupted-launch recovery: launch, lease store,
   expiry and fake-provider tests. One red run, one corrected focused run; any
   additional run requires a distinct correction. No full gate until all batches ready.
2. DNS journaling, concurrency and persistent workstation scheduling. Reuse existing
   exact-identity expiry, never invent a second delete path. Register scheduling before
   provisioning; require install/activation evidence. Preserve TTL, bounded retries.
3. Move fixture identity/readiness contracts into supported tooling; add prerequisite
   preflight to existing assurance, not another orchestrator or cache.
4. Coverage, security/negative review and required release gate on frozen candidate.

## Trust boundaries

Provider responses are untrusted. Private leases use the existing atomic store and
integrity validation. A prepared lease cannot authorize deletion of an unknown
resource; ambiguous identities block and retain evidence. Store only exception type,
not exception text or secrets. Tests use fakes, never credentials or provider calls.
Add native Bash/PowerShell wrappers for any new operational capability, through the
existing orchestrator entrypoint. Python-only internal changes need no new shell CLI.

## Adjacent consumers

Expiry scans, lease replay, full/restricted launch modes, DNS rollback, workstation
launcher and operator media-principal fixture setup. No UI/style sources change;
existing visual release requirements remain selected by supported assurance.

## Rollback

Retain schema v2 readability. Never remove active leases or reset expiry on replay.
Revert code only after inspecting outstanding nonterminal leases. Existing production
application and database schema are untouched.
