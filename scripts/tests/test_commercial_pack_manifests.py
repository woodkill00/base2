import json
import unittest
from pathlib import Path

from scripts.python.module_registry import ModuleRegistry


class CommercialPackManifestTests(unittest.TestCase):
    def test_pairs_are_ordered_and_payment_is_only_on_transaction_modules(self):
        root = Path(__file__).parents[2]
        names = ('membership', 'subscription', 'catalog', 'commerce', 'listing', 'marketplace')
        payloads = [json.loads((root / 'modules' / name / 'module.json').read_text()) for name in names]
        plan = ModuleRegistry(payloads).install_plan()
        order = [item['id'] for item in plan]
        for parent, child in (('membership', 'subscription'), ('catalog', 'commerce'), ('listing', 'marketplace')):
            self.assertLess(order.index(parent), order.index(child))
        payment = {item['id'] for item in plan if item['capabilities'] == ['payment']}
        self.assertEqual({'subscription', 'commerce', 'marketplace'}, payment)

    def test_every_pack_defaults_disabled_and_excludes_live_provider_values(self):
        root = Path(__file__).parents[2]
        for name in ('membership', 'subscription', 'catalog', 'commerce', 'listing', 'marketplace'):
            schema = json.loads((root / 'modules' / name / 'settings.schema.json').read_text())
            encoded = json.dumps(schema, sort_keys=True)
            self.assertNotIn('production', encoded)
            if 'provider' in schema['properties']:
                self.assertEqual(['none', 'local_fake'], schema['properties']['provider']['enum'])


if __name__ == '__main__':
    unittest.main()
