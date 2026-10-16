from pathlib import Path
import os
import subprocess
from unittest import TestCase

from scripts.python.validate_edge_security import ROOT, findings_for


def current():
    return {
        "dynamic": (ROOT / "traefik/dynamic.yml").read_text(),
        "canary": (ROOT / "traefik/dynamic-canary.yml").read_text(),
        "static": (ROOT / "traefik/traefik.yml").read_text(),
        "nginx": (ROOT / "react-app/nginx/default.conf").read_text(),
        "api_main": (ROOT / "api/main.py").read_text(),
    }


class EdgeSecurityPolicyTests(TestCase):
    def test_google_style_policy_is_fixed_opt_in_and_cannot_be_injected(self):
        entrypoint = (ROOT / 'traefik/entrypoint.sh').read_text()
        block = entrypoint.split('# BEGIN GOOGLE STYLE POLICY\n')[1].split('# END GOOGLE STYLE POLICY')[0]
        for flag in ('true', 'false', '', 'true; evil', 'https://evil.test'):
            result = subprocess.run(
                ['sh', '-c', block + '\nprintf "%s|%s" "$GOOGLE_CSP_STYLE_SOURCE" "$GOOGLE_PUBLIC_REFERRER_POLICY"'],
                env={**os.environ, 'GOOGLE_OAUTH_ENABLED': flag, 'GOOGLE_CSP_STYLE_SOURCE': 'https://evil.test'},
                text=True, capture_output=True,
            )
            if flag in ('true', 'false', ''):
                self.assertEqual(result.returncode, 0)
                self.assertEqual(result.stdout, ' https://accounts.google.com/gsi/style|strict-origin-when-cross-origin' if flag == 'true' else '|no-referrer')
            else:
                self.assertEqual(result.returncode, 78)
            self.assertNotIn('evil.test', result.stdout)
        for template in ('dynamic.yml', 'dynamic-full-preview.yml'):
            self.assertEqual((ROOT / 'traefik' / template).read_text().count('${GOOGLE_CSP_STYLE_SOURCE}'), 1)
        self.assertNotIn('GOOGLE_CSP_STYLE_SOURCE', (ROOT / 'traefik/dynamic-canary.yml').read_text())
        preview = (ROOT / 'traefik/dynamic-full-preview.yml').read_text()
        self.assertEqual(preview.count('${GOOGLE_PUBLIC_REFERRER_POLICY}'), 1)
        self.assertIn('referrerPolicy: same-origin', preview)
        for compose in ('local.docker.yml', 'development.docker.yml'):
            source = (ROOT / compose).read_text().split('  traefik:\n')[1].split('\n  postgres:')[0]
            self.assertIn('GOOGLE_OAUTH_ENABLED=${GOOGLE_OAUTH_ENABLED:-false}', source)

    def test_current_policy_is_complete(self):
        self.assertEqual(findings_for(**current()), [])

    def test_mutations_fail_closed(self):
        values = current()
        values["canary"] = values["canary"].replace("noindex, nofollow, noarchive", "index")
        values["dynamic"] = values["dynamic"].replace("stsSeconds: 31536000", "stsSeconds: 0")
        values["dynamic"] = values["dynamic"].replace(
            "        - security-csp-swagger\n        - traefik-basic-auth",
            "        - security-csp-swagger",
        )
        values["nginx"] = values["nginx"].replace("X-Frame-Options DENY always", "")
        values["static"] = values["static"].replace("insecure: false", "insecure: true")
        findings = findings_for(**values)
        self.assertTrue(any(item.startswith("canary_missing:") for item in findings))
        self.assertTrue(any(item.startswith("dynamic_missing:") for item in findings))
        self.assertIn("swagger_auth_policy_incomplete", findings)
        self.assertTrue(any(item.startswith("nginx_missing:") for item in findings))
        self.assertTrue(any(item.startswith("static_missing:") for item in findings))
