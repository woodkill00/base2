# Preview recovery and verification

Feature 111 candidate `eb3974f` passed all 121 local release-gate checks. The following
describes the validated interface; it does not grant publication, provider spending,
live deployment or destructive authority. No live-cloud acceptance was run for it.

The native Bash entrypoint is `digital_ocean/scripts/bash/full-preview.sh` and the
PowerShell entrypoint is `digital_ocean/scripts/powershell/full-preview.ps1`.
Both call the same Python module without cross-calling shells. Launch requires
Linux/WSL with user systemd; native Windows launch is not supported. PowerShell
runtime acceptance remains pending where PowerShell is unavailable.

`launch` forwards the existing guarded launch arguments. The installed user timer
is persistent, bound to the lease's original UTC expiry and verified active before
creation. It cannot execute while the workstation/WSL is off. A restart catches up
on the original date, not a renewed lease. Installation failure blocks creation.
Five service restart attempts per ten-minute window are the configured ceiling.
The timer also retries inactive cleanup every minute, so a busy launch cannot
exhaust the only retry window. Terminal cleanup disables its exact timer; terminal
replays need no credential read. Operators must inspect unresolved failed state:
unknown ownership still requires reconciliation, not a destructive automatic retry.

Launch and expiry share one operation lock per lease root. A domain-level lock
also excludes concurrent launches across directories for the same OS account.
Existing full-preview inventory blocks another launch. This is not a distributed
lock between independent operator machines/accounts.

DNS writes persist intent before calling the provider, then persist the returned
identity. A lost response is explicitly uncertain. The system must not repeat a
create or delete a matching record merely because its name/IP looks right.

Read-only reconciliation through either wrapper:

```text
reconcile --reconcile RUN_ID --domain DOMAIN --state-root LEASE_DIRECTORY --credential-file PRIVATE_RESOLVED_CREDENTIAL
```

It reports compute candidate IDs and pending DNS operations; it grants no adoption,
retry or deletion authority. Review the private lease/journal and provider inventory
before an owner-directed repair. Keep journals and original failures; never edit a
pass receipt or mark an uncertain resource destroyed. Live and rollback DNS writes
are journaled; interrupted rollback is not automatically resumed in this candidate.

Before an expensive release gate:

```bash
bash scripts/bash/assure.sh preflight --json
```

This validates existing exact-source repetition evidence. A blocked result requires
freezing a clean candidate and running the supported repetition runner. Passing
preflight is **not** release acceptance and does not replace any full gate, coverage,
visual approval or security check. It does not run tests or create a pass receipt.

Synthetic fixture IDs use `digital_ocean.scripts.python.preview_fixture` for the
run ID plus an optional `-r1` through `-r99` revision. Both active WSL fixture helpers
now consume it. The launch helper uses `full_preview_cli launch`, without a duplicate
transient timer or diagnostic bypass. These three machine-specific helper updates
were explicitly authorized and are outside the Base2 Git repository; never run the
notebook's destructive sync to copy them back. Static validation binds their hashes
in local Feature 111 evidence; no credentials were read by that validation.

Two provider-free Chromium readiness checks run in the complete gate. They prove
the harness rejects both a dashboard URL with the departing signup heading and a
Dashboard heading on the wrong route. This is browser-contract proof, not a new
live-cloud acceptance run or new owner design approval.

No Volcano styles, images or screenshot baselines are changed by this feature.
