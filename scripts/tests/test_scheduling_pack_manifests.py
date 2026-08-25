import json, unittest
from pathlib import Path
from scripts.python.module_registry import ModuleRegistry

class SchedulingPackTests(unittest.TestCase):
    def test_events_precede_booking_and_only_booking_declares_email(self):
        root=Path(__file__).parents[2]
        items=[json.loads((root/f'modules/{name}/module.json').read_text()) for name in ('booking','events')]
        plan=ModuleRegistry(items).install_plan()
        self.assertEqual(['events','booking'],[item['id'] for item in plan])
        self.assertEqual([[],['email']],[item['capabilities'] for item in plan])

if __name__ == '__main__': unittest.main()
