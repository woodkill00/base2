# Base2 module SDK

Base2 modules are declarative JSON manifests. A manifest may declare data models, ordered migration files, API and UI routes, navigation entries, namespaced permissions, scheduled-job identities, a settings schema, health checks, reviewed provider capabilities, dependencies, and data-lifecycle policy. It cannot declare commands, callables, imports, executable hooks, credentials, or provider configuration.

`scripts/python/module_registry.py` validates one manifest or a complete registry. Validation rejects unknown keys, incompatible Base2 versions, unsafe paths and routes, namespace violations, unknown capabilities, conflicts, missing dependencies, and cycles before any lifecycle operation.

`scripts/python/module_lifecycle.py` owns lifecycle state. Its state and lock files are owner-only. Install, enable, disable, upgrade, and removal operations require a caller-created operation ID and a complete validated manifest. Exact replay returns the prior receipt; reuse with changed input fails. Disable always suppresses scheduled jobs and follows the declared preserve/archive policy. Removal follows forbid/backup-required/purge policy. Upgrades expose a migration preview and cannot remove migration history. Rollback accepts only the exact latest signed receipt and exact current/before state digests.

The admin overview contains only module ID, version, state, job state, data state, health-check identities, and declared capabilities. It excludes receipt keys, state snapshots, operation history, settings, credentials, and module data. A future UI must consume this projection and must not read the private lifecycle file directly.

Adding a module requires reviewed manifest/schema changes, migrations, isolated tests, documentation, and a compatibility declaration. Provider capability declaration does not activate a provider or grant credentials; activation remains a separate approved operation.
