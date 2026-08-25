import unittest
from pathlib import Path

from scripts.python.capacity_assurance import CapacityError, load_profile, run_capacity_drill


ROOT = Path(__file__).parents[2]


class CapacityAssuranceTests(unittest.TestCase):
    def test_documented_small_preview_profile_passes_all_pressure_drills(self):
        profile = load_profile(ROOT/'scripts/config/capacity-profiles.json','small-preview')
        result = run_capacity_drill(profile)
        self.assertEqual('passed', result['status'])
        self.assertEqual(1, result['queueRejected'])
        self.assertEqual(1, result['cacheLoads'])
        self.assertEqual(0, result['integrityErrors'])
        self.assertLessEqual(result['p95Milliseconds'], profile['p95Milliseconds'])
        self.assertLessEqual(result['peakMemoryBytes'], profile['maximumMemoryBytes'])

    def test_unknown_or_hostile_profile_fails_closed(self):
        with self.assertRaisesRegex(CapacityError, 'profile'):
            load_profile(ROOT/'scripts/config/capacity-profiles.json','missing')
        bad = load_profile(ROOT/'scripts/config/capacity-profiles.json','small-preview')
        bad['p95Milliseconds'] = -1
        with self.assertRaisesRegex(CapacityError, 'slo'):
            run_capacity_drill(bad)


if __name__ == '__main__':
    unittest.main()
