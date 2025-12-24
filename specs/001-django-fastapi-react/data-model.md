# Data Model (Phase 1): Full-stack Baseline

This feature reuses and extends existing Django models. Django remains the canonical source of truth.

## Entities

### 1) User (canonical auth identity)

**Canonical store**: Django auth user model (`django.contrib.auth.get_user_model()`).

**Key fields (typical Django fields)**:
- `id` (integer primary key)
- `username` (string; may be optional depending on configuration)
- `email` (string)
- `password` (hashed; never stored or logged in plaintext)
- `is_active`, `is_staff`, `is_superuser`
- `date_joined`, `last_login`

**Validation rules**:
- Password is stored using a slow hash.
- Authentication errors MUST not reveal whether the account exists.

**State transitions**:
- `is_active`: `true -> false` (account disabled)

---

### 2) UserProfile (account metadata)

**Canonical model**: `django/users/models.py::UserProfile`

**Fields**:
- `uuid` (UUID)
- `created`, `updated`
- `user` (1:1 to User)
- `display_name` (string, optional)
- `avatar_url` (URL string, optional)
- `bio` (text, optional)

**Validation rules**:
- Only “allowed profile fields” are user-editable.

---

### 3) EmailAddress (supporting identity)

**Canonical model**: `django/users/models.py::EmailAddress`

**Fields**:
- `email` (from `common.models.Email` mixin)
- `created`, `updated`
- `user` (N:1 to User)
- `is_primary` (bool)
- `is_verified` (bool)
- `verification_token` (string)
- `verified_at` (datetime)

**Validation rules**:
- A user SHOULD have at most one `is_primary=true` email.
- `verification_token` MUST be treated as a secret (not logged).

**State transitions**:
- `is_verified`: `false -> true`

---

### 4) OAuthAccount (third-party sign-in linkage)

**Canonical model**: `django/users/models.py::OAuthAccount`

**Fields**:
- `uuid`, `created`, `updated`
- `user` (N:1 to User)
- `provider` (string, e.g. `google`)
- `provider_user_id` (string)
- `access_token`, `refresh_token` (text; treat as secrets)
- `expires_at` (datetime)

**Constraints**:
- Unique constraint: `(provider, provider_user_id)`.

**State transitions**:
- Link: create OAuthAccount
- Unlink: delete/disable OAuthAccount (policy decision; must be audited)

---

### 5) AuditEvent (security-relevant event log)

**Canonical model**: `django/users/models.py::AuditEvent`

**Fields**:
- `created`, `updated`
- `actor_user` (nullable N:1 to User)
- `action` (string)
- `target_type`, `target_id` (strings)
- `ip` (IP address)
- `user_agent` (text)
- `metadata` (JSON)

**Validation rules**:
- MUST avoid logging secrets in `metadata`.

**Typical actions**:
- `auth.signup`
- `auth.login.success`
- `auth.login.failure`
- `auth.logout`
- `oauth.google.linked`
- `profile.updated`

---

### 6) Session (authenticated session state)

**Canonical approach**: cookie-based auth with server-side or signed-token-backed session semantics.

**Implementation mapping**:
- If using Django sessions: `django_session` table becomes canonical for session storage.
- If using signed session cookies: session state is contained in the HttpOnly cookie, with CSRF token state stored separately.

**Validation rules**:
- Cookies MUST be `HttpOnly` (credential cookie), `Secure` in staging/prod-like, and `SameSite` appropriately set.
- State-changing requests MUST require CSRF protections.
