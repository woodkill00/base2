# Plan

Native WSL branch 118-preview-antivirus-startup-evidence from main 8504ea0.
Change both supported Compose profiles together. Keep health probes, freshness,
isolation, six-minute launcher deadline and one-hour resource ceiling unchanged.
Emit fixed failure markers before the existing cleanup path; parse strictly and
revalidate exception metadata before serializing the private receipt.

Budget: one focused regression batch, serial complete gate on a clean candidate,
hosted CI, then separately approved live trial. Do not rerun paid trials or
change resources based on an unproven OOM hypothesis. Preserve first failures.
