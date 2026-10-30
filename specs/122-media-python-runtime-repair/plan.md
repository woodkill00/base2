# Plan — 122

## Evidence and decision

The former Wolfi Python APK is 3.15.1_git20261024-r1, built from CPython
`d6903b58e39427b251d5ef602c867214cb9fe7a1`, before the 3.15 SSL fix
`36cd295f32fc9ba19399e01abee91231440a41dd`. A newer vendor image did not establish
a fixed package. Do not relabel that APK or copy Debian Python into Wolfi's
OpenSSL 4 runtime.

Migrate all Python stages to immutable linux/amd64 Docker Official Python 3.15.2
trixie images (full build stage, slim production stage). This uses the official
source rebuild on a consistent Debian libc/OpenSSL ABI, not a new custom build
recipe. Registry configs and source tarball agree on Python.org's SHA-256. Track
images, source, and official recipe revision in `api/media-inspector-runtime.lock.json`.
Use the slim image's native setpriv/libcap-ng; retain `/usr/bin/python` via a
symlink to native `/usr/local/bin/python3.15`. Keep wheel pins and scanner inputs.

## Build/runtime checks

Download and hash-check the official source archive in the builder only. Bind
mount its `Lib/test` into the production build for the upstream
`SSLObjectTests.test_distrusted_spki` (verify code 28) and a positive handshake;
reject skipped tests. Run the same production interpreter against binary wheel
imports and cryptographic/PDF/image smoke checks. Do not ship source fixtures.
Remove pip from the final runtime and clear inherited SUID/SGID bits; no compiler
or new package installation enters production. The slim base does retain Debian
shell/utilities: a documented base-migration tradeoff, not expanded service
capabilities. Existing network-none/read-only/no-new-privileges/two-UID controls
remain unchanged.

Preserve Debian's dpkg database and add genuine ClamAV control/owned-path metadata
instead of replacing the OS inventory. Fresh Syft output must include Python
3.15.2, Debian dependencies and ClamAV before the unchanged Grype high gate.

## Validation and budget

Static contracts and focused unit/security tests first; the existing authorized
GitHub PR CI then builds the image and runs SSL, wheel, hostile-media, signed
spool/two-UID and updater acceptance plus fresh SBOM/Grype. Local Docker is
unavailable; do not change daemon or sandbox privileges. No provider, deployment,
merge, publication, or visual changes are part of this repair. Parent alone may
publish the draft candidate. Reassess each material CI failure before retrying.

## Sources

- https://www.python.org/downloads/release/python-3152/
- https://github.com/python/cpython/pull/160568
- https://github.com/docker-library/python/tree/f4c67ece208dead594e43628d22e3c6027dd97ab/3.15
