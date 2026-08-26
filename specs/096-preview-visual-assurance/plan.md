# Implementation Plan: Deterministic Preview Orchestration and Visual Assurance

## Summary

Feature 096 composes the existing guarded launcher, lease-v2 teardown, DNS migration, exact-address probe, and Playwright live gate behind a new credential-free control plane. It adds native-runtime admission, lease inventory, DNS convergence evidence, persistent expiry planning, visual artifact indexing, typed diagnostics, and one Bash entrypoint.

## Architecture

1. `preview_runtime.py` validates native WSL/Linux tools and paths.
2. `preview_inventory.py` discovers integrity-valid lease envelopes and summarizes lifecycle state.
3. `preview_dns_convergence.py` normalizes provider/public/system DNS observations without performing writes.
4. `preview_expiry.py` builds and verifies exact persistent expiry plans; execution remains the existing lease-v2 teardown.
5. `preview_visual_evidence.py` validates, hashes, and indexes screenshot/test evidence.
6. `preview_control.py` exposes deterministic subcommands and typed receipts.
7. `base2-preview.sh` is the WSL-only operator entrypoint.

## Security model

- Read-only commands never accept or open provider credentials.
- Mutation commands delegate only to existing fixed operations.
- State roots and evidence roots must be owner-only real directories.
- Paths are resolved and constrained before use; symlinks are rejected.
- Receipts contain IDs, hashes, counts, states, timestamps, and safe remediation only.
- Exact-address browser verification does not relax public DNS requirements.
- Expiry commands contain fixed module entrypoints, not request-supplied shell text.

## Delivery phases

1. Specifications, contracts, failing tests, and closeout evidence.
2. Runtime and state-root admission.
3. Lease inventory and reconciliation receipts.
4. DNS convergence model and diagnostics.
5. Persistent expiry planning and verification.
6. Visual evidence manifest, HTML index, and asset policy.
7. Unified CLI and Bash entrypoint.
8. Responsive/visual/fault matrix expansion.
9. Complete gates, live canary, exact teardown, and closeout.

## Test strategy

- Pure unit tests use temporary owner-only roots and fake resolvers/providers.
- CLI tests prove stdout is valid sanitized JSON and stderr is bounded.
- Fault tests cover integrity failure, symlinks, stale DNS, split DNS, Windows binaries, timer drift, duplicate artifacts, partial cleanup, and replay.
- Visual tests retain representative PR viewports and add expanded release-only geometry coverage.
- The live canary uses staging-only certificates, one owner `/32`, exact-address Playwright, and exact lease teardown.

## Rollback

- Code rollback is a normal Git revert of the feature commit.
- No migration changes existing lease-v2 envelopes.
- New indexes and receipts are derived artifacts and can be deleted without affecting provider state.
- Existing launcher and teardown modules remain independently callable.
