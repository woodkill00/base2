# Deployment Guide

Authoritative deploy/update/test is executed via `digital_ocean/scripts/powershell/deploy.ps1`.

## Workflow Overview

- Commit code changes and ensure tests are green locally.
- Push to `origin/<branch>`.
- Set `.env` `DO_APP_BRANCH` to the branch you want the droplet to hard-reset to (usually `main`).
- Run UpdateOnly deploy with tests: `-UpdateOnly -AllTests -Timestamped`.
- Review artifacts under `local_run_logs/<ip>-<timestamp>/`.

## Modes

- Full deploy: `powershell -File digital_ocean/scripts/powershell/deploy.ps1 -Full -AllTests -Timestamped`
- Update-only: `powershell -File digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests -Timestamped`

Alias/Flag note: Recent runs used `-RunAllTests` which is equivalent to `-AllTests`.

## Flags Reference

- `-Full`: deploy an existing target or provision one missing target. A new target stops at the authenticated host-key enrollment boundary; rerun after owner verification to perform DNS, source, secret, migration, and stack mutation.
- `-UpdateOnly`: skip provisioning, hard-reset remote repo to `origin/$env:DO_APP_BRANCH`, rebuild core services.
- `-Preflight`: run preflight validators locally; deploy fails fast if validation fails.
- `-AllTests`: run all remote and local post-deploy tests (React Jest, Playwright E2E, API/Django pytest, lint, type, and smoke checks). Missing tools, skipped required results, and nonzero commands fail the deployment and enter rollback.
- `-RunTests`: run a subset of tests (omit E2E by default); use with `-TestsJson` for machine-readable output.
- `-TestsJson`: JSON output for test results; artifacts saved under `local_run_logs/.../meta`.
- `-Timestamped`: write artifacts to `local_run_logs/<ip>-<timestamp>/` instead of a generic folder.
- `-AsyncVerify`: disabled for authoritative deployment because unfinished remote mutation cannot produce terminal success.
- `-SshKey <path>`: specify SSH private key path.
- `-SkipAllowlist`: do not update IP allowlists in `.env` before deploy.
- `-VerifyTimeoutSec <sec>`: override remote verification timeout (default 1800).
- `-ReactTestTimeoutSec <sec>`: override local React test timeout (default 1800).

New-target provisioning additionally requires an exact-owner conditional lease.
`DO_PROVISION_LEASE_GIT_REMOTE` names an already configured dedicated private
lease-repository remote used for an atomic Git compare-and-swap provisioning
lease. It must not resolve to the source `origin`, and its credential must be
limited to that otherwise empty coordination repository. Credential-bearing,
plain-HTTP, SSH, SCP, command-helper, and local-only production remotes are
rejected. The controller ignores inherited global/system Git configuration and
transport overrides; private HTTPS authentication must come from the bounded
process credential broker without placing credentials in the URL. The fixed,
digest-named remote ref is created only when a new paid resource is needed and
is deleted only with the exact owner revision. Conflict, crash, expiry, or ref
drift fails closed; recovery requires exact-owner cleanup. Update-only operation
does not contact the lease remote. A conflicting, crashed, or uncertain provider
request leaves the lease in place and is never treated as permission to create
another paid resource.

### When to use which

- Use `-UpdateOnly` for routine code changes already on the droplet; faster and safer.
- Use `-Full` to create one missing droplet or deploy the detected existing target. New creation always stops before SSH until its host key is separately verified and enrolled.
- Use `-UpdateOnly -CreateIfMissing` only when an update should provision a missing target and stop at that same enrollment boundary. `-CreateIfMissing` alone and `-Full -UpdateOnly` are rejected.
- Always include `-AllTests` for CI-like gating unless experimenting locally.
- Use `-Timestamped` to keep runs isolated and auditable.

Provider discovery is paginated and typed. Only an authoritative `missing`
result can enter provisioning; API errors, duplicate names, and an existing
droplet still awaiting a public address fail closed. A dedicated private Git
coordination repository serializes the final lookup and create operation with
an atomic ref create and exact-revision compare-and-swap deletion. Conflict,
stale ownership, transport uncertainty, or an uncertain provider result keeps
the lease in place for explicit exact-owner recovery. Existing deployments
remain bound to the exact provider droplet ID returned by discovery.

Fresh cloud-init contains no repository or credential. It installs only
distribution-signed bootstrap packages. Terminal local evidence retains the
user-data SHA-256, authoritative provider identity, and sanitized resolved
package/version inventory, all bound by the exact-source manifest. After the
owner authenticates and pins the new SSH host key,
the deploy runner may clone a credential-free public HTTPS repository URL.
URLs with userinfo, query tokens, fragments, SSH transports, or plaintext HTTP
are rejected; private repository bootstrap requires a separate scoped JIT
credential workflow.

