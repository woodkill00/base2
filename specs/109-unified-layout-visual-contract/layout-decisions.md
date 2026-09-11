# Representative implementation decisions

Proceed with the approved plan's default: both rails on desktop, no auth omission
exception; public-safe guest links and no new privileged actions. Geometry follows
the proposed acceptance contract, subject to owner review at T013.

Only Home, Dashboard and Settings opt into the candidate shell before that review.
Other consumers remain on their current rendering until approval. The shared
AppShell is the entrypoint; this is a staged replacement, not an additional permanent
competing shell. Keep existing Home section/share/search behavior in a context slot.

Owner visual acceptance: PENDING. No blanket approval inferred from implementation
authorization. No cloud launch or existing lease extension for this prototype.
