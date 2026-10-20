# Repair plan

Base source: 5c1ba450149c8221397bb03088254162a138577d, native WSL.
Budget: one focused diagnostic/repair batch, targeted tests and visual review before
one complete gate; no paid resources during implementation.

Recognize only the exact recent_reauthentication_required detail on 401/403 in
the shared interceptor, after epoch validation. Notify the auth context without
invalidating credentials, refreshing, or replaying. Render an accessible shared
notice inside each AppShell main region using existing Volcano tokens and
sanitized return paths. A separate boolean-only context preserves standalone
layout usage without an authentication provider. Focus/scroll the notice into
view on a freshness request; keep the skip link first in the shell.
Clear it on explicit successful authentication or invalidation, not failed/MFA
pending login. Server authorization and refresh-token semantics remain unchanged.

Scope Google color-scheme to its own provider container, keeping filled_black.
Add an iframe-aware browser assertion; a plain button mock is insufficient.

Consumers: settings privacy export, identity/account, media and operations.
Trust boundaries: stale responses, credential freshness, cross-origin Google frame,
safe internal navigation; no new stored secrets or provider interaction.
