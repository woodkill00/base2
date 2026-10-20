# Fresh sign-in before sensitive actions

A restored session remains signed in, but some actions (such as requesting a
personal-data export) require a fresh sign-in. Base2 explains this without logging
you out. Choose **Sign in again**, complete normal password/MFA or Google
authentication, and return to the original page. Submit the action again yourself.
Base2 never submits it automatically.

Failed or cancelled authentication does not grant new authority. A successful
cookie refresh alone does not satisfy the requirement. Return links remain on
this site and omit query strings and fragments.

The Google button uses Google's supported dark theme. Only the surrounding frame
rendering context is adjusted to avoid a white canvas; Google branding and consent
pages are not altered.
