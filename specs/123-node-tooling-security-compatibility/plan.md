# Plan — 123

## Evidence

At `f83b3e65a1362e786c61496bfae4fc7a400ba0d1`, the unchanged moderate audit fails
on 17 development-tool nodes caused by GHSA-g3hv-75wg-m249 (minimatch <11.0.1)
and GHSA-3g3m-2fjr-6pw4 (glob >=9 through 14.0.1). No affected package is in the
production dependency graph. This does not waive the all-dependency gate.

Upstream's first fixed releases are minimatch 11.0.1 and glob 14.0.2. Available
consumer releases still require older major versions. Their new named exports and
matching representations make unreviewed global overrides unsafe. Backporting only
the vulnerability fixes would leave the audited package versions vulnerable and
does not satisfy the gate.

## Independently reviewed bounded integration

Retain ESLint 8, existing lint configuration and rule coverage. Replace the legacy
cache-deletion dependency through a version-scoped flat-cache -> rimraf 6 update;
flat-cache uses only synchronous deletion with globbing disabled. Select fixed
glob for modern rimraf and the optional TypeScript docgen plugin. Select fixed
minimatch through an explicit, version-scoped consumer allowlist, never a global
replacement affecting unknown consumers.

Where necessary, commit auditable import-only consumer patches for the React ESLint
rules, Redocly and eslintrc ESM entrypoint. Do not patch the fixed minimatch/glob
implementation or rename versions. Use the maintained patch-package tool with
fatal failures and explicit target-version checks. Production installs may skip
development patches only when all target packages are absent; a present target
with a missing patcher is an error. Frontend Docker installation must copy the hook
and patches before npm ci. This is a maintained local compatibility responsibility,
not an upstream compatibility claim; remove patches when maintained consumer
releases support the fixed APIs.

The accepted implementation pins minimatch 11.0.1, glob 14.0.2, rimraf 6.1.3 and
patch-package 8.0.1. Exactly seven import statements in three consumer packages
change: five eslint-plugin-react rules, Redocly's header-pattern matcher and
eslintrc's ESM entrypoint. CJS/eslintrc universal behavior is tested separately.
The fixed packages themselves are not patched. The three patch files use standard
zero-context unified hunks so the patches themselves contain no trailing blank
context whitespace; full original/result file hashes still protect application.

The guard validates the complete patch inventory, patch hashes, consumer versions
and original/result file hashes. `verify:tooling` rejects an unpatched installation;
`test:tooling` runs 27 Node-realm tests separately from the application's JSDOM
environment. Existing npm test/test:ci hooks include this suite; lint/build,
Storybook and OpenAPI generation verify installed consumers before running.
The container copies the hook, manifest and patches before installing dependencies.
No lint rule or application coverage floor changes.

All previous production lock entries, pngjs/type pins and the redirect fix remain
unchanged. Lock churn is limited to the affected development closure and the patch
tool; eight unrelated optional libc metadata fields dropped by local npm were
restored. New/version-changed dependency engine declarations accept the supported
Node 20 and Node 24 versions. Actual local execution used Node 24.22.1/npm 11.9.0;
Node 20 execution and final Storybook acceptance belong to exact-source CI.

## Validation and boundaries

Test actual callable React rule paths, Redocly URL/header matching using a synthetic
in-memory fetch, both eslintrc module surfaces, config/file globbing and lint-cache
creation/reuse/invalidation/deletion. Exercise the optional TypeScript docgen path
directly because normal Storybook defaults do not cover it. Test fixed minimatch
preprocessing bounds and glob cancellation locally with bounded fixtures. All
credentials/URLs are synthetic; no external service requests.

Run focused tests and install-hook failure cases before a clean
`npm ci --legacy-peer-deps`, unchanged moderate audit, production audit, full lint,
TypeScript, unit tests, production build, Storybook build and actual local OpenAPI
type generation. Preserve generated-file drift rather than claiming equivalence.
Keep unrelated lock entries unchanged except necessary transitive closure. Account
for supported Node 20 frontend CI and Node 24 security/container environments.

## Maintenance

Do not regenerate patch hashes to bless unexpected source. Inspect new upstream
versions, update the explicit consumer resolutions, regenerate import-only patches
against verified registry artifacts, and rerun the complete compatibility matrix.
Failing guards are review requests, not instructions to bypass lifecycle scripts.
The pre-existing UUID override is unchanged. A future maintained consumer release
may remove an adaptation only after equivalent behavioral checks pass.

## Primary sources

- https://github.com/advisories/GHSA-g3hv-75wg-m249
- https://github.com/advisories/GHSA-3g3m-2fjr-6pw4
- https://github.com/isaacs/minimatch/releases/tag/v11.0.1
- https://github.com/isaacs/node-glob/releases/tag/v14.0.2
- https://docs.npmjs.com/cli/v11/commands/npm-audit/
- https://github.com/ds300/patch-package
