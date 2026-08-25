# Research: Base2 Universal Website Foundation

## Baseline evidence (2026-08-24)

- Current source: `main` at `5320d3fac8decfb77df75c10b4633821f91cea78`.
- Visual source: `vscode-codex/base2-volcanic-obsidian-layout` at `0132131292d584172a9b2fa173e439b540abed99`. Its merge base is exact current `main`; it is 231 commits ahead, with a net delta of 17 files, 4,513 insertions, and 510 deletions. The tip changes only `home.css`, but the complete visual result spans the full 231-commit delta.
- Frontend lint/build and 45 suites/84 tests pass, but “100%” coverage applies only to selected glass components.
- API tests pass at 52.63% total coverage; auth, tenant limits, user routes, and email paths have material gaps.
- Root environment tests pass 14/28; missing generated fixtures and Linux `pwsh` assumptions coexist with real production/SMTP drift.
- Production frontend audit reports six findings (two high, four moderate); the legacy CRA tree has additional critical findings.
- Common CI is green, but performance repeatedly fails and security jobs contain non-blocking suppression.
- Live canary needed manual repair for Nginx generation, health binaries, ACME ownership, malformed env, first deploy, and DNS drift.
- Public UI includes no-op controls, demo data, incomplete errors, inconsistent branding, and an `/api/items` 501 placeholder.

## Decisions

### R-001: Port, do not wholesale-merge, the long-running visual work

Inventory its net 17-file delta and 231-commit history, map tokens/components/routes, and selectively implement reviewed behavior on Feature 093. Exclude its deployment bootstrap mutation and any mocked/no-op interactions. This prevents a large experimental history from becoming the production unit of review.

### R-002: Monorepo plus declarative modules

Add site/module manifests around Django/FastAPI/React. A registry coordinates capabilities while Django remains the model authority.

### R-003: Evidence-manifest complete gate

A machine-readable manifest declares check ID, command, applicability, timeout, policy, artifacts, and dependencies. Status is `passed|failed|skipped|unavailable|not_run`.

### R-004: Honest ratcheted coverage

Establish whole-surface baselines, require changed-line coverage, ratchet floors, and exhaustively branch-test security/isolation paths. Do not fabricate an instant global 100% number.

### R-005: Previews are exact leases

Each preview has provider IDs, ownership tags, DNS state, TTL, cost estimate, evidence digest, and teardown receipt. Names/IPs alone are never deletion identity.

### R-006: Destroy idle compute by default

Persist only declared durable state, then destroy owned preview compute/DNS. Recreate from immutable artifacts. Provider-specific suspension is an explicit exception.

### R-007: Strict JSON Schema contracts

Version site/module documents with `additionalProperties: false` plus semantic cross-field validation. This works across Python, Node, CI, editors, and generated repos.

### R-008: Django → FastAPI → React per pack

Decompose persistent work in that order, then contract/E2E validation, preventing frontend-only mocks and model drift.

### R-009: Provider/payment authority remains separate

Installing a pack never activates credentials, network, public DNS, email, payments, publication, or billable infrastructure.

### R-010: Deterministic visual evidence

Self-host test assets; freeze clock, locale, timezone, data, viewport, theme, motion, and network; require reviewed baseline changes.

### R-011: Typed optionality, no broad suppression

Required modules fail startup. Optional modules expose explicit disabled/degraded health and reason.

### R-012: Immutable child generation

Use an exact commit archive plus declarative transformations; never copy the live worktree or execute input content during generation.

### R-013: Replace Create React App with bounded Vite 6/Vitest 4 compatibility

Vite 6.4 is the newest line jointly supported by Node 24, Vitest 4, and the retained Storybook 8 framework. The migration preserves the existing `build/` artifact, `REACT_APP_*` public build inputs, all 46 frontend suites, Istanbul report paths, Docker/Nginx serving contract, and Storybook while removing `react-scripts`, its Webpack builder/preset, and its patch-package workaround. Client configuration is accessed through `import.meta.env`; prefixed values remain public by design and must never contain secrets. Full npm audit moved from 34 findings including 15 high to five moderate and zero high/critical. React Router 7 and Storybook major upgrades remain separately compatibility-tested moderate remediation work under the T020 SLA.

## Alternatives rejected

- Promoting the stale design branch.
- Unchecked all-purpose settings files.
- Copying a running worktree to generate sites.
- Name-based provider cleanup.
- Soft-failing required security tools.
- Hardwiring every pack into core routes/navigation.
- Keeping placeholder controls indefinitely.

## Decisions deferred behind adapters

- Object storage, mail, payment, and analytics providers use local fakes and disabled defaults.
- Permanent production hosting and public production DNS need separate approval.
