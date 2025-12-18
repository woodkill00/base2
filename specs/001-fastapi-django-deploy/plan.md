# Implementation Plan: FastAPI + Django Automated Deployment

**Branch**: `001-fastapi-django-deploy` | **Date**: 2025-12-18 | **Spec**: [specs/001-fastapi-django-deploy/spec.md](specs/001-fastapi-django-deploy/spec.md)
**Input**: Feature specification from `/specs/001-fastapi-django-deploy/spec.md`

## Summary

Automate a one-command deploy/upgrade that integrates the FastAPI API and Django service behind the existing Traefik edge, runs remote verification when possible, and writes a timestamped artifact set under the local logs directory. The deployment must fail fast on missing/invalid credentials, keep Django admin non-public by default (allow optional exposure only in non-production with protections), and always use staging certificates for this development-production simulation.

## Technical Context

- **Languages**: PowerShell (deploy orchestration), Python (DigitalOcean orchestration), YAML (Docker Compose, Traefik), TS/JS (existing), plus future Python for FastAPI/Django services
- **Primary Dependencies**: Docker Engine + Compose, Traefik, DigitalOcean (pydo), FastAPI, Django, PostgreSQL
- **Storage**: PostgreSQL (existing `postgres` service)
- **Testing**: Deployment smoke tests via remote verification (HTTP headers, health endpoints, proxy config snapshots)
- **Target Platform**: Linux Droplet on DigitalOcean; Traefik as sole public entrypoint on 80/443
- **Project Type**: Web application (frontend + API + services)
- **Performance Goals**: API and homepage reachable within 5 seconds post-deploy; update-only reduces runtime ≥30%
- **Constraints**: Staging certificates only; fail-fast on missing DO credentials; admin non-public by default
- **Scale/Scope**: Single droplet; single domain; internal-only Django by default

## Constitution Check

- User-value focus: The plan maintains a single-command deploy with verifiable outcomes.
- Security-first defaults: No public admin by default; TLS enforced at edge; staging-only certs respected.
- Observability: Timestamped artifact capture for every run, even on partial success.
Status: Pass

## Project Structure

### Documentation (this feature)

```text
specs/001-fastapi-django-deploy/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
└── contracts/
```

### Source Code (repository root)

```text
# Existing
react-app/
backend/
digital_ocean/
scripts/
traefik/
postgres/

# To add for this feature (scaffold only)
api/        # FastAPI service (containerized)
django/     # Django service (containerized, internal-only by default)
```

**Structure Decision**: Keep current web-app layout, add `api/` (FastAPI) and `django/` services per spec. Traefik remains the only public entrypoint.

## Phased Plan

1) Deployment pipeline hardening (P1)
- Update `scripts/deploy.ps1` behavior is already aligned: venv bootstrap, `.env` load, allowlist update, orchestrator run, IP discovery, remote verification, timestamped artifacts.
- Enforce fail-fast on missing/invalid DO credentials before cloud actions (already implied by spec). Ensure clear error surface.
- Ensure artifact set includes: compose ps, Traefik env/static/dynamic, template snapshots, proxy logs, `curl` headers for `/` and `/api/`.

2) FastAPI + Django integration surface (P1)
- Compose: replace `backend` with `api` (FastAPI) service; add `django` service; join internal network; no host port exposure.
- Traefik: route `Host(WEBSITE_DOMAIN) && PathPrefix(/api)` → `api`; attach security headers and ratelimit; maintain staging resolver.
- API: ensure `/api/health` exists and is reachable via edge.
- Django: internal-only by default. Optional admin exposure only in non-production under protections (IP allowlist and/or auth) if later needed.

3) Verification and logs (P1)
- Confirm remote verify captures: running containers, Traefik configs, environment (sanitized), and tails logs.
- Ensure timestamped folder option is documented and used in CI/manual runs.

4) Update-only mode efficiency (P2)
- Use update-only flag to skip unnecessary rebuilds where safe; measure runtime vs full deploy.
- Document expected behavior and limitations.

5) Documentation (P1)
- Add quickstart guidance for operators: prerequisites, command variants, expected outputs, troubleshooting.
- Note certificate policy (staging-only) and admin exposure policy.

## Acceptance & Validation

- Homepage reachable via HTTPS on configured domain after deploy.
- `/api/health` returns OK via edge.
- Artifact folder created on every run; contains all required files.
- Update-only is measurably faster (≥30%) vs full deploy on same environment.

## Risks & Mitigations

- DNS misconfiguration → Highlight in verification output and quickstart.
- SSH key/port restrictions → Skip remote verify but retain local logs with explicit warning.
- Compose drift on droplet → Force rebuild/refresh of Traefik in verify step (already covered).

## Rollout

- Branch: `001-fastapi-django-deploy`
- Merge strategy: PR with deployment logs attached from a timestamped run.
- Post-merge: Tag repo and capture final artifact set for reference.
