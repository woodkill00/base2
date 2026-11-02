# Project screenshot retention

Retain synthetic project test screenshots for evaluation and reference. Approved
Playwright references stay in their existing `*-snapshots` paths and Git history.
Diagnostic retention never approves an image or makes a failing test pass.

## Storage and provenance

`evidence/visual/objects/<sha256>.png` stores unchanged, deduplicated diagnostic
bytes. `evidence/visual/runs/<run>-<attempt>-<job>-<artifact>.json` is immutable:
it records repository, exact source commit/tree, requested PR head, native IDs,
archive hash, test/project/viewport, PNG hash/dimensions/size, capture role and
original result. Import metadata has no URL fields. Do not store signed download
URLs, credentials, real user data or internal conversations. Import only inspected
synthetic fixture captures; PNG validity alone is not a sensitive-data check.

Each capture's `storage` is either `objects/<sha256>.png` or
`git:<commit>:react-app/e2e/<suite>-snapshots/<reference>.png`. A Git reference must
resolve to exactly the imported bytes, preserving the old reference even after a
baseline change. Identical new PNGs share one object. Do not delete first failures
or overwrite run manifests when a later comparison succeeds.

Before import, independently verify GitHub run/job/artifact metadata and ZIP digest
through the authorized connector, and inspect the synthetic fixture scope. The
local importer verifies declared provenance consistency, ancestry and byte
integrity; it cannot authenticate GitHub metadata offline. Test fixtures in its unit
tests are deliberately synthetic and must never become native evidence.

## Import and validation

Use the repository Python entrypoint with the normal API development dependencies:

```
python -m scripts.python.screenshot_archive --repo . --archive /safe/local/captures.zip --manifest /safe/local/run.json
python -m scripts.python.screenshot_archive --repo .
python -m scripts.python.screenshot_archive --repo . --event /safe/local/review.json
```

The run JSON fields and exact allowed values are defined by `validate_manifest`.
A nonempty explicit member inventory is required. The ZIP is limited to 32 MiB,
selected PNG file bytes to 30 MiB and each decoded image to 32 million pixels; oversized collections must be split upstream
without truncating images. Only inventoried PNGs are imported; traces, video,
fixtures and unlisted files are excluded. Source identities must exist in Git and
the requested head must be an ancestor of the actual tested commit. No network,
browser, Docker, baseline write, Git commit or push occurs in the importer.

Technical review and later native validation are separate immutable
`events/<event-sha256>.json` records targeting the exact original manifest hash and
capture hashes. A review records inspected pixels and an intended-change,
defect-found or inconclusive conclusion. A later validation references a separately
retained native run manifest covering the same tests/projects/viewports, preserving
its actual result. Neither event grants whole-suite acceptance or modifies the
original pending fields. Notes must describe technical findings only. Record
reviewer identity and review context in the ordinary PR review, not internal
conversation transcripts in the archive. Baseline changes require the existing
technical review/publication process and fresh native tests afterward. Existing
accepted review manifests remain governed by their own full-matrix contracts.

## Collection coverage and next adapters

`screenshot-inventory.json` inventories every current explicit screenshot source
(including helpers) and every automatic failure-screenshot configuration. A source
contract fails when a new source/configuration is absent from that inventory.

Implemented native collection: workspace high-contrast records, schema, imports,
and exports, each in a bounded artifact containing actual/expected/diff/post-assert
PNGs where produced. Existing full artifacts remain unchanged. The importer and
validator accept explicitly inventoried captures from any listed synthetic suite;
this does not mean those other suites have a bounded collector yet.

Pending bounded adapters: remaining workspace projects; media and operations full
matrices; account/settings; layout/Volcano; journeys and optional modules;
experience; visual/localization/restoration; restricted notice; Google binding;
real-service workspace representative; and automatic failure screenshots from all
listed configurations. Live-preview captures additionally require explicit
synthetic-data verification before retention. Preserve existing artifacts while
adding adapters incrementally. For each adapter, retain every produced PNG role,
source/test identity and original outcome; split inventories into bounded artifacts
and deduplicate bytes only at archive import. No CI repository-write credential or
automatic promotion is introduced.

