# Data Model: Deployment Observability Entities

## Entities

- Deployment Run
  - Attributes: id/timestamp, mode (full | update-only), outcome (success | partial | fail), artifact_path
  - Relations: has many Log Artifacts

- Log Artifact
  - Attributes: name, type (config | env | log | http-headers | container-state), size, created_at
  - Relations: belongs to Deployment Run

- Cloud Instance
  - Attributes: name, ip_address, region, size_slug, image_slug, created_at, droplet_id
  - Relations: none

- Service Health
  - Attributes: route ("/" | "/api/health"), status (ok | degraded | fail), observed_at, latency_ms
  - Relations: belongs to Deployment Run
