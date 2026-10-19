# Bounded live acceptance

Authority: one Frankfurt preview, staging TLS, maximum 60 minutes and USD 0.25,
after exact-source local release and hosted CI pass. Preserve independent expiry
cleanup and tear down afterward. No additional trial or lease extension is implied.

## Preconditions

- Use the guarded full-preview CLI through the existing notebook launch helper.
  Confirm the previous receipt is destroyed and provider inventory has no owned
  leaked resource before provisioning. Do not alter the four sending DNS records
  during temporary preview teardown; receiving MX remains out of scope.
- Build the private mail handoff through the existing validated configuration
  path, using the existing scoped Vaultwarden Resend credential. Never print it.
  Set the sole recipient to `thejunkmailvoid+base2-test@gmail.com`, a lease no
  longer than the preview and at most five send attempts. Never reset that budget.
- Confirm the owner is available for mailbox actions before starting the lease.
  Store disposable credentials only in private local state; no secrets, reset
  URLs, verification URLs or populated password fields in logs/screenshots/traces.
- Keep Discord delivery disabled. No receiving email service or contact-email
  delivery is enabled. Optional modules remain disabled in the default profile.

## Required outcomes

1. Run the supported live browser acceptance, restricted subsites, responsive
   shared-layout and approved-reference comparisons. Preserve every failure and
   do not substitute a changed-source retry for the original result.
2. Create the approved disposable Base2 account and request verification once.
   Ask the owner to confirm inbox receipt and use the verification link privately.
   Verify the account is verified; token expiry/replay remains additionally covered
   by the isolated PostgreSQL suite. Never request that the owner paste a token.
3. Establish a session for that disposable account, then request its Base2 reset
   once. Ask the owner to complete the reset privately. Verify old sessions and
   the original disposable password no longer authorize access, and the owner
   can sign in with the new disposable password. Do not request that password.
   This changes neither Google's password nor the reusable Woodkill account.
4. Verify email health/budget evidence and stored contact outcome without claiming
   contact email delivery. An inbox delay is pending, not a passing delivery test.
   Do not send repeated emails to work around unavailable owner confirmation.
5. If a live failure requires a code change, preserve its receipt, stop dependent
   checks, fix/test locally, and obtain fresh authority if another trial is needed.
   Do not extend the existing lease to accommodate a new candidate.
6. After confirmation or at the deadline, use the supported exact teardown.
   Independently verify owned droplet/temporary DNS removal, preserved mail DNS,
   and lease status. Record elapsed time and cost as measured or clearly estimated.

Human confirmation is an explicit prerequisite, not something automation may
forge. If the owner is unavailable, stop that acceptance step and report it while
still completing cleanup. No unknown-defect or all-provider-combinations claim.
