import json
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from digital_ocean.scripts.python.preview_state import authorize_destructive_transition
from scripts.python.recovery_assurance import RecoveryDenied, certificate_drill, create_backup, migration_preflight, preview_snapshot, restore_isolated


class RecoveryAssuranceTests(unittest.TestCase):
    def setUp(self):
        self.key = b'k' * 32
        self.key_ref = 'vaultwarden://base2/backup-key'
        self.now = datetime(2026, 8, 25, 12, tzinfo=UTC)

    def test_encrypted_backup_isolated_restore_and_no_secret_exposure(self):
        with TemporaryDirectory() as temporary:
            backup, restored = Path(temporary) / 'backup.enc', Path(temporary) / 'isolated' / 'data.bin'
            receipt = create_backup(payload=b'exact approved state', target_id='preview-001', data_schema=4, key=self.key, key_ref=self.key_ref, output=backup, now=self.now)
            encoded = backup.read_text()
            self.assertNotIn('exact approved state', encoded)
            self.assertNotIn(self.key.decode(), encoded)
            result = restore_isolated(backup=backup, key=self.key, expected_target='preview-001', expected_schema=4, output=restored)
            self.assertEqual(receipt['plaintextSha256'], result['sha256'])
            self.assertEqual(b'exact approved state', restored.read_bytes())
            self.assertEqual(0o600, backup.stat().st_mode & 0o777)

    def test_corruption_wrong_target_schema_partial_and_live_restore_fail_closed(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary); backup = root / 'backup.enc'
            create_backup(payload=b'state', target_id='preview-001', data_schema=4, key=self.key, key_ref=self.key_ref, output=backup, now=self.now)
            for target, schema, error in [('wrong-target', 4, 'wrong_target'), ('preview-001', 3, 'schema_mismatch')]:
                with self.assertRaisesRegex(RecoveryDenied, error):
                    restore_isolated(backup=backup, key=self.key, expected_target=target, expected_schema=schema, output=root / f'{target}-{schema}')
            payload = json.loads(backup.read_text()); payload['ciphertext'] = payload['ciphertext'][:-4] + 'AAAA'; backup.write_text(json.dumps(payload))
            with self.assertRaisesRegex(RecoveryDenied, 'integrity_failed'):
                restore_isolated(backup=backup, key=self.key, expected_target='preview-001', expected_schema=4, output=root / 'corrupt')
            backup.write_text('{partial')
            with self.assertRaisesRegex(RecoveryDenied, 'backup_invalid'):
                restore_isolated(backup=backup, key=self.key, expected_target='preview-001', expected_schema=4, output=root / 'partial')
            (root / 'existing').write_text('live')
            with self.assertRaisesRegex(RecoveryDenied, 'must_be_absent'):
                restore_isolated(backup=backup, key=self.key, expected_target='preview-001', expected_schema=4, output=root / 'existing')

    def test_migration_rollback_and_certificate_preflight(self):
        self.assertTrue(migration_preflight(current_schema=4, target_schema=5, backup_schema=4)['allowed'])
        with self.assertRaisesRegex(RecoveryDenied, 'downgrade'):
            migration_preflight(current_schema=4, target_schema=3, backup_schema=4)
        with self.assertRaisesRegex(RecoveryDenied, 'backup_stale'):
            migration_preflight(current_schema=4, target_schema=5, backup_schema=3)
        self.assertTrue(certificate_drill(acme_mode='staging', days_remaining=20)['renewalRequired'])
        with self.assertRaisesRegex(RecoveryDenied, 'production_forbidden'):
            certificate_drill(acme_mode='production', days_remaining=20)

    def test_preview_snapshot_authorizes_destroy_then_exact_recreation(self):
        with TemporaryDirectory() as temporary:
            backup = Path(temporary) / 'preview.enc'
            expiry = self.now + timedelta(hours=1)
            receipt = preview_snapshot(lease_id='preview-001', payload=b'approved state', key=self.key, key_ref=self.key_ref, output=backup, verified_at=self.now, expires_at=expiry)
            declaration = {'schemaVersion':1,'leaseId':'preview-001','classification':'restore-required','retentionExpiresAt':expiry.isoformat().replace('+00:00','Z'),'encryptionKeyRef':self.key_ref}
            policy_receipt = {key: receipt[key] for key in ('schemaVersion','leaseId','status','sha256','size','encrypted','keyRef','verifiedAt','retentionExpiresAt')}
            authority = authorize_destructive_transition(declaration, policy_receipt, now=self.now + timedelta(minutes=1))
            self.assertTrue(authority['requiresRestore'])
            restored = Path(temporary) / 'recreated' / 'state'
            restore_isolated(backup=backup, key=self.key, expected_target='preview-001', expected_schema=1, output=restored)
            self.assertEqual(b'approved state', restored.read_bytes())


if __name__ == '__main__':
    unittest.main()
