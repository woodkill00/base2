# Feature 124 disposable real-service acceptance

Supported entrypoints: `scripts/bash/e2e-isolated.sh` or, on Linux/WSL with
PowerShell and Python `fcntl`, `scripts/powershell/e2e-isolated.ps1`. CI (e2e)
uses the same isolated runner. Do not run this against a deployed environment.
The fixed project owns its disposable database, Redis and encrypted local artifact
volume and removes them on exit. No live email adapter is configured or invoked.

`workspace_fixture.py seed` is a one-shot Compose setup dependency, not an API.
It requires the exact test environment, fixed generated `base2-obsidian` profile,
local `postgres/e2e` database and owner setup role, and refuses any pre-existing
auth users or organizations. It creates six synthetic login-capable actors and a
pre-ready PNG variant. The PNG uses the real encrypted local artifact store; its
readiness is **seeded, not proof of media inspection/scanning**. Real sessions and
all policy, preference, record, approval, role, export and asset requests use the
existing API. No browser tenant selector or role-grant endpoint is added.

`workspace_fixture.py snapshot` and `consume --now <UTC ISO timestamp>` execute
only through trusted `docker compose exec` or `run --rm --no-deps` using the
restricted content-worker service. The deterministic section stops beat and the
queue consumer, then uses a fresh restricted container/process for each call so
queued real-time tasks cannot race its controlled clock. They
accept no SQL, site, role, recipient or credentials. Snapshot reports bounded
synthetic identities, notification status/receipt keys and scheduler audit events.
The direct clock is limited to five minutes in the past/two days in the future.
It is not a production clock or authentication bypass. Synthetic passwords and
fixture UUIDs are intentionally public test data, never real credentials.

The Playwright journey has no API mocks or route interception. It covers:

- Real browser login/cookie refresh and CSRF denial; two rendered settings tabs
  conflict and reconcile without overwriting the first committed preferences.
- Independent approval, self/stale/role-revoked denial and due scheduler denial.
- Public direct/search visibility before and after restriction; active-member
  record/export/asset access; suspended/nonmember direct/search/export/asset denial.
- Durable immediate review delivery through **actual beat and content worker**
  after a worker restart (the ordinary production 60-second schedule is unchanged).
- Separately labeled **direct controlled-clock service** proof of opt-out,
  next-UTC-boundary digest, restart/replay idempotency and recipient revocation.

`workspace_fixture.py suspend-viewer` runs only via the existing one-shot
`workspace-fixture` setup service, never inside the runtime API or worker. It
requires the owner-only disposable guard, checks the exact synthetic organization
and all six predetermined actor IDs/emails, takes the production effect lock, and
changes only that seeded active viewer to suspended. There is no ID/site/SQL/role
parameter or HTTP endpoint. This is explicitly **fixture-driven membership state
change, not acceptance of a user-facing suspension flow**. The viewer's own asset
and export grants first succeed, then fail after suspension; measured elapsed time
must remain below their 60-second TTL with a one-second safety margin. The JSON
attachment contains timing/status evidence, not grant tokens.

The ordered journey cannot automatically retry against partially mutated shared
state. Start a new disposable run after a failure. Authentication alone honors one
server-provided bounded `429 Retry-After`, because actors share one loopback IP;
incorrect passwords and other auth failures are never retried or bypassed.

Evidence is retained on success and failure under `e2e/artifacts/` and normal
Playwright result attachments. `real-beat-after-worker-restart` and
`controlled-clock-local-sink-not-beat` are distinct JSON attachments. Compose logs
provide actual scheduler/task execution evidence; receipts alone do not prove TLS
or a live notification provider. Runner exit/cleanup status and source commit are
recorded; local collection/static passes are not runtime acceptance.

## Explicit remaining boundaries

This is loopback HTTP with non-Secure test cookies and Nginx, not Traefik/TLS
acceptance. Never invoke live-full-preview to fill that gap without its separate
authorization. The local sink stores receipts only; it never sends mail. One
base2-obsidian run does not close representative publishing/docs/portfolio profile
coverage, all Feature124 T16 obligations, migration/restore/race acceptance, visual
review, or the complete release gate. The same-actor stale-grant test uses the narrowly scoped fixture suspension above;
a user-facing membership suspension journey still needs a supported API and is not
claimed here.
