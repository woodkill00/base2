"""Fail-closed contracts for the source-bound media interpreter migration."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]


class MediaPythonRuntimeTests(unittest.TestCase):
    def test_fixed_official_runtime_and_truthful_inventory(self):
        lock = json.loads((ROOT / 'api/media-inspector-runtime.lock.json').read_text())
        dockerfile = (ROOT / 'api/Dockerfile.media-inspector').read_text()
        self.assertEqual('3.15.2', lock['pythonVersion'])
        self.assertEqual('linux/amd64', lock['platform'])
        self.assertEqual('8b5536d280142ecf6cdfe15d12a21ba1c65e300bbf7b28a8d0cdb849575797de', lock['source']['sha256'])
        for role in ('builder', 'runtime'):
            self.assertRegex(lock['images'][role]['reference'], r'^python@sha256:[a-f0-9]{64}$')
            self.assertIn(lock['images'][role]['reference'], dockerfile)
        self.assertNotIn('cgr.dev/chainguard/python', dockerfile)
        self.assertNotIn('privilege-runtime', dockerfile)
        self.assertIn(lock['source']['url'], dockerfile)
        self.assertIn(lock['source']['sha256'], dockerfile)
        self.assertIn('ln -s /usr/local/bin/python3.15 /usr/bin/python', dockerfile)
        self.assertNotIn('/tmp/clamav/control /var/lib/dpkg/status', dockerfile)
        self.assertIn('>> /var/lib/dpkg/status', dockerfile)
        self.assertIn('/var/lib/dpkg/info/clamav.list', dockerfile)
        self.assertIn('python -m pip uninstall --yes pip', dockerfile)
        self.assertIn('chmod a-s', dockerfile)
        self.assertIn('rm -rf /usr/local/lib/python3.15/ensurepip', dockerfile)
        self.assertIn('rm -f /usr/local/bin/pip', dockerfile)

    def test_final_runtime_runs_upstream_ssl_and_import_checks_without_shipping_tests(self):
        dockerfile = (ROOT / 'api/Dockerfile.media-inspector').read_text()
        self.assertIn('source=/tmp/python-source/Lib/test,target=/tmp/cpython-tests/test', dockerfile)
        self.assertIn('source=tests/media_inspector_runtime_acceptance.py', dockerfile)
        production = dockerfile.split('AS media-inspector-production', 1)[1].split('AS media-inspector-acceptance', 1)[0]
        self.assertIn('/usr/bin/python /tmp/runtime_acceptance.py', production)
        self.assertNotIn('COPY tests/', production)
        source = (ROOT / 'api/tests/media_inspector_runtime_acceptance.py').read_text()
        self.assertIn('test.test_ssl.SSLObjectTests.test_distrusted_spki', source)
        self.assertIn('test.test_ssl.SSLObjectTests.test_unwrap', source)
        self.assertIn('result.skipped', source)
        self.assertIn('Ed25519PrivateKey', source)
        self.assertIn('PIL', source)
        self.assertIn('_cffi_backend', source)

    def test_ci_keeps_full_inventory_and_high_critical_gate(self):
        workflow = (ROOT / '.github/workflows/security.yml').read_text()
        self.assertIn('api/tests/media_inspector_sbom_acceptance.py media-inspector-sbom.cdx.json', workflow)
        self.assertEqual(2, workflow.count('severity-cutoff: high'))
        self.assertEqual(2, workflow.count('fail-build: true'))
        self.assertIn('media_inspector_two_uid_container_acceptance.sh', workflow)
        self.assertIn('clamav_updater_container_acceptance.sh', workflow)


if __name__ == '__main__':
    unittest.main()
