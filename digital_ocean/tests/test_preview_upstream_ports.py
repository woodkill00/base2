from pathlib import Path
from string import Template
from urllib.parse import urlsplit

import yaml


def test_preview_upstreams_use_application_ports_from_compose_environment():
    root = Path(__file__).resolve().parents[2]
    compose = yaml.safe_load((root / 'development.docker.yml').read_text())
    # Non-default ports prove these are propagated, rather than hardcoded.
    inputs = {'FASTAPI_PORT': '8123', 'DJANGO_PORT': '8456'}
    environment = {}
    for entry in compose['services']['traefik']['environment']:
        key, value = entry.split('=', 1)
        if key in inputs:
            environment[key] = Template(value).substitute(inputs)
    template = (root / 'traefik/dynamic-full-preview.yml').read_text()
    for key, value in {'TRAEFIK_CERT_RESOLVER': 'le-staging', 'OWNER_ALLOWLIST_CSV': '127.0.0.1/32'}.items():
        template = template.replace('${' + key + '}', value)
    routes = yaml.safe_load(template)
    for service, port_key in [('api', 'FASTAPI_PORT'), ('django', 'DJANGO_PORT')]:
        upstream = routes['http']['services'][service]['loadBalancer']['servers'][0]['url']
        rendered = Template(upstream).substitute(environment)
        assert urlsplit(rendered).hostname == service
        assert urlsplit(rendered).port == int(inputs[port_key])
