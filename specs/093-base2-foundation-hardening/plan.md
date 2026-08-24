# Implementation Plan: Base2 Universal Website Foundation

**Branch**: `093-base2-foundation-hardening` | **Date**: 2026-08-24 | **Spec**: [spec.md](spec.md)

## Summary

Harden current Base2 before expanding it. The order is: truthful gates and deployment substrate; current-main visual port; versioned site manifest and real public workflows; accounts/admin and isolation; module contract and representative packs; recovery; then a provider-bounded factory with disposable DigitalOcean previews.

## Technical Context

**Language/Version**: Python 3.12, Node.js 24.x, JavaScript/TypeScript, Bash, PowerShell 7+
**Primary Dependencies**: Django, FastAPI, React/CRA (modernization target decided by evidence), PostgreSQL, Redis, Celery, Traefik, Docker Compose v2, Playwright, Jest, pytest
**Storage**: PostgreSQL canonical state; Redis bounded cache/queue state; object-storage abstraction for media/backups; private redacted evidence
**Testing**: pytest, Jest, Playwright, axe, Storybook, Compose smoke/contract tests, k6, dependency/image/IaC/secret scanning
**Target Platform**: Linux containers locally/CI and disposable DigitalOcean Linux previews
**Project Type**: Multi-service web foundation and repository generator
**Performance Goals**: Public p75 LCP <=2.5s and INP <=200ms; core API p95 <=300ms; teardown begins within 5 minutes of expiry
**Constraints**: Production parity; no secret commits; staging certificates only; fail-closed gates; scoped provider authority; no stale branch promotion
**Scale/Scope**: One core, 12 representative packs, two fixture brands, multiple tenants, one first-class preview provider

## Constitution Check

### Pre-research

- Constitution → Spec → Plan → Tasks → Code: **PASS**
- TDD and coverage review: **PASS**, mandatory task order
- Production parity and Compose-first: **PASS**
- Sole deploy implementation through `orchestrate_deploy.py`: **PASS**
- Bash/PowerShell parity: **PASS**, new operations require both wrappers
- Observable artifact evidence: **PASS**
- Django → FastAPI → React order: **PASS**
- Internal-by-default and staging-only certificates: **PASS**
- Security/documentation governance: **PASS**

### Post-design

**PASS**. The module registry coordinates declarations but does not replace Django domain ownership. Provider mutations remain behind the existing orchestrator. No exception is required.

## Architecture and delivery slices

1. **P0 truth layer**: reproducible fixtures, honest gate manifest, coverage policy, blocking security, typed startup failure.
2. **P0 deploy layer**: portable frontend image, correct health, TLS bootstrap, strict env parsing, leases, DNS transaction, cleanup, evidence.
3. **P1 experience layer**: current-main visual port, tokens/components, site manifest, pages, content/search/forms/media/SEO/consent.
4. **P1 identity layer**: accounts, MFA/WebAuthn, organizations, RBAC, isolation, audit, admin, data lifecycle.
5. **P2 module layer**: versioned SDK and representative packs, payment-impacting packs disabled/sandboxed.
6. **P2 operations layer**: telemetry, alerts, SLOs, backup/restore, rollback, DR, provenance.
7. **P3 factory layer**: immutable export, child identities/manifests, compatibility/upgrade tooling, disposable previews.

Each slice has an independent acceptance checkpoint; later slices cannot weaken earlier gates.

## Project Structure

```text
api/                         # FastAPI mirrors, policy, tests
django/                      # canonical models, migrations, admin, tests
react-app/                   # client, design system, Storybook, visual/E2E
shared/                      # versioned schemas/generated contracts
modules/                     # declarative pack definitions/adapters
site_profiles/               # fixture/example manifests, never secrets
digital_ocean/
  scripts/python/            # sole provider implementations
  scripts/{bash,powershell}/ # shell-native wrappers
  tests/                     # providerless/live-canary tests
scripts/                     # complete gate, manifest, factory, evidence
e2e/                         # cross-service journeys
specs/093-base2-foundation-hardening/
```

**Structure Decision**: Preserve the monorepo. Add `modules/` and `site_profiles/` as declarative coordination layers, not alternate frameworks.

## Key technical decisions

- Port the reviewed net design delta from the 231-commit visual branch by token/component mapping onto Feature 093, never by wholesale branch promotion.
- Replace Dockerfile-generated config with checked-in validated config.
- Define health commands per image capability and test them in built images.
- Parse environment files with one strict shared implementation; reject malformed input before mutation.
- Make the complete gate manifest-driven with explicit status and immutable evidence.
- Use strict JSON Schema plus semantic validation for site/module manifests.
- Keep content/module state in Django; FastAPI mirrors it and enforces tenant policy.
- Make screenshots deterministic by freezing fonts, data, time, locale, network, viewport, and animation.
- Use ownership tags, immutable provider IDs, and atomic receipts for cleanup.
- Generate child repos from `git archive` of an exact commit, not a worktree copy.

## Migration strategy

1. Freeze current-main baseline evidence.
2. Repair P0 gate/deploy without changing appearance.
3. Port visual behavior with approved screenshot diffs.
4. Add manifest defaults that reproduce the current site; remove hardcoded branding incrementally.
5. Replace no-ops with real contracts, explicit disabled states, or removal.
6. Add persistent features in Django → FastAPI → React order.
7. Add modules/factory only after isolation and recovery gates pass.

## Risk register

| Risk | Mitigation |
|---|---|
| Umbrella scope hides incomplete work | Ordered tasks, checkpoints, traceability, no blanket done status |
| Stale design reintroduces defects | Patch-level current-main port and full gate replay |
| Security stays cosmetic | Failure-injection tests and CI suppression-policy scan |
| Cleanup deletes wrong resource | Provider ID + tags + lease digest + compare-before-delete |
| Tenant data leaks | Tenant key/policy in models, caches, jobs, search, APIs, hostile tests |
| Packs bloat/weaken core | Declarative boundaries and isolated activation tests |
| Screenshots flake | Hermetic assets/data/time/network and governed baselines |
| Testing completeness is overstated | Requirement/control/state ledger plus residual-risk report |

## Definition of Done

- Requirements map to implemented tasks and passing evidence.
- Task completion is backed by reproducible validation.
- No unresolved analysis findings, placeholders, silent failures, or unexplained skips.
- Code, docs, migrations, schemas, artifacts, and rollback agree.
- Three provider canaries leave zero owned resources.
- A generated-site trial passes its gate and teardown.
- Production-impacting activation remains separately authorized.
