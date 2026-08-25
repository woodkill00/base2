# Edge security policy

Base2 applies defense in depth at Traefik and the frontend container. Production TLS responses require HSTS, deny framing and MIME sniffing, restrict referrers and browser capabilities, and use a restrictive CSP. HTML is never cached; fingerprinted assets are immutable. API CORS is an explicit allowlist and wildcard origins cannot carry credentials.

Public API and frontend routers use bounded edge rate limiting. This is the provider-independent bot and retry-storm baseline; a CDN or managed WAF is an optional, separately activated adapter and may only narrow access. It cannot weaken application authorization, abuse controls, or these headers.

Preview/canary routes deliberately set HSTS to zero because Feature 093 remains staging-certificate-only. They add `X-Robots-Tag: noindex, nofollow, noarchive`, a self-only CSP, and the same framing, MIME, referrer, and permissions restrictions. Public indexing and production certificate issuance remain separate activation decisions.
