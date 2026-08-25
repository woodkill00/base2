import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class IdentityRealmContractTests(unittest.TestCase):
    def setUp(self):
        self.contract = json.loads(
            (ROOT / 'shared/config/identity-realms.json').read_text(encoding='utf-8')
        )

    def test_realms_are_distinct_and_surface_allowlists_do_not_overlap(self):
        self.assertEqual(self.contract['schemaVersion'], 1)
        public = self.contract['realms']['publicAccount']
        operator = self.contract['realms']['operatorCms']
        self.assertNotEqual(public['authority'], operator['authority'])
        self.assertEqual(set(public['allowedSurfaces']), set(operator['forbiddenSurfaces']))
        self.assertEqual(set(operator['allowedSurfaces']), set(public['forbiddenSurfaces']))
        self.assertNotEqual(set(public['sessionTypes']), set(operator['sessionTypes']))

    def test_mutable_identity_joins_and_token_authority_are_forbidden(self):
        mapping = self.contract['crossRealmMapping']
        self.assertEqual(mapping['mode'], 'none')
        self.assertGreaterEqual(
            set(mapping['forbiddenJoinKeys']), {'email', 'display_name', 'username'}
        )
        authz = self.contract['authorization']
        self.assertEqual(authz['permissionSource'], 'server-side-active-membership')
        self.assertEqual(authz['unknownRole'], 'deny')
        self.assertGreaterEqual(
            set(authz['untrustedTokenClaims']), {'tenant_id', 'organization_id', 'role', 'permissions'}
        )

    def test_future_mapping_has_activation_and_rollback_requirements(self):
        requirements = set(self.contract['crossRealmMapping']['futureMappingRequires'])
        self.assertGreaterEqual(
            requirements,
            {
                'immutable-link-table',
                'explicit-account-link-proof',
                'two-realm-revocation-tests',
                'migration-and-rollback-plan',
            },
        )


if __name__ == '__main__':
    unittest.main()
