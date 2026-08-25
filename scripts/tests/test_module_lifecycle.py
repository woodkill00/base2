import copy
import tempfile
import unittest
from pathlib import Path

from scripts.python.module_lifecycle import ModuleLifecycle, ModuleLifecycleError
from scripts.tests.test_module_registry import manifest


class ModuleLifecycleTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / 'private' / 'modules.json'
        self.lifecycle = ModuleLifecycle(self.path, receipt_key=b'x' * 32)

    def test_install_disable_enable_export_and_job_policy(self):
        item = manifest('blog')
        self.lifecycle.apply(operation_id='install-1', action='install', manifest_payload=item)
        self.assertTrue(self.lifecycle.status()['blog']['jobsScheduled'])
        self.lifecycle.apply(operation_id='disable-1', action='disable', manifest_payload=item)
        self.assertEqual('disabled', self.lifecycle.status()['blog']['status'])
        self.assertFalse(self.lifecycle.status()['blog']['jobsScheduled'])
        self.lifecycle.apply(operation_id='enable-1', action='enable', manifest_payload=item)
        self.assertEqual('1.2.3', self.lifecycle.export_inventory('blog')['version'])
        self.assertEqual(0o600, self.path.stat().st_mode & 0o777)

    def test_exact_replay_is_idempotent_and_changed_replay_fails(self):
        item = manifest()
        first = self.lifecycle.apply(operation_id='same', action='install', manifest_payload=item)
        self.assertEqual(first, self.lifecycle.apply(operation_id='same', action='install', manifest_payload=item))
        changed = copy.deepcopy(item)
        changed['version'] = '1.2.4'
        with self.assertRaisesRegex(ModuleLifecycleError, 'request_mismatch'):
            self.lifecycle.apply(operation_id='same', action='upgrade', manifest_payload=changed)

    def test_upgrade_requires_newer_version_and_preserves_disabled_jobs(self):
        item = manifest('blog')
        self.lifecycle.apply(operation_id='i', action='install', manifest_payload=item)
        self.lifecycle.apply(operation_id='d', action='disable', manifest_payload=item)
        newer = manifest(
            'blog', version='1.3.0',
            migrations=['modules/blog/migrations/0001.sql', 'modules/blog/migrations/0002.sql'],
        )
        preview = self.lifecycle.upgrade_preview(newer)
        self.assertEqual(['modules/blog/migrations/0002.sql'], preview['addedMigrations'])
        self.lifecycle.apply(operation_id='u', action='upgrade', manifest_payload=newer)
        state = self.lifecycle.status()['blog']
        self.assertEqual('1.3.0', state['version'])
        self.assertFalse(state['jobsScheduled'])
        with self.assertRaisesRegex(ModuleLifecycleError, 'not_newer'):
            self.lifecycle.apply(operation_id='old', action='upgrade', manifest_payload=item)

    def test_removal_obeys_persistent_data_policy(self):
        item = manifest('blog')
        self.lifecycle.apply(operation_id='i', action='install', manifest_payload=item)
        with self.assertRaisesRegex(ModuleLifecycleError, 'backup_required'):
            self.lifecycle.apply(operation_id='r1', action='remove', manifest_payload=item)
        self.lifecycle.apply(
            operation_id='r2', action='remove', manifest_payload=item, backup_receipt='backup-sha256'
        )
        self.assertEqual({}, self.lifecycle.status())

    def test_unsupported_transition_and_corrupt_state_fail_closed(self):
        with self.assertRaisesRegex(ModuleLifecycleError, 'unsupported'):
            self.lifecycle.apply(operation_id='x', action='execute', manifest_payload=manifest())
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text('{bad', encoding='utf-8')
        with self.assertRaisesRegex(ModuleLifecycleError, 'unreadable'):
            self.lifecycle.status()

    def test_rollback_rejects_tampering_then_exactly_restores_and_replays(self):
        first = self.lifecycle.apply(operation_id='i', action='install', manifest_payload=manifest())
        tampered = dict(first, afterDigest='0' * 64)
        with self.assertRaisesRegex(ModuleLifecycleError, 'not_exact'):
            self.lifecycle.rollback(operation_id='i', receipt=tampered)
        rollback = self.lifecycle.rollback(operation_id='i', receipt=first)
        self.assertEqual({}, self.lifecycle.status())
        self.assertEqual(rollback, self.lifecycle.rollback(operation_id='i', receipt=first))

    def test_admin_overview_is_sanitized_and_stable(self):
        self.lifecycle.apply(operation_id='i', action='install', manifest_payload=manifest('blog'))
        self.assertEqual(
            [{
                'id': 'blog', 'version': '1.2.3', 'status': 'enabled',
                'jobsScheduled': True, 'dataState': 'preserved',
                'healthChecks': ['blog.ready'], 'providerCapabilities': [],
            }],
            self.lifecycle.admin_overview(),
        )


if __name__ == '__main__':
    unittest.main()
