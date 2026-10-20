# Explicit reauthentication and Google frame repair

Preserve the approved Volcano design and valid signed-in sessions when a sensitive
action requires a fresh sign-in. Explain the requirement, offer an explicit safe
return to the originating page, and never replay the sensitive action automatically.
Refreshed sessions must not gain recent-authentication authority.

The Google button remains provider-rendered, filled black, with standard branding;
its surrounding canvas must blend with the dark page. No provider UI is restyled.

Acceptance includes negative/session-race tests, shared-consumer checks, responsive
visual review, complete gate and CI. Real inbox and interactive Google testing are
deferred. Publication/merge and another paid trial require fresh approval.
