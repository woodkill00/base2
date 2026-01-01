# Key Rotation Runbook

Purpose: Safely rotate sensitive keys and secrets (JWT signing keys, TOKEN_PEPPER, OAuth client secrets, SMTP credentials) with minimal downtime and clear validation.

Prerequisites:

- Staging-like environment is green (`deploy.ps1 -UpdateOnly -AllTests`)
- Backups exist for relevant stores (Postgres, Redis)
- Access to CI secrets and droplet env management

Rotation Steps:

1. Plan: Identify keys to rotate and affected services (`api`, `django`, Traefik if TLS email changes).
2. Prepare: Generate new secrets securely (offline generator). Store in a secret manager or CI repository secrets.
3. Dual-Config Window (if applicable):
   - Add new secrets alongside old ones (e.g., accept old refresh tokens while issuing new sessions).
   - Set env vars in droplet and CI but do not deploy yet.
4. Deploy UpdateOnly:
   - Run `digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests -Timestamped`.
   - Confirm `post-deploy-report.json` success.
5. Cutover:
   - Flip services to require new keys (e.g., invalidate token families issued with old pepper).
   - Clear caches if necessary (Redis namespaces).
6. Validate:
   - Run smoke: `/api/health`, `/api/openapi.json`, login/logout, protected routes.
   - Review artifacts (`local_run_logs/<run>/meta/*`).
7. Cleanup:
   - Remove old keys from env after grace period.
   - Update documentation and audit logs.

Rollback:

- If failures occur, restore previous env values and redeploy UpdateOnly.
- Document incident and findings in `docs/RELEASE.md`.
