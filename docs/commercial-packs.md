# Commercial packs

Membership/subscription, catalog/commerce, and listing/marketplace are separate dependency pairs. All six packs default disabled. Only the transaction half of each pair declares the `payment` capability, and its only Feature 093 adapter is the credential-free, socket-free `local_fake` implementation.

Installing, enabling, or configuring a pack does not activate a live provider. Production mode, credentials, network payment calls, refunds against a real provider, and public activation require a separately reviewed and approved feature. Marketplace listings remain unavailable until moderated, self-purchase is rejected, and all local fake operations are tenant- and replay-key-bound.
