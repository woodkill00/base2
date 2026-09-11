# Implementation checkpoint

Implemented: signup Axios validation/network/internal-error regressions, password
policy help and accessible field descriptions; transaction-scoped tenant binding
for preference/notification reads and writes; shared Obsidian shell/card/input/
button tokens and light preference compatibility; optional private owner bootstrap
in the full preview deployment with preservation/conflict/environment tests.

Owner bootstrap uses the existing canonical API auth schema and hashing code.
It creates no admin grants, MFA bypass or verified-email flag. Existing credentials
are never reset. Provisioning serializes on profile to prevent concurrent name or
email collisions. The private JSON input is passed on stdin and removed remotely.

Validation so far: 32 focused backend/deployment checks passed. Initial complete
frontend run: 290 passed, one normalized-error compatibility regression found and
repaired. New browser matrix covers 17 public/auth routes at mobile and desktop,
plus signup field validation; screenshots captured privately. Existing authenticated
and vendor acceptance must still run on the final exact-source deployment.

Not complete: full route/state inventory, complete authenticated visual matrix,
baseline owner approval, local restricted-role migration alignment, final release
gate, real owner credential identification, live owner/restart/recreation checks,
deployment and teardown evidence. Tasks remain open until their full acceptance
is met; this checkpoint is not feature closeout.

Vault lookup found a gateway entry and a Facebook login, not a confirmed Base2
application password. Never substitute either credential. Owner activation waits
for the dedicated Base2 Vaultwarden login.
