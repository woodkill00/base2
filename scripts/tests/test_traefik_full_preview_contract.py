from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]

def test_full_preview_has_only_expected_public_ports_and_staging_resolver():
    compose = (ROOT / "development.docker.yml").read_text()
    traefik = (ROOT / "traefik/dynamic-full-preview.yml").read_text()
    static = (ROOT / "traefik/traefik.yml").read_text()
    assert "'80:80'" in compose and "'443:443'" in compose
    assert "8080:8080" not in compose and "5555:5555" not in compose
    assert "acme-staging-v02.api.letsencrypt.org" in static
    assert "acme-v02.api.letsencrypt.org/directory" not in static
    assert "owner-allow-ip" in traefik and "operator-basic-auth" in traefik

def test_every_operator_router_has_both_edge_guards():
    text = (ROOT / "traefik/dynamic-full-preview.yml").read_text()
    for router in ("django-admin:", "django-static:", "swagger:", "traefik-dashboard:", "pgadmin:", "flower:"):
        section = re.split(r"\n    \S", text.split(f"    {router}", 1)[1], maxsplit=1)[0]
        assert "owner-allow-ip" in section
        assert "operator-basic-auth" in section

def test_full_preview_is_noindex_no_store_and_has_no_hsts():
    text = (ROOT / "traefik/dynamic-full-preview.yml").read_text()
    assert text.count("stsSeconds: 0") >= 3
    assert text.count("noindex, nofollow, noarchive") >= 3
    assert text.count("Cache-Control: 'no-store'") >= 2


def test_public_preview_csp_allows_only_the_google_identity_origins_it_loads():
    text = (ROOT / "traefik/dynamic-full-preview.yml").read_text()
    public_headers = text.split("preview-public-security:", 1)[1].split("preview-operator-security:", 1)[0]
    assert "script-src 'self' https://accounts.google.com https://apis.google.com" in public_headers
    assert "connect-src 'self' https://accounts.google.com https://oauth2.googleapis.com https://www.googleapis.com" in public_headers
    assert "frame-src https://accounts.google.com" in public_headers
    assert "script-src *" not in public_headers and "connect-src *" not in public_headers
