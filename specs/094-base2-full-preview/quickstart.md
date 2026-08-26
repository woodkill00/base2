# Quickstart: Base2 Full-Stack Obsidian Preview

## Local readiness

```bash
python3 scripts/python/generate_site_profiles.py --check
python3 -m pytest digital_ocean/tests/test_full_preview_policy.py digital_ocean/tests/test_preview_lease_v2.py
cd react-app && VITE_SITE_PROFILE=base2-obsidian npm run build
cd .. && scripts/bash/test-base2-full-preview.sh
```

The result may become `ready_for_live_approval`; it must not create provider resources.

## Live boundary

Live creation, DNS mutation, credentials, and teardown require a private resolver plus exact owner approval through the supported orchestrator. Certificates remain staging-only. Administrative URLs require both current owner-host admission and edge credentials; Django and pgAdmin additionally require their application login.

## Required view matrix

- `/`, `/api`, `/api/health`
- `admin.<domain>/admin/`
- `swagger.<domain>/docs`
- `traefik.<domain>/`
- `pgadmin.<domain>/`
- `flower.<domain>/`

## Completion

Completion requires a reviewed live screenshot, zero failed route checks, all services healthy, and a subsequent exact teardown proving zero owned provider and DNS resources.
