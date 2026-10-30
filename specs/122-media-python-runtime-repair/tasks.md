# Tasks / issue ledger — 122

- [x] T001 Confirm scope, actual vulnerable source, compatible official fixed bases.
- [x] T002 Add failing fixed-runtime/provenance/metadata contract regressions.
- [x] T003 Migrate immutable Python stages; retain exact isolation contracts.
- [x] T004 Add upstream SSL and wheel/ABI checks against the actual final runtime.
- [x] T005 Require complete fresh image SBOM, retaining unchanged security cutoff.
- [x] T006 Run focused local contracts/security tests; review coverage and diff.
- [ ] T007 Parent publishes draft; exact candidate CI passes all image/security tests.

## Issues

- Critical: real CPython SSL distrust omission in old Wolfi source. Reproduction:
  prior PR89 Grype finding CVE-2026-115557; upstream regression rejects compromised
  chain with verification code 28. Status: implementing source/base replacement.
- Medium: tarfile CVE-2026-114583 retained without suppression; 3.15.2 includes
  upstream fix. Fresh scanner evidence is still required.
- Validation prerequisite: no local Docker daemon. Actual container tests/SBOM
  are pending authorized PR CI, not represented by host tests or static contracts.

## Evidence

Registry manifests/configs, verified source archive and read-only layer inventory:
`.artifacts/feature-122/source/` (local evidence, not committed binaries).

## Analysis / focused validation (2026-10-30)

Three new static contracts failed before implementation (`contracts-red.txt`).
After the repair, 135 focused media processor/formats/runtime/worker/derivative,
isolation, CI-policy, dependency-policy and runtime-inventory tests pass
(`focused-validation.txt`). Ruff, workflow YAML parsing and `git diff --check`
pass. Fifteen executable runtime/SBOM tests cover missing/old/misclassified
interpreter, pypi masquerade, missing OS/scanner/wheel, stale APK inventory and
upstream test failure/skip/count; successful real-container checks remain CI-only.

All five original wheel hashes download for CPython 3.15/glibc 2.41. An initial
diagnostic platform list capped glibc at 2.28 and selected a different cryptography
wheel; its hash correctly failed. Repeating with the actual pinned runtime's
complete compatible platform list selected the existing locked manylinux_2_34
wheel. No requirement/hash was relaxed (`wheel-download*.txt`). ELF inspection
finds max required GLIBC 2.34 across wheels; every NEEDED name is in the pinned
base or bundled wheel libraries (`wheel-elf-audit.txt`). Independent ClamAV ELF
review finds max GLIBC 2.30, no direct OpenSSL linkage; native slim provides 2.41.
These checks establish compatibility prerequisites, not executed-image acceptance.

Coverage impact: no application runtime branches changed. New acceptance code is
under the existing test exclusion, with no policy/exclusion change. SBOM validation
function and SSL outcome/skip guard have focused unit coverage; real interpreter,
SSL certificate denial/positive handshake, wheel crypto/PDF/image smoke and SUID
removal assertions run in CI against the final image, not a mocked host claim.

Independent review caught residual ensurepip's bundled wheel after pip uninstall;
it is now explicitly removed. Pip's console-entrypoint metadata normally removes
the `pip -> pip3` alias too; exact-path cleanup is defensive, not evidence of an
observed leftover. Runtime assertions and static contracts cover these removals. The final-stage SSL RUN has network disabled. No Compose/service
privileges, UID, spool, mounts, scanner pins or security cutoffs changed.

T007 is still open: the final candidate is NOT security-cleared until the parent
publishes it and exact-source PR CI supplies a fresh passing image/SBOM/Grype and
all existing hostile-media, signed-spool/two-UID and updater lifecycle evidence.
No local container execution, privilege escalation, deployment or publication was
performed by the repair worker. Full release gate remains parent's open task.

Independent read-only review found no remaining code blocker for Dockerfile
SHA-256 `7590e60c185e6befbb7c106ecc76fd1123ce81511962c46c8adff8f5cd5d9b03`.
It separately verified immutable image/source/wheel identities, ClamAV ABI,
unchanged isolation/policy and negative acceptance checks. This is code-review
completion only, not image acceptance or release approval.

## CI failure / bounded repair (2026-10-30, run 41143078334)

Exact combined head `3f9914595f886423e1da5a9fc531615b1c47e5a7`, security job
`124361718976`: image build, upstream SSL distrust+valid handshake, fixed-version
wheel imports, updater lifecycle and production-code exclusion passed. The later
hardened runtime step failed its duplicate full-filesystem `find` traversal on
`/var/lib/apt/lists/partial` and `/var/cache/apt/archives/partial`. It was UID 0
with all capabilities dropped, NOT a nonroot run: `_apt` owns those mode 0700
directories and CAP_DAC_OVERRIDE was unavailable. Supervisor/two-UID/final-image
SBOM/Grype did not run. First failure excerpt is preserved at
`.artifacts/feature-122/ci-audit-repair/first-failure-job124361718976.log`.

Repair separates two mandatory contexts, never ignores traversal failures:

- Build runs interpreter/import/upstream SSL checks via native setpriv as decoder
  UID/GID 65534, clear groups, no-new-privs and empty capability sets.
- The complete root immutable-filesystem SUID/SGID audit runs LAST in the final
  production build RUN, after every payload COPY and all test-created remnants.
  Every find error, including permission denied, is fatal. No subsequent
  production filesystem mutation is permitted by the static contract.
- Hardened CI runtime smoke explicitly uses UID/GID 65534 and asserts that identity;
  it does not attempt an inherently privileged full-filesystem enumeration.
- Production USER root/supervisor capability model stays unchanged. Later
  acceptance-only script COPYs explicitly use 0644, preventing host SUID/SGID
  metadata from entering the acceptance image.

Test-first repair produced 12 expected failing contracts. After implementation,
91 focused runtime/inventory/isolation/CI contracts pass; the full affected media
batch then passes 147 tests (`ci-audit-repair/full-focused-green.txt`). Ruff and
diff checks pass. Regression tests exercise clean/elevated inventories, root/nonroot audit
preconditions, propagation of exact Permission-denied failure, exclusive required
CLI contexts, wrong-identity rejection and nonroot SSL dispatch. Source-published
CI must now rerun the changed candidate; no image-security clearance is inferred.
