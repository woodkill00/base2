# Immutable release path

Release admission requires an image pinned by SHA-256 digest, exact 40-character source commit, SBOM digest, provenance digest, and integrity signature. A changed manifest, mutable tag, bad signature, or reused release ID with different content fails before health checks or traffic state.

The provider-neutral controller records private atomic state, admits a candidate, evaluates its health gate, and changes traffic only after success. Failed health restores the prior release without traffic change. Explicit rollback is bound to the exact current release. Provider deployment, registry credentials, public traffic mutation, and production rollout still require separate scoped authorization.
