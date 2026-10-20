# Plan

Start from clean main 1323dd6051904bc6be98b27b2ecfeb5c18b974f7 in native WSL.
Branch: 116-volcano-auth-usability. No paid resources or extra agents.

Extend GlassInput for password fields with a token-styled, non-submit visibility
control. Keep the input node stable; use accessible state and field association,
hide on blur and never persist visibility. Existing consumers keep their props.
Add explicit autocomplete for login and reset. Configure the supported Google
button theme without CSS filtering, iframe access or replacement branding.

Use existing shared shell, route inventory and visual suites for site-wide
regressions. No Django/API change is needed for this presentation-only feature.
Account settings currently has no inline password input: retain its existing
recovery/security flows, do not invent a new endpoint.

Budget: one discovery sweep; focused unit and browser batch; inspect captures;
review coverage then one complete gate on the ready candidate. Preserve failures;
rerun only after relevant fixes or one justified diagnostic retry. No baseline
updates without actual review. Provider-owned appearance needs separate live
confirmation if a future bounded preview is approved.

Google theme reference:
https://developers.google.com/identity/gsi/web/reference/js-reference
