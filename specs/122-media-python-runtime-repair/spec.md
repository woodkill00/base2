# 122 — Media inspector Python security repair

## Outcome

Media inspection uses an actually fixed Python release, without weakening its
isolation, authenticated spool, decoder limits, malware protection, or security
gates. The owner authorized this separate repair on 2026-10-30 after the existing
image failed the critical-vulnerability gate; this does not authorize deployment.

## Acceptance

- The shipped interpreter rejects the compromised intermediate certificates and
  still accepts a valid TLS handshake. Its identity and origin are independently
  checkable, and no vulnerable predecessor remains in the final filesystem.
- Locked media wheels, hostile-media behavior, signed receipts, two-UID spool,
  updater lifecycle, and runtime isolation keep passing their existing checks.
- A fresh final-image SBOM identifies the real interpreter and OS/scanner
  components. The unchanged high/critical Grype gate passes, without exceptions,
  suppression, misleading package versions, or undocumented scanner omissions.
- Production excludes acceptance fixtures, uses minimal runtime rather than build
  tooling, and exposes no new privileges, networks, ports, or writable mounts.
- Until exact-source CI establishes these results, the candidate remains blocked.
