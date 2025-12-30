# Secrets Management Runbook

Scope: Handling, storing, and auditing secrets across environments.

Principles:

- Prefer environment variables injected at runtime; never commit secrets.
- Use per-environment values (local, staging, production) with least privilege.
- Redact secrets in logs and artifacts; verify via tests.

Storage:

- CI: GitHub Actions encrypted repository/environment secrets.
- Droplet: `.env` managed via deploy scripts; permissions restricted.
- Local: `.env.local` only; ignored by git.

Rotation:

- Follow `key_rotation.md` for rotation cadence and safe rollout.

Audit:

- CI includes `gitleaks` and SBOM scans; add Semgrep SAST.
- Regularly run `deploy.ps1 -UpdateOnly -AllTests` and review `meta/post-deploy-report.json`.

Allow/Deny Policies:

- Dependencies must use acceptable licenses (MIT, Apache-2.0, BSD-3-Clause, ISC). Non-compliant licenses trigger CI failure.
- Container images must be pinned; floating `latest` tags are disallowed.

Incident Response:

- If a secret leaks, immediately rotate, invalidate sessions, and review logs.
- Document the incident and remediation steps in `docs/RELEASE.md`.
