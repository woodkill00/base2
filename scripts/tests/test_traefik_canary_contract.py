from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_canary_template_has_one_exact_host_and_no_sans() -> None:
    template = (ROOT / "traefik/dynamic-canary.yml").read_text(encoding="utf-8")
    assert template.count("Host(`${WEBSITE_DOMAIN}`)") == 2
    assert "HostRegexp" not in template
    assert "sans:" not in template
    for forbidden in ("www.", "admin.", "swagger.", "pgadmin", "flower", "traefik-dashboard"):
        assert forbidden not in template
    assert template.count("certResolver: ${TRAEFIK_CERT_RESOLVER}") == 2


def test_image_contains_but_does_not_default_to_canary_template() -> None:
    dockerfile = (ROOT / "traefik/Dockerfile").read_text(encoding="utf-8")
    entrypoint = (ROOT / "traefik/entrypoint.sh").read_text(encoding="utf-8")
    assert "dynamic-canary.yml" in dockerfile
    assert 'TRAEFIK_CANARY_MODE:-false' in entrypoint
    assert "/etc/traefik/templates/dynamic-canary.yml.template" in entrypoint
    assert 'DYNAMIC_TEMPLATE_PATH="/etc/traefik/templates/dynamic.yml.template"' in entrypoint


def test_canary_mode_remains_staging_only() -> None:
    static = (ROOT / "traefik/traefik.yml").read_text(encoding="utf-8")
    entrypoint = (ROOT / "traefik/entrypoint.sh").read_text(encoding="utf-8")
    assert "acme-staging-v02.api.letsencrypt.org" in static
    assert "acme-staging.json" in static
    assert 'TRAEFIK_CERT_RESOLVER="le-staging"' in entrypoint


def test_real_compose_observer_has_explicit_canary_mode() -> None:
    observer = (ROOT / "scripts/bash/observe-compose-health.sh").read_text(
        encoding="utf-8"
    )
    assert "OBSERVE_TRAEFIK_CANARY_MODE" in observer
    assert "traefik-canary-single-host=verified" in observer
