# Implementation Plan: Base2 Full-Stack Obsidian Preview

## Summary

Add a canonical Base2 profile, a separately selected full-preview edge mode, strict owner admission, exact multi-record DNS/lease ownership, safe early teardown, outside-in authenticated probes, and local/live visual parity. Reuse Feature 093 primitives where their contracts are sound; repair the observed premature DNS cleanup and incomplete canary assumptions rather than layering ad-hoc live commands over them.

## Constitution Check

- **Test first**: contract and hostile fixtures precede implementation; visual references require explicit review.
- **Environment parity**: full preview uses the normal 12-service Compose topology; only staging TLS, TTL, indexing denial, and guarded operator exposure differ.
- **Compose first**: no application service receives a public port; Traefik remains the only edge.
- **Single entrypoint**: extend supported Bash/PowerShell orchestrator surfaces rather than retaining operator-notebook scripts.
- **Shell parity**: Python owns portable state/policy; paired thin Bash/PowerShell entrypoints invoke it.
- **Observability**: every stage emits a typed redacted result; no suppressed failure satisfies readiness.
- **Security**: staging ACME only, exact host CIDRs, edge plus application authentication, private SecretRefs, no wildcard deletion.

## Technical Context

- React 18/Vite 6 frontend with manifest-driven profiles and Playwright visual tests.
- FastAPI API with production docs policy and existing `/api/*` routes.
- Django admin, PostgreSQL, Redis, Celery, Flower, pgAdmin, and Traefik Compose services.
- Python provider/orchestration libraries with DigitalOcean fake-provider tests.
- DigitalOcean preview size target `s-2vcpu-2gb`; default TTL 60 minutes, maximum 4 hours.

## Architecture

1. `site_profiles/base2-obsidian.json` becomes the canonical Base2 reference profile. The profile generator emits integrity-identical service copies and a generated frontend registry that does not require hand-maintained imports.
2. Theme bootstrap applies profile identity before first paint while the light/dark accessibility preference remains an orthogonal mode.
3. Traefik supports exactly three policy states: local/full development, minimal live canary, and guarded full live preview. Unknown or contradictory state exits before Traefik starts.
4. A full-preview policy renderer validates exact host CIDRs and private runtime credentials, then renders the existing complete dynamic router with stronger protection for every operator surface.
5. `/api` provides a non-sensitive service document. Swagger remains disabled unless the explicit full-preview policy enables it.
6. A versioned preview lease binds source, profile, Droplet identity, and every DNS record identity. Teardown is one state machine: requested → compute deleting/absent → DNS deleting/absent → verified zero resources. An unexpired no-authority request is a non-success refusal and cannot trigger DNS cleanup.
7. Outside-in verification probes public and protected paths, captures a live screenshot, checks console/network failures, and emits only digests and safe statuses.

## Security Boundaries

- Public: root frontend, selected public pages, `/api`, `/api/health`, and required public API calls.
- Protected operator edge: Django admin, Swagger, Traefik, pgAdmin, Flower. Each requires exact owner CIDR and edge authentication; Django/pgAdmin retain application login.
- Internal: Docker socket, databases, queues, service ports, health internals, credentials, runtime environment, and provider resolver.
- Certificate boundary: `le-staging` is immutable in this feature.
- DNS boundary: exact record IDs and values only; legacy records are evidence until explicitly adopted or removed.

## Delivery Phases

1. Contracts and failing tests.
2. Canonical profile and live visual contract.
3. API and edge policy.
4. Owner admission and private environment rendering.
5. DNS transaction and lease v2 state machine.
6. Full-preview orchestrator and evidence.
7. Complete local gates, hostile simulations, review, merge.
8. Separately approved bounded live launch and visual owner review.

## Gate Strategy

- Focused Python unit/contract tests.
- React unit, accessibility, interaction, and three-viewport visual tests.
- Generated profile freshness and multi-profile build checks.
- Rendered Compose/Traefik route and public-port checks.
- Providerless create/teardown/replay/partial-failure matrix.
- Secret scanning over source, staged diff, generated output, and evidence fixtures.
- Full repository complete gate with no required skipped/unavailable/not-run checks.
- Live outside-in verification remains separate because it mutates provider state.

## Rollback

Code rollback is a normal non-force revert. Preview rollback uses the exact lease state machine and cannot broaden identity. If compute is gone but DNS cleanup fails, state remains `dns_cleanup_pending`, alerts remain active, and reconciliation retries only the bound record IDs. No database from a disposable preview is restored into another environment.
