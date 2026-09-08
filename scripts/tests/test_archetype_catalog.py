import json
from pathlib import Path

from api.services.extension_platform import ARCHETYPES, archetype_contract

ROOT = Path(__file__).resolve().parents[2]


def test_all_archetypes_bind_modules_routes_roles_journeys_visual_capacity_and_cost():
    value = json.loads((ROOT / 'shared/config/archetypes-v1.json').read_text())
    assert value['schemaVersion'] == 1
    assert {item['id'] for item in value['archetypes']} == ARCHETYPES
    for item in value['archetypes']:
        assert item['modules'] and item['routes'] and item['roles'] and item['journeys']
        assert item['visualProfile'] and item['capacity']
        assert archetype_contract(
            item['id'], modules=item['modules'],
            provider_cost_ceiling=item['maximumMonthlyProviderCostUsd'],
        )['routesDeclared']
