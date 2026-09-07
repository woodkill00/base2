# Current Base2 State

Last reviewed: 2026-09-08

Base2 uses Django as the domain source of truth, FastAPI as the versioned API,
React as the untrusted browser client, PostgreSQL for durable relational state,
Redis/Celery for queued work, Traefik/Nginx at the edge, and isolated supporting
services. The deprecated Node application backend is not part of the production
architecture.

The repository includes a deterministic website factory, closed module
manifests, generated site profiles, the Obsidian design system, identity and
settings foundations, content/data and media workspaces, staging-certificate
preview orchestration, bounded provider lifecycle controls, visual assurance,
recovery checks, supply-chain policy, and a manifest-driven complete gate.

Feature 106 is the active production-readiness program. Its reviewed inventory,
classification of existing capabilities versus remaining production work,
environment boundaries, release contract, trust model, resource defaults, and
evidence rules are documented in `docs/PRODUCTION_READINESS_PROGRAM.md` and
enforced by `shared/config/production-readiness-v1.json`.

Production deployment, DNS mutation, production certificate issuance,
credential use, spending, destructive migration, and provider teardown remain
separately approved operations. No checked-in profile grants those actions.
