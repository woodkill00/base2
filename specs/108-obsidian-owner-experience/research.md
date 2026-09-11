# Evidence and decisions

Inspected constitution, main 6d17e3f, PublicRoutes.jsx and Feature 107 assurance plan.

Confirmed prior live investigation:

- Signup POST /api/auth/register returned 422. Policy is minimum eight characters,
  upper/lowercase and digit. UI lacks guidance; apiErrors.js can mistake Axios
  errors for normalized errors and discard response validation.
- Appearance save returned 500; sanitized exception identifies RLS rejection on
  api_user_preferences. Investigate transaction identity, not bypass grants.
- Existing live browser run passed five scenarios but failed preference saving.
  HTTP route success is not proof of complete user functionality.
- Login/signup have conflicting light inline styling. Reuse homepage tokens.
- Current preview accounts are run-specific and disappear with an empty DB.

Observed route families: home, about/privacy/terms/accessibility, contact/search/
journal, events, portfolio/blog/docs collections/details, login/signup/verify-email/
forgot-password/reset-password, dashboard/workspace/media/operations, account
redirect/admin/invitation, settings and localized/error routes. Expand nested
settings/localized branches in implementation inventory; this list is not a claim
of complete runtime coverage.

Decisions: shared tokens over duplicate CSS; existing email authentication over
unrequested username auth; private environment-scoped provisioning over default
seed accounts; synthetic identities for mutations; real limited-role PostgreSQL
tests for RLS; reviewed snapshots over automatically accepting current defects.
