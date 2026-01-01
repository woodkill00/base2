# Access Reviews Runbook

Purpose: Establish an audit-friendly process to review admin access and roles.

Roles & Permissions:

- Django Admin: superuser-only, gated via Traefik (basic-auth/IP allowlist).
- pgAdmin & Flower: routed only if needed; gated via Traefik and credentials.
- FastAPI Admin Surfaces: none exposed publicly; use internal-only endpoints.

Checklist (execute quarterly):

- Verify Traefik gates for admin.websitedomain, pgadmin.<domain>, flower.<domain>.
- Review superuser roster and last-login; remove stale accounts.
- Confirm audit events exist for auth-sensitive actions (login, reset, verify, role changes).
- Validate secrets rotation notes are current (see key_rotation.md).

Artifacts:

- Save screenshots of gate prompts and access denials.
- Export audit logs for the review window.
