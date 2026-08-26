# Feature 096: Deterministic Preview Orchestration and Visual Assurance

## Objective

Provide one secure, bounded, repeatable workflow that reconciles prior Base2 previews, validates a native WSL runtime, launches an exact merged commit, distinguishes authoritative DNS from recursive cache state, verifies public and protected routes against the leased address, captures complete visual evidence, reports typed failures, and enforces exact eventual cleanup whenever at least one approved controller is online.

## Non-negotiable boundaries

- Preview certificates remain Let's Encrypt staging-only.
- Provider mutation requires an exact merged commit, exact source archive digest, exact profile digest, one public owner `/32` or `/128`, a bounded TTL, and the existing USD 0.25 ceiling.
- Deletion is permitted only through integrity-bound lease IDs, provider resource IDs, DNS record IDs, and ownership tags. Mutable names are never deletion authority.
- DigitalOcean credentials remain owner-only SecretRef output and are never copied to a Droplet, Git, evidence, screenshots, Discord, or process arguments that are reported.
- Public DNS verification and exact-address application acceptance are separate checks; neither may substitute for the other.
- Baseline screenshots never update silently. A visual change is evidence until explicitly reviewed.
- Windows executables are invalid for repository, deployment, Playwright, Git, Python, Docker, SSH, and Node work.
- SVG is required for scalable interface artwork; raster assets are allowed only for photographs, textures, screenshots, or content whose source is inherently raster.
- The feature grants no production deployment, production certificate, broad network, unrelated provider-resource, or arbitrary-command authority.

## User stories

### US1 - One deterministic operator workflow (P1)

As the owner, I can run one command to preflight, inspect, launch, verify, review, extend, or destroy a Base2 preview without reconstructing private paths and command sequences.

Acceptance:

- Commands return versioned JSON receipts and stable exit codes.
- Repeating status, verification, or destruction is idempotent.
- Conflicting active operations fail closed under an exclusive lock.

### US2 - Cost-safe exact lifecycle (P1)

As the owner, I know an expired or failed preview cannot silently continue consuming resources.

Acceptance:

- Launch is blocked while an unresolved owned preview or lease exists.
- A persistent expiry timer is armed and verified as part of launch closeout.
- A backup observer reports when cleanup authority is unavailable.
- Successful destruction proves zero exact-owned Droplets and absence of every leased DNS ID.

### US3 - Honest DNS convergence (P1)

As the owner, I can distinguish correct authoritative DNS from stale workstation, router, or ISP cache results.

Acceptance:

- Required A and AAAA state is checked through provider, public recursive, system recursive, and exact-address views.
- Stale answers include the resolver, retired address, observed TTL when available, and a safe remediation.
- Browser evidence is pinned to the exact leased IPv4 while public DNS remains a separately required receipt.

### US4 - Native runtime certainty (P1)

As the operator, I receive a pre-mutation failure if WSL inherited Windows Node, npm, Python, Git, SSH, or Docker tooling.

Acceptance:

- Runtime paths, binary format, architecture, and required versions are checked before credential access.
- Windows, UNC, `/mnt/c`, missing, or incompatible executable paths fail with a typed diagnostic.

### US5 - Complete visual evidence (P1)

As a reviewer, I can inspect every declared public section, navigation surface, responsive state, and protected application from one private report.

Acceptance:

- Desktop, tablet, mobile, landscape, large-text, reduced-motion, and representative DPR states are declared and validated.
- Geometry checks reject horizontal overflow, covered controls, inaccessible internal scroll regions, and viewport escape.
- An HTML/JSON evidence index binds screenshots to commit, profile digest, viewport, browser, route, state, SHA-256, and review status.

### US6 - Typed recovery and notification (P2)

As the owner, failures do not disappear or require log archaeology.

Acceptance:

- Failures use a fixed code catalog, safe summary, cleanup state, recommended recovery, and evidence path.
- Provider rate limit, stale DNS, unhealthy containers, browser failure, authentication failure, expiry failure, and orphaned-resource conditions are represented.

## Functional requirements