Runtime and owner-scoped
API migrations use one exact-commit image. Production migration connections
must use an effective external database target with `verify-full` TLS and an
absolute CA path; `DATABASE_URL` cannot override that boundary with a local,
socket, loopback, malformed, or non-PostgreSQL target.

Terminal success requires a complete hash-verified local evidence manifest and
a recursive secret scan before remote staging evidence is removed. Failure to
copy, validate, or scan that evidence is a deployment failure, not a warning.

## Pre-Deploy Discipline (UpdateOnly)

- Commit and push runtime-impacting changes to `origin/<DO_APP_BRANCH>` before using `-UpdateOnly`.
- Ensure `.env` defines `DO_APP_BRANCH` for the droplet. The deploy script hard-resets the droplet repo to `origin/<DO_APP_BRANCH>`.
- Runtime-impacting changes include service code (`api/`, `django/`, `react-app/`), Dockerfiles, Compose files, and Traefik configs. Docs-only changes do not require a push.

Recommended: set `DO_APP_BRANCH=main` in `.env` for stable deployments.

## TLS Policy (Staging-Only)

- Traefik must use the Let’s Encrypt staging ACME directory (`le-staging`).
- Verification (`test.ps1`) uses the repository-pinned staging trust bundle,
  validates hostname and chain, and fails on every TLS or curl transport error.

### TLS Mode Guard (Hardening)

- Deploy verification also enforces:
  - ACME email is set (`TRAEFIK_CERT_EMAIL`)
  - ACME storage files are not world-readable
  - If the production Let's Encrypt directory is referenced, `ENV=prod` must be explicitly set

Flag interaction:

- In staging/non-prod, the stack uses Let's Encrypt staging (`le-staging`); tests expect browser warnings on TLS.
- In prod (`ENV=production`), use real ACME directory and ensure DNS/allowlists are correct; tests will enforce stricter checks.

## Artifacts

- Runs write artifacts to `local_run_logs/<droplet-ip>-<timestamp>/`.
- Post-deploy report: `meta/post-deploy-report.json`.

### Suggested Verification Flow (UpdateOnly)

- Run: `powershell -File digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -RunAllTests -Timestamped`
- Verify endpoints:
  - Traefik dashboard: https://traefik.${WEBSITE_DOMAIN}/ (basic-auth + allowlist)
  - Django admin: https://admin.${WEBSITE_DOMAIN}/admin/ (basic-auth + allowlist)
  - FastAPI Swagger UI: https://swagger.${WEBSITE_DOMAIN}/docs
- Review artifacts under `local_run_logs/<droplet-ip>-<timestamp>/` for jest, Playwright, and API/Django pytest outputs.

Artifacts map:

- `meta/post-deploy-report.json`: consolidated outcome and timings.
- `docker/*`: compose ps/config/ports.
- `traefik/*`: static/dynamic configs and logs.
- `api/*`, `django/*`: service-specific logs and health outputs.
- `react-app/*`: jest/e2e outputs.

## Troubleshooting

- If UpdateOnly changes don’t reflect on the droplet, verify a recent push to `origin/<DO_APP_BRANCH>`.
- For DNS allowlists, the script updates `.env` with your public IP; restart Traefik if needed.

Test warnings:

- React Router v7 "Future Flag Warning" messages are suppressed in Jest only; see `docs/TESTING.md` for policy and the `TestRouter` helper.

## Cache guidance (SPA)

CRA builds produce hashed asset filenames, so `static/js/*.js` and `static/css/*.css` can be cached long-term.

The main risk is `index.html` being cached too aggressively, which can create a mismatch where some clients (often mobile) fetch a new `index.html` referencing new assets while others keep an older HTML (or vice-versa).

Recommended posture:

- Cache `index.html` with `no-store` (or very short TTL), and cache hashed assets as `immutable`.
- After deploying breaking frontend changes, if you see “desktop works, mobile broken”, force-refresh on mobile and consider purging any proxy/CDN cache for `index.html`.

## Migration Safety (CI)

CI enforces Django migration safety by failing if model changes are detected without migrations.
Run locally before PRs:

```
cd django
python manage.py makemigrations --check --dry-run
```

## Hostnames (Dev-Production)

- Main site: `https://${WEBSITE_DOMAIN}/`
- API: `https://${WEBSITE_DOMAIN}/api/*`
- Django admin: `https://admin.${WEBSITE_DOMAIN}/admin/` (guarded by Traefik basic-auth + IP allowlist)
- FastAPI Swagger UI: `https://swagger.${WEBSITE_DOMAIN}/docs` (docs-only host; routed to FastAPI)

## Container Runtime Hardening

`development.docker.yml` applies defense-in-depth settings where feasible:

- `cap_drop: [ALL]`
- `security_opt: [no-new-privileges:true]`
- `read_only: true` for stateless services, with `tmpfs` mounts for writable paths like `/tmp`
