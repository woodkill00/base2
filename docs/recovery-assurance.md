# Recovery assurance

Backups and stateful preview snapshots use AES-256-GCM with a fresh nonce, authenticated metadata, plaintext digest, atomic owner-only storage, and a Vaultwarden SecretRef recorded instead of key material. Restore is permitted only into an absent isolated target after exact target, schema, AEAD tag, size, and digest validation. A live or existing target is refused.

Migration preflight rejects downgrade and stale rollback data. Certificate drills are hard-wired to ACME staging. Stateful preview destruction requires the existing lease-bound preservation policy to accept a complete, encrypted, unexpired snapshot before teardown; recreation must decrypt and match the approved state exactly. Key retrieval, provider mutation, production restore, and live certificate issuance remain separately authorized operations.
