from pathlib import Path
from unittest import TestCase

from scripts.python.validate_edge_security import ROOT, findings_for


def current():
    return {
        'dynamic': (ROOT / 'traefik/dynamic.yml').read_text(),
        'canary': (ROOT / 'traefik/dynamic-canary.yml').read_text(),
        'nginx': (ROOT / 'react-app/nginx/default.conf').read_text(),
        'api_main': (ROOT / 'api/main.py').read_text(),
    }


class EdgeSecurityPolicyTests(TestCase):
    def test_current_policy_is_complete(self):
        self.assertEqual(findings_for(**current()), [])

    def test_mutations_fail_closed(self):
        values = current()
        values['canary'] = values['canary'].replace('noindex, nofollow, noarchive', 'index')
        values['dynamic'] = values['dynamic'].replace('stsSeconds: 31536000', 'stsSeconds: 0')
        values['nginx'] = values['nginx'].replace('X-Frame-Options DENY always', '')
        findings = findings_for(**values)
        self.assertTrue(any(item.startswith('canary_missing:') for item in findings))
        self.assertTrue(any(item.startswith('dynamic_missing:') for item in findings))
        self.assertTrue(any(item.startswith('nginx_missing:') for item in findings))
