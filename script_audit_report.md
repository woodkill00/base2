# Script Audit Report

Date: 2025-12-23

This report covers the scripts in:
- `digital_ocean/scripts/**` (canonical deployment automation)
- `scripts/**` (local Docker/dev helpers)

Legend:
- **KEEP**: actively useful / canonical
- **DEPRECATE**: keep only if you still use it; otherwise safe to remove later (this repo has removed all items previously marked DEPRECATE)
- **DELETE**: safe to remove now (no remaining known use)

---

## Canonical DigitalOcean automation (KEEP)

These are the scripts we should treat as the source of truth for DigitalOcean deploy/verify behavior.

### PowerShell (canonical)
- **KEEP** `digital_ocean/scripts/powershell/deploy.ps1`
  - Canonical Windows deployment entrypoint (provision/update + remote verification + timestamped local artifacts + post-deploy tests).
- **KEEP** `digital_ocean/scripts/powershell/test.ps1`
  - Canonical post-deploy test runner; used by deploy and supports artifacts.
- **KEEP** `digital_ocean/scripts/powershell/smoke-tests.ps1`
  - Canonical smoke tests for the deployed site/API.
- **KEEP** `digital_ocean/scripts/powershell/validate-predeploy.ps1`
  - Validates required env and basic predeploy invariants (PowerShell 5.1 compatible).
- **KEEP** `digital_ocean/scripts/powershell/update-pgadmin-allowlist.ps1`
  - Updates pgAdmin allowlist in `.env` (PowerShell 5.1 compatible).

### Python (canonical)
- **KEEP** `digital_ocean/scripts/python/orchestrate_deploy.py`
  - Canonical DO deploy orchestrator used by PowerShell deploy.
- **KEEP** `digital_ocean/scripts/python/validate_dns.py`
  - Canonical DNS validation utility used in deploy workflow.

### Shell scripts used by the droplet / orchestration
- **KEEP** `digital_ocean/scripts/digital_ocean_base.sh`
  - Droplet user-data/bootstrap script (referenced by orchestrator).
- **KEEP** `digital_ocean/scripts/post_reboot_complete.sh`
  - Helper executed on droplet reboot completion (referenced by orchestration flow).

---

## DigitalOcean shell wrappers (mostly optional)

These exist to make DO utilities runnable on Linux/macOS, but they are not the Windows canonical path.

- **KEEP** `digital_ocean/scripts/teardown.sh`
  - Wrapper to run `digital_ocean/teardown.py` (currently the easiest non-Windows teardown entrypoint).

---

## Local Docker/dev helper scripts (KEEP)

These are not duplicates of DO automation; they’re local environment helpers for `local.docker.yml`.

- **KEEP** `scripts/start.sh`
  - Starts the local stack (optionally `--build`), validates `.env`, can follow logs briefly.
- **KEEP** `scripts/stop.sh`
  - Stops the stack; optional `--volumes` (data-destructive).
- **KEEP** `scripts/rebuild.sh`
  - Rebuilds images; optional `--no-cache` and optional single-service argument.
- **KEEP** `scripts/restart.sh`
  - Restarts the whole stack or one service.
- **KEEP** `scripts/logs.sh`
  - Views logs with `--follow` and `--tail`.
- **KEEP** `scripts/status.sh`
  - High-level status + per-container health state + resource usage.
- **KEEP** `scripts/health.sh`
  - Healthcheck-oriented view with last logs for unhealthy containers.
- **KEEP** `scripts/debug.sh`
  - Dumps container details for a given service (or overall).
- **KEEP** `scripts/shell.sh`
  - Opens a shell into a container.
- **KEEP** `scripts/kill.sh`
  - “Nuclear” cleanup (dangerous) removing all project containers/volumes/images/networks.
- **KEEP** `scripts/sync-env.sh`
  - Synchronizes a few literal config values (notably Compose network name) with `.env`.
- **KEEP** `scripts/test.sh`
  - Runs frontend tests (backend tests intentionally removed for the FastAPI/Django stack).

---

## One-off helpers (keep, but some are OS-specific)

- **KEEP** `scripts/generate-traefik-auth.ps1`
  - PowerShell-friendly Traefik basic-auth line generator; uses Docker `httpd` htpasswd by default and outputs `.env`-safe escaping.

- **KEEP** `scripts/update-django-admin-allowlist.ps1`
  - Updates `DJANGO_ADMIN_ALLOWLIST` in `.env` based on detected public IPv4.
- **KEEP** `scripts/update-flower-allowlist.ps1`
  - Updates `FLOWER_ALLOWLIST` in `.env` based on detected public IPv4.

## Legacy / workflow leftovers

---

Legacy helpers and shell wrappers previously marked **DEPRECATE** were deleted per request.

---

## Duplicates deleted already

- The old `scripts/*.ps1` DO entrypoints were duplicates of `digital_ocean/scripts/powershell/*` and were removed.
- Legacy Python entrypoints that contained duplicated “full implementations” below trampolines were cleaned to trampoline-only to avoid drift.
