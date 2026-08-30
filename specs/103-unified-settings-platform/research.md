# Research: Unified Account and Settings Platform

## Product patterns

- Google centralizes personal information, security recommendations, devices, linked access, privacy controls, and export/deletion.
- Meta centralizes connected-account identity, contact information, security, privacy, payments, and ownership controls.
- Amazon groups identity, payment, devices, communications, personalization, and history.
- GitHub separates appearance, accessibility, security, developer, and organization settings.
- Apple and Android recommend manageable groups, precise language, good defaults, contextual placement, and adaptive list-detail navigation.

## Decisions

1. Use a central overview plus category routes, not one long form.
2. Keep security within the shell but isolate sensitive actions visually and technically.
3. Use manifest-driven optional packs with a strict server capability response.
4. Store typed fields rather than arbitrary client JSON.
5. Use explicit save for forms and optimistic instant save only for reversible controls.
6. Require version-based conflict handling.
7. Treat authenticated settings screens as first-class visual baselines.
8. Retain existing privacy, session, TOTP, recovery, organization, and audit foundations.
9. Reject unsafe avatar URLs and never fetch them on the backend.
10. Keep passkeys disabled until a full WebAuthn ceremony exists.

## Standards

- WCAG 2.2 AA for navigation, focus, input assistance, accessible authentication, target size, status messages, and reflow.
- NIST SP 800-63B principles for authenticators, reauthentication, and session management.
- Base2 constitution for Django-first models, FastAPI mirrors, React-last implementation, container parity, staging certificates, and single-entrypoint operations.
