"""Fail-closed contracts for the source-bound media interpreter migration."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class MediaPythonRuntimeTests(unittest.TestCase):
    def test_fixed_official_runtime_and_truthful_inventory(self):
        lock = json.loads((ROOT / 'api/media-inspector-runtime.lock.json').read_text())
        dockerfile = (ROOT / 'api/Dockerfile.media-inspector').read_text()
        self.assertEqual('3.15.2', lock['pythonVersion'])
        self.assertEqual('linux/amd64', lock['platform'])
        self.assertEqual('8b5536d280142ecf6cdfe15d12a21ba1c65e300bbf7b28a8d0cdb849575797de', lock['source']['sha256'])
        for role in ('builder', 'downloads'):
            self.assertRegex(lock['images'][role]['reference'], r'@sha256:[a-f0-9]{64}$')
            self.assertIn(lock['images'][role]['reference'], dockerfile)
        self.assertIn('FROM scratch AS media-inspector-production', dockerfile)
        self.assertNotIn('cgr.dev/chainguard/python', dockerfile)
        self.assertNotIn('privilege-runtime', dockerfile)
        self.assertIn(lock['source']['url'], dockerfile)
        self.assertIn(lock['source']['sha256'], dockerfile)
        self.assertIn('ln -s /usr/local/bin/python3.15 /runtime-root/usr/bin/python', dockerfile)
        self.assertNotIn('/var/lib/dpkg/status', dockerfile)
        self.assertIn('scanner-bom', dockerfile)
        self.assertIn('python-files', dockerfile)
        self.assertIn('--without-ensurepip', dockerfile)
        self.assertIn('chmod a-s', dockerfile)
        self.assertIn('/python-root/usr/local/lib/python3.15/ensurepip', dockerfile)
        self.assertIn('apk --keys-dir /locked-keys verify /locked-inputs/repository/x86_64/APKINDEX.tar.gz', dockerfile)
        self.assertIn('sha256sum -c /locked-inputs/key.sha256', dockerfile)
        self.assertNotIn('--allow-untrusted', dockerfile)
        self.assertEqual(4, dockerfile.count('--keys-dir /locked-keys'))
        self.assertIn('cp /etc/apk/keys/wolfi-signing.rsa.pub /locked-keys/wolfi-signing.rsa.pub', dockerfile)
        self.assertIn('--repositories-file /dev/null --repository /locked-inputs/repository', dockerfile)
        self.assertIn('--no-network --no-cache', dockerfile)
        for role in ('build', 'runtime'):
            self.assertIn(f'cmp /{role}-expected.txt /{role}-actual.txt', dockerfile)
        production = dockerfile.split('AS media-inspector-production', 1)[1]
        self.assertNotIn('/locked-inputs /', production)
        self.assertNotIn('/repository/ /', production)

    def test_final_runtime_runs_upstream_ssl_and_import_checks_without_shipping_tests(self):
        dockerfile = (ROOT / 'api/Dockerfile.media-inspector').read_text()
        self.assertIn('source=/tmp/python-source/Lib/test,target=/tmp/cpython-tests/test', dockerfile)
        self.assertIn('source=tests/media_inspector_runtime_acceptance.py', dockerfile)
        production = dockerfile.split('AS media-inspector-production', 1)[1].split('AS media-inspector-acceptance', 1)[0]
        self.assertIn('["/usr/bin/python", "/tmp/runtime_acceptance.py", "--audit-elevated-files"]', production)
        self.assertLess(production.rfind('\nCOPY '), production.index('--audit-elevated-files'))
        self.assertIn('["/usr/bin/setpriv", "--reuid=65534", "--regid=65534", "--clear-groups"', production)
        self.assertIn('"--no-new-privs", "--inh-caps=-all", "--ambient-caps=-all", "--bounding-set=-all"', production)
        self.assertIn('"--runtime-user", "65534", "--cpython-tests", "/tmp/cpython-tests"', production)
        self.assertLess(production.index('--runtime-user'), production.index('--audit-elevated-files'))
        self.assertNotRegex(production.split('--audit-elevated-files', 1)[1], r'(?im)^\s*(RUN|COPY|ADD|WORKDIR|ONBUILD)\b')
        acceptance = dockerfile.split('AS media-inspector-acceptance', 1)[1].split('FROM media-inspector-production AS media-inspector-final', 1)[0]
        copies = [line for line in acceptance.splitlines() if line.startswith('COPY ')]
        self.assertEqual(3, len(copies))
        self.assertTrue(all('--chmod=0644' in line for line in copies))
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
        runtime_step = workflow.split('name: Verify final Python runtime and binary wheel imports', 1)[1].split('      - name:', 1)[0]
        self.assertIn('--user 65534:65534', runtime_step)
        self.assertIn('/tmp/runtime_acceptance.py --runtime-user 65534', runtime_step)
        self.assertNotIn('--cap-add', runtime_step)
        self.assertEqual(2, workflow.count('severity-cutoff: high'))
        self.assertEqual(2, workflow.count('fail-build: true'))
        self.assertIn('config: api/media-inspector-syft.yaml', workflow)
        self.assertIn('media-inspector-sbom.raw.cdx.json media-inspector-clamav.bom.json', workflow)
        config = (ROOT / 'api/media-inspector-syft.yaml').read_text()
        self.assertIn('  - +sbom-cataloger', config)
        self.assertNotIn('  - -', config)
        self.assertIn('media_inspector_two_uid_container_acceptance.sh', workflow)
        self.assertIn('clamav_updater_container_acceptance.sh', workflow)


if __name__ == '__main__':
    unittest.main()
