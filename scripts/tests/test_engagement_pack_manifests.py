import json,unittest
from pathlib import Path
from scripts.python.module_registry import ModuleRegistry
class EngagementPackTests(unittest.TestCase):
    def test_dependencies_and_inert_email(self):
        root=Path(__file__).parents[2]
        names=('community','support','content','forms')
        plan=ModuleRegistry([json.loads((root/f'modules/{n}/module.json').read_text()) for n in names]).install_plan()
        ids=[item['id'] for item in plan]
        self.assertLess(ids.index('content'),ids.index('community'))
        self.assertLess(ids.index('forms'),ids.index('support'))
        self.assertEqual(['email'],next(item for item in plan if item['id']=='support')['capabilities'])
if __name__=='__main__':unittest.main()
