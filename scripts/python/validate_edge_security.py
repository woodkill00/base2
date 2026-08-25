#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def findings_for(*, dynamic: str, canary: str, nginx: str, api_main: str) -> list[str]:
    findings: list[str] = []
    required_dynamic = [
        "stsSeconds: 31536000",
        "stsIncludeSubdomains: true",
        "stsPreload: true",
        "frameDeny: true",
        "contentTypeNosniff: true",
        "referrerPolicy: 'strict-origin-when-cross-origin'",
        "Permissions-Policy: 'geolocation=(), microphone=(), camera=(), payment=(), usb=()'",
        "default-src 'self'",
        "frame-ancestors 'none'",
        "rateLimit:",
    ]
    for value in required_dynamic:
        if value not in dynamic:
            findings.append(f"dynamic_missing:{value}")
    frontend = dynamic.split('frontend-react:', 1)[1].split('swagger-docs:', 1)[0]
    for middleware in ('security-headers', 'security-csp', 'rate-limit'):
        if f'- {middleware}' not in frontend:
            findings.append(f'frontend_missing:{middleware}')
    required_canary = [
        'stsSeconds: 0',
        "X-Robots-Tag: 'noindex, nofollow, noarchive'",
        "default-src 'self'",
        "connect-src 'self'",
    ]
    for value in required_canary:
        if value not in canary:
            findings.append(f'canary_missing:{value}')
    required_nginx = [
        'default "no-store"',
        '"public, max-age=31536000, immutable"',
        'Cache-Control $base2_cache_control always',
        'Content-Security-Policy',
        'X-Frame-Options DENY always',
        'X-Content-Type-Options nosniff always',
        'Permissions-Policy',
    ]
    for value in required_nginx:
        if value not in nginx:
            findings.append(f'nginx_missing:{value}')
    if "if '*' in origins" not in api_main or 'allow_credentials = False' not in api_main:
        findings.append('cors_wildcard_credentials_not_blocked')
    return findings


def main() -> int:
    paths = {
        'dynamic': ROOT / 'traefik/dynamic.yml',
        'canary': ROOT / 'traefik/dynamic-canary.yml',
        'nginx': ROOT / 'react-app/nginx/default.conf',
        'api_main': ROOT / 'api/main.py',
    }
    findings = findings_for(**{key: path.read_text(encoding='utf-8') for key, path in paths.items()})
    if findings:
        print('\n'.join(findings))
        return 1
    print('Edge security policy: PASS')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
