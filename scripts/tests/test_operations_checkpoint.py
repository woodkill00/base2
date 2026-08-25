import unittest
from scripts.python.run_operations_checkpoint import run


class OperationsCheckpointTests(unittest.TestCase):
    def test_three_cycles_capacity_alert_recovery_and_cleanup(self):
        result=run()
        self.assertEqual('passed',result['status'])
        self.assertEqual(3,result['faultRestoreCycles'])
        self.assertEqual(['healthy']*3,result['releaseStates'])
        self.assertEqual(2,result['incidentNotifications'])
        self.assertEqual(0,result['providerCalls'])
        self.assertEqual(0,result['ownedResourcesAfter'])
        self.assertFalse(result['temporaryStateRetained'])


if __name__=='__main__': unittest.main()
