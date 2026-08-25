import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from digital_ocean.scripts.python.release_orchestrator import ReleaseController, ReleaseDenied, signed_release, verify_release


KEY = b'release-test-signing-key-material-32'


def release(number: int):
    digit = format(number, 'x')[-1]
    return signed_release(release_id=f'release-test-{number:04d}', image=f'registry.example/base2@sha256:{digit * 64}', source_commit=digit * 40, sbom_digest=digit * 64, provenance_digest=digit * 64, signing_key=KEY)


class ReleaseOrchestratorTests(unittest.TestCase):
    def test_mutable_tampered_and_unverified_images_fail_before_health_or_traffic(self):
        with self.assertRaisesRegex(ReleaseDenied, 'image_not_immutable'):
            signed_release(release_id='release-test-0001', image='registry.example/base2:latest', source_commit='a'*40, sbom_digest='a'*64, provenance_digest='a'*64, signing_key=KEY)
        item = release(1); item['image'] = item['image'].replace('1'*64, '2'*64)
        with self.assertRaisesRegex(ReleaseDenied, 'signature_invalid'):
            verify_release(item, signing_key=KEY)

    def test_health_gate_precedes_traffic_and_failure_rolls_back(self):
        with TemporaryDirectory() as temporary:
            controller = ReleaseController(Path(temporary)/'private/state.json', signing_key=KEY)
            first = controller.update(release(1), health_gate=lambda _: True)
            self.assertEqual('healthy', first['status'])
            failed = controller.update(release(2), health_gate=lambda _: False)
            self.assertEqual({'status':'rolled_back','current':'release-test-0001','trafficChanged':False}, failed)
            self.assertEqual('release-test-0001', controller.observe()['current'])

    def test_three_update_restore_cycles_and_exact_rollback(self):
        with TemporaryDirectory() as temporary:
            controller = ReleaseController(Path(temporary)/'private/state.json', signing_key=KEY)
            for number in (1,2,3):
                self.assertEqual('healthy', controller.update(release(number), health_gate=lambda _: True)['status'])
                self.assertEqual('idempotent', controller.update(release(number), health_gate=lambda _: (_ for _ in ()).throw(AssertionError('health replayed')))['status'])
            result = controller.rollback(expected_current='release-test-0003')
            self.assertEqual('release-test-0002', result['current'])
            with self.assertRaisesRegex(ReleaseDenied, 'target_mismatch'):
                controller.rollback(expected_current='release-test-0003')


if __name__ == '__main__':
    unittest.main()
