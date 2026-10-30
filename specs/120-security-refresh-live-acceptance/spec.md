# Security refresh and bounded live acceptance

Restore current dependency and container security acceptance without changing
the approved Obsidian/Volcano design, authorization boundaries, or audit floors.
Users retain working authentication, explicit reauthentication and media flows.
Validate the repaired release through automated live acceptance, with truthful
failure evidence and verified teardown. Real email and interactive Google tests
remain deferred; no new product features or persistent infrastructure.

Acceptance: current package/container scans meet existing policies; media isolation
and decoder compatibility pass; full local gate and hosted CI pass before merge;
the merged source passes deployment admission; one Frankfurt trial uses staging
certificates, at most 60 minutes/USD 0.25, and ends with verified cleanup.
