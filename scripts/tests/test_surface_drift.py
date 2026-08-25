import json
from pathlib import Path
import tempfile
import unittest

from scripts.python.validate_surface_drift import DriftError, GROUPS, inventory, validate


class SurfaceDriftTests(unittest.TestCase):
    def _fixture(self, root: Path) -> Path:
        for patterns in GROUPS.values():
            pattern = patterns[0]
            path = root / pattern
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(pattern + "\n", encoding="utf-8")
        lock = root / "lock.json"
        lock.write_text(json.dumps(inventory(root)), encoding="utf-8")
        return lock

    def test_exact_inventory_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = validate(root, self._fixture(root))
            self.assertEqual("passed", result["status"])
            self.assertEqual(set(GROUPS), set(inventory(root)["groups"]))

    def test_each_stale_surface_fails_with_diagnostic(self):
        for group, patterns in GROUPS.items():
            with self.subTest(group=group), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                lock = self._fixture(root)
                path = root / patterns[0]
                path.write_text("stale\n", encoding="utf-8")
                with self.assertRaisesRegex(DriftError, rf"{group}:stale:"):
                    validate(root, lock)

    def test_new_and_missing_artifacts_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lock = self._fixture(root)
            new_route = root / "api/routes/new.py"
            new_route.parent.mkdir(parents=True, exist_ok=True)
            new_route.write_text("route\n", encoding="utf-8")
            with self.assertRaisesRegex(DriftError, "routeInventory:unlocked"):
                validate(root, lock)
            new_route.unlink()
            (root / GROUPS["docs"][0]).unlink()
            with self.assertRaisesRegex(DriftError, "docs:(?:missing|empty_inventory)"):
                validate(root, lock)


if __name__ == "__main__":
    unittest.main()
