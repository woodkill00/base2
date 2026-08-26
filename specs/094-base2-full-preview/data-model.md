# Data Model: Base2 Full-Stack Obsidian Preview

## CanonicalProfile

- `schemaVersion`, `siteId`, `slug`, `name`, `brand`, `domains`, `navigation`, `modules`, `operationsProfile`, `previewPolicy`
- Canonical identity is a SHA-256 digest of normalized validated JSON.
- `base2-obsidian` is a reference profile; fixture profiles remain distinct.

## OwnerAdmission

- `schemaVersion`
- `cidrs`: one to four exact public IPv4 `/32` or IPv6 `/128` entries
- `verifiedAt`, `expiresAt`
- `digest`
- Raw discovery responses are not retained in public evidence.

## PreviewRoute

- `hostname`, `path`, `service`, `exposure`
- `exposure`: `public`, `protected-edge`, or `internal`
- `auth`: edge auth, application auth, or both
- `expectedAnonymousStatus`, `expectedAuthorizedStatus`

## DNSRecordBinding

- `providerId`, `domain`, `type`, `name`, `value`
- `runId`, `createdAt`, `state`
- `state`: `planned`, `created`, `adopted-exact`, `delete-pending`, `absent`
- A record is mutable only when every identity field matches current provider state.

## PreviewLeaseV2

- `schemaVersion`, `runId`, `state`, `armedAt`, `expiresAt`
- `sourceCommit`, `sourceArchiveSha256`, `profileId`, `profileDigest`
- `droplet`: exact provider identity or null
- `dnsRecords`: exact `DNSRecordBinding` list
- `ownerAdmissionDigest`, `certificateMode`, `budgetCeilingUsd`
- `mutationCounts`, `lastError`, `integritySha256`
- States: `prepared`, `compute-bound`, `dns-bound`, `deploying`, `live-verified`, `teardown-requested`, `compute-delete-pending`, `dns-cleanup-pending`, `destroyed`, `blocked`.

## LiveEvidence

- Exact source/profile/lease digests
- Safe service and route statuses
- Screenshot hashes and approved-reference identities
- Console/network error counts
- DNS/provider mutation counts
- Certificate mode and expiry
- Secret findings count; never secret values
