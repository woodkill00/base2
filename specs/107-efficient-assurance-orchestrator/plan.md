# Implementation Plan: Efficient Assurance Orchestrator

**Branch**: `vscode-codex/107-efficient-assurance-orchestrator` | **Date**: 2026-09-10 | **Spec**: `spec.md`

## Summary

Add a policy-driven assurance planner and runner in front of the existing test entrypoints. It selects transitive checks from an explicit change graph, reuses only exact integrity-bound evidence, emits compact receipts, and escalates risky or unknown changes. The existing complete production gate remains the release authority and is not replaced.

## Technical Context

**Language/Version**: Python 3.12, Bash, PowerShell 7  
**Primary Dependencies**: Python standard library; existing pytest, Vitest, Playwright, Docker Compose, GitHub Actions  
**Storage**: Private ignored `.artifacts/assurance-orchestrator/` JSON and log bundles  
**Testing**: pytest/unittest, policy tests, shell parity, deterministic fixtures, mutation tests, bounded real acceptance  
**Target Platform**: WSL2 Ubuntu, Linux CI, Windows PowerShell wrapper  
**Project Type**: Multi-service web application and generated-site platform  
**Performance Goals**: ≥50% median routine-time reduction; ≥90% output reduction; ≤4 KiB successful output  
**Constraints**: No loss of mandatory release coverage; no new authority; fail closed; low memory/concurrency  
**Scale/Scope**: Current Base2 repository, generated children, 111-check complete gate, all existing CI workflows

## Constitution Check

- Test-first: selector, graph, evidence, failure, mutation, and parity tests precede implementation.
- Environment parity: checks call existing entrypoints; no alternative fake production topology.
- Container-first: integration checks retain Compose; narrow tiers avoid it only when risk does not require it.
- Single entrypoint: wrappers are repository-supported and release delegates to `run_complete_gate.py`.
- Shell parity: native Bash and PowerShell wrappers invoke the same Python contract without cross-shell calls.
- Observability: compact public receipts point to private complete evidence; no silent skip.
- Security: unknown changes escalate; paths, commands, and evidence are closed and versioned.

No constitutional exception is required.

## Architecture

1. `shared/config/assurance-orchestrator-v1.json` is the closed graph: path rules → surfaces → checks → dependencies, risk floors, cache policy, resource class, and command IDs.
2. `scripts/python/assurance_orchestrator.py` admits a clean exact source, calculates a normalized diff, validates the graph, resolves a tier, and creates a deterministic plan.
3. Commands are fixed in configuration and validated against an allowlist; users cannot inject shell, paths, environment, or arbitrary arguments.
4. A private no-follow evidence store records per-check logs and receipts plus an aggregate run receipt. Exact replay is allowed only where policy permits.
5. A nonblocking private lease prevents duplicate runs. Resource classes cap concurrency; initial implementation is deliberately serialized except safe lightweight checks.
6. `release` delegates to the existing complete gate. It never consumes focused evidence as a replacement.
7. Agent-facing output is a compact JSON or text summary; full logs require an explicit local inspection command.
8. Fixed fixture manifests benchmark selection and mutation detection without repeatedly executing the entire stack during development.

## Project Structure

```text
shared/config/assurance-orchestrator-v1.json
shared/schemas/assurance-orchestrator-v1.schema.json
scripts/python/assurance_orchestrator.py
scripts/bash/assure.sh
scripts/powershell/assure.ps1
scripts/tests/test_assurance_orchestrator.py
scripts/tests/test_assurance_orchestrator_policy.py
scripts/tests/test_assurance_orchestrator_acceptance.py
docs/TESTING.md
specs/107-efficient-assurance-orchestrator/
```

## Delivery Strategy

- First deliver planning and explanation with no execution.
- Add private evidence and exact reuse.
- Add bounded execution and wrappers.
- Add benchmark/mutation fixtures and CI policy integration.
- Run focused acceptance once, then one final complete gate only at the release boundary unless a high-risk change invalidates it.

## Explicit Non-Goals

- Reducing the scope of the release gate.
- Automatically updating visual baselines.
- Treating flaky or failed checks as passing.
- Sending logs or source to an LLM.
- Creating cloud resources or changing deployment authority.