- **FR-001** Provide `preflight`, `status`, `dns`, `evidence`, `launch`, `arm-expiry`, `extend`, `destroy`, and `verify` commands.
- **FR-002** Use one canonical private state root and enumerate all valid version-2 leases without following symlinks.
- **FR-003** Reject malformed, duplicate, conflicting, or integrity-invalid leases.
- **FR-004** Reconcile exact-owned provider inventory before launch and after teardown.
- **FR-005** Enforce a single mutation lock and deterministic request digest.
- **FR-006** Validate native Linux runtime tools before reading credentials.
- **FR-007** Separate authoritative/provider DNS, public recursive DNS, system recursive DNS, and exact-address route evidence.
- **FR-008** Detect stale, split, duplicate, and unexpected IPv4/IPv6 answers.
- **FR-009** Derive browser target address from the integrity-checked lease by default.
- **FR-010** Create a persistent expiry unit bound to exact run ID, lease root, and credential file.
- **FR-011** Verify the expiry unit is armed; otherwise launch closeout fails with cleanup guidance.
- **FR-012** Extend only a live verified lease, within maximum TTL and budget, through an exact approved request.
- **FR-013** Produce an inventory receipt containing counts and identities but no secrets.
- **FR-014** Generate a private visual evidence manifest and HTML index using only validated local artifacts.
- **FR-015** Hash every evidence artifact and reject symlinks, traversal, unexpected formats, oversized files, and duplicate logical identities.
- **FR-016** Require declared coverage for public sections, navigation, footer, palette, operator surfaces, and authenticated application states.
- **FR-017** Enforce scalable SVG UI-artwork policy and explicitly classified raster exceptions.
- **FR-018** Retain responsive geometry tests using `calc()`, `min()`, `max()`, or `clamp()` for major layout dimensions.
- **FR-019** Emit typed, redacted diagnostics and stable nonzero exit codes.
- **FR-020** Preserve exact failure cleanup and exact DNS rollback behavior.
- **FR-021** Generate no provider mutation from `preflight`, `status`, `dns`, or `evidence`.
- **FR-022** Keep all output deterministic for identical sanitized inputs.
- **FR-023** Accept launch configuration only from an owner-only, schema-validated real file; reject request-supplied commands and unknown fields.
- **FR-024** Prove the launch commit is the exact clean local `main`/`origin/main` commit before archive creation.
- **FR-025** If expiry arming fails after launch, immediately invoke exact lease cleanup and report reconciliation instead of success.
- **FR-026** Keep the expiry execution path stable across branch deletion, checkout switching, and ordinary repository updates.
- **FR-027** Emit bounded cost, retention, rate-limit, and notification/outbox receipts without secret values.
- **FR-028** Bind every DNS observation to source class, observation time, expected address, normalized answers, and receipt digest; unavailable TTL is explicit rather than invented.
- **FR-029** Journal launch intent before provider mutation so an interrupted pre-lease launch is recoverable by exact admission tag.
- **FR-030** Represent primary and backup cleanup-controller availability honestly; no software may claim guaranteed wall-clock cleanup while every controller is offline.
- **FR-031** Separate representative pull-request visual coverage from the expanded release matrix while keeping both deterministic and required at their declared gate.
- **FR-032** Wait for fonts and declared stable UI state, disable nondeterministic animation, and bound screenshot dimensions/bytes before accepting visual evidence.
- **FR-033** Validate SVG content for unsafe scripts, external active content, missing viewBox, and inaccessible semantic use.

## Edge cases

- WSL resolves only some subdomains to retired addresses.
- Public resolvers disagree temporarily after a DNS transaction.
- An expired lease exists but its Droplet is already absent.
- DNS cleanup completes partially and must resume.
- The workstation shuts down before expiry and resumes afterward.
- A timer exists but points at the wrong run or credential file.
- Evidence contains a symlink, duplicate screenshot identity, corrupt PNG, unknown viewport, or oversized file.
- Playwright succeeds against an exact address while public DNS remains stale.
- A Windows executable is reachable earlier in `PATH` than the Linux tool.
- Two operators start lifecycle mutations concurrently.

## Measurable outcomes

- One command produces a complete preflight receipt without credential access.
- All destructive replays perform zero additional mutations.
- Every live acceptance receipt binds the leased IP, commit, profile, DNS views, screenshots, and application logins.
- Every declared visual surface has desktop, tablet, and mobile evidence, with expanded release-only responsive states.
- No tracked secret finding, raw credential output, unrelated provider mutation, or production certificate request occurs.
- Complete gate, focused lifecycle/DNS/runtime/evidence suites, visual suite, and live canary closeout all pass.
