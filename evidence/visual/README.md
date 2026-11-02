
### Diagnostic archive schema 2

Schema 1 records remain immutable and valid. Schema 2 Git-transfer manifests add
an explicit outer-artifact-to-inner-ZIP-to-member chain, with a digest for each
available original member. An unavailable historical inner-ZIP digest is recorded
as null with `unavailable-in-retained-inventory`; it is never synthesized from
transferred PNGs. Original archive verification is external. Local verification
covers exact Git-delivered bytes, hashes, dimensions and full PNG decoding.
Persisted archive validation needs retained source history/proofs and stored bytes,
not access to unreferenced transfer commits or the network.

Original media geometry JSON is separately registered by immutable content hash,
project and original schema version. Its strict allowlisted schema is validated
without upgrading or rewriting receipts. Earlier centered-card observations do not
establish universal freedom from obstruction. PNG roles remain per-member:
expected/diff images are never relabeled current actual captures.

Per-case outcomes require the exact retained native report identity or a native
log digest and matching identity. `unknown` explicitly means the per-case result
is unavailable; it cannot establish later validation coverage. Workflow success
is not a substitute for a case result. A null viewport records missing capture
viewport evidence; image pixel dimensions are not assumed to be CSS viewports.

Schema 2 technical review events bind an explicit subset of member/hash/role
triples and record individual inspection, limited contact-sheet overview, or an
exact byte match to previously inspected pixels. They do not approve baselines or
grant acceptance. Legacy hash-only reviews cannot target schema 2 manifests.
Batch event append validates all events before writing any. All source records,
original failures and subsequent review/validation events remain separate.
