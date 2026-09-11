import importlib.util
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('layout_plan', ROOT / 'validate_plan.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class PlanValidationTests(unittest.TestCase):
    def test_current_plan(self):
        self.assertEqual(module.validate()['tasks'], 28)

    def check_rejected(self, filename, before, after, expected):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / 'plan'
            shutil.copytree(ROOT, target, ignore=shutil.ignore_patterns('__pycache__'))
            path = target / filename
            self.assertIn(before, path.read_text())
            path.write_text(path.read_text().replace(before, after, 1))
            with self.assertRaisesRegex(ValueError, expected):
                module.validate(target)

    def test_future_dependency(self):
        self.check_rejected('tasks.md', '(depends: T001)', '(depends: T028)', 'invalid predecessor')

    def test_duplicate_id(self):
        self.check_rejected('tasks.md', '] T002 [', '] T001 [', 'task sequence')

    def test_false_completion(self):
        self.check_rejected('tasks.md', '- [ ] T001', '- [x] T001', 'cannot claim completion')

    def test_missing_coverage(self):
        self.check_rejected('traceability.md', 'T026, T027, T028', 'T026, T027', 'traceability mismatch')


if __name__ == '__main__':
    unittest.main()
