# Representative implementation decisions

Proceed with the approved plan's default: both rails on desktop, no auth omission
exception; public-safe guest links and no new privileged actions. Geometry follows
the proposed acceptance contract, subject to owner review at T013.

The owner subsequently directed completion of every first-party page (cycle 5).
All AppShell and PublicShell consumers now use the candidate when enabled. The
supported Compose builds enable it with `BASE2_SHARED_LAYOUT=true`; setting false
and rebuilding retains the legacy layout as a rollback. Direct Vite diagnostic
builds still require `VITE_LAYOUT109_PREVIEW=true`. The shared AppShell remains
the entrypoint, not a third permanent shell. Home section/share/search, safe utility,
movement and palette actions live in its context slot. The palette is inline, not
an overlapping legacy modal. Rich public/Home footer uses content-sized tracks.

Owner visual acceptance: PENDING. No blanket approval inferred from implementation
authorization. No cloud launch or existing lease extension for this prototype.