Initial population retains 30 native capture records across six artifact manifests,
using 20 new content-addressed objects and exact historical Git references for the
remaining captures. Original failures from runs 41268107152 and 41277438310 remain.
The passing targeted media/operations captures from run 41277438310 are recorded
separately; they do not imply that its frontend job passed. `originalOutcome` at the
manifest level summarizes its inventoried captures; each capture retains its test
outcome. It is not the enclosing workflow/job conclusion.

Four workspace HC references are prepared from reviewed native actual captures.
Their filenames are `workspace-<view>-chromium-high-contrast-chromium-high-contrast-linux.png`
in the existing workspace snapshot directory:

| View | Exact native actual SHA256 | Original different pixels |
| --- | --- | ---: |
| records | 28fbeee09d5e63280ba83a5a97b5fec76b72577985fd5b5f9a7aec2a4c8a9cb0 | 65540 |
| schema | 90ee262788f063532814a7f5c892149d56b28de228a6c4986948665d28285c7f | 67505 |
| imports | 8a2598ad098085ebf595b135a01a43813267049ad587c4dfe4140b9841209245 | 82941 |
| exports | 7e9ce3f60b1e9c8466707fe462e0159131b955a019f8962e57dfa01eabc8d233 | 89408 |

Technical review identifies system palette, control borders and selected-tab
underlines replacing stale normal-mode references, without a new clipping/layout
regression. Hard forced-mode, paint and accessibility prerequisites passed before
the original comparisons failed. The threshold remains `maxDiffPixelRatio: 0.01`.
Fresh native validation of these four replacements is pending. No other baseline
or accepted full visual manifest changes are included.


## Explicit Git transfer mode

When the original ZIP was verified in a separate authorized environment, PNG bytes
may arrive through an exact Git transfer commit. Use `--git-transfer --manifest`
instead of `--archive`. The additional `transfer` object records commit/tree, exact
SHA256-to-Git-blob mapping, `originalArchiveVerification` set to
`externally-verified-zip-and-members`, and `localVerification` set to
`git-blob-sha256-size-dimensions-full-decode`. The importer verifies each regular
Git object path, blob ID, size, SHA256, dimensions and full decode before writing.
It does not claim to have rehashed the original ZIP locally. The ZIP importer
continues to require actual ZIP bytes and rejects Git-transfer claims.

This population used transfer commit c1fd5134f08af2905268b870a9a784db9896d003,
tree 1ced85a887bd9f780ee2d141afeada53414c53d8. The transfer commit is transport
provenance, not a tested application source or a publication branch. Subsequent
archive validation verifies retained PNGs and declared source identities; it does
not require the unreferenced transfer commit to remain fetchable. Exact source
commits must be available locally for ancestry checks. External archive and member
verification remains a reviewed prerequisite, never an inferred local result.

Backend API CI now validates the committed archive after installing the existing
pinned API development dependencies. Checkout retains full history and does not
persist credentials. The validator checks run manifests, review/validation events,
PNG integrity/full decoding, and historical baseline references rooted in retained
ancestry. It grants no native visual acceptance and performs no network fetch.

Two native runs used temporary GitHub merge commits. Their exact commit-object
bytes are retained in `evidence/visual/sources/<source-sha>.commit`. Validation
recomputes the Git commit identity, checks the declared tree and direct requested
head, then requires tree equivalence to that head in retained repository ancestry.
This preserves exact-source evidence without relying on future fetchability of
those merge commits. The transfer commit itself is still provenance only; its
objects are not required for ongoing archive validation.
The CI invocation includes `--require-runs`, so an empty or missing archive fails
instead of reporting a vacuous integrity result.
