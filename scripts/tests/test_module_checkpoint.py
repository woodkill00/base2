import unittest

from scripts.python.run_module_checkpoint import run


class ModuleCheckpointTests(unittest.TestCase):
    def test_every_module_completes_every_nondestructive_lifecycle(self):
        result = run()
        self.assertEqual('passed', result['status'])
        self.assertGreaterEqual(result['moduleCount'], 18)
        self.assertEqual(
            {result['moduleCount']}, set(result['lifecycleCounts'].values())
        )
        self.assertEqual(0, result['credentialReads'])
        self.assertEqual(0, result['networkCalls'])
        self.assertFalse(result['persistentStateRetained'])


if __name__ == '__main__':
    unittest.main()
