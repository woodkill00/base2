# Specification

## Goal

Provide every generated Base2 site with one optional media library for images,
documents, audio, and video. New originals remain private and quarantined until
trusted byte inspection, a current malware scan, and a safe derivative succeed.

## Required behavior

- One closed `media` module version and policy schema drives generated routes,
  navigation, permissions, formats, limits, jobs, storage, and checks.
- Disabled profiles have no media navigation or registered API surface.
- Every repository query is tenant scoped; object keys never enter public APIs.
- Upload metadata, checksums, byte limits, replay, expiry, lifecycle, and
  optimistic versions fail closed.
- Originals are immutable, encrypted outside the webroot, and never served
  inline. Safe derivatives use restrictive delivery headers.
- Exact deduplication cannot disclose cross-tenant presence; similarity never
  mutates data.
- The browser library provides search, filters, selection, keyboard-equivalent
  multi-upload, progress, empty, error, processing, and quarantine states.
- Visual and interaction proof covers compact through ultrawide layouts, zoom,
  themes, RTL, high contrast, and reduced motion before merge.

## Authority boundary

Repository implementation and tests grant no authority to publish, merge,
deploy, spend, mutate DNS, issue production certificates, or retain a provider
resource. Each remains separately approved and exact-source bound.

## Non-goals

Executable content, HTML, arbitrary archives, active SVG, remote URL ingest,
live streaming, DRM, biometric analysis, and automatic similarity merging are
not supported.
