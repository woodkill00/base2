# Transactional email

Transactional email is disabled by default. The only enabled implementation in Feature 093 is `local_fake`, which records a deterministic outcome without opening a socket or contacting a provider. Unknown adapter names fail closed. Any live provider requires a separate activation feature, credential reference, domain controls, provider-specific webhook verification, and owner approval.

Verification, password-reset, contact-receipt, and invitation templates validate recipient and action URLs, produce text and escaped HTML alternatives, and reject header injection or insecure public links. Delivery state distinguishes disabled, sent, suppressed, retry, and dead-letter outcomes. Bounce results become suppressions; retryable failures are bounded to three attempts.

Operator diagnostics expose the outbox identifier, recipient digest, state, provider label, timestamps, and whether an error exists. They never include the recipient address, message body, action token, or raw provider response.
