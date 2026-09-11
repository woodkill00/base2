"""Render historical migration states without a database or shared-registry mutation."""

from django.apps import apps
from django.db.migrations.loader import MigrationLoader


def _registry_identity():
    return tuple(
        (
            config.label,
            id(config.models),
            tuple(sorted((key, id(value)) for key, value in config.models.items())),
        )
        for config in apps.get_app_configs()
    )


def test_historical_migration_rendering_preserves_global_registry():
    before = _registry_identity()
    loader = MigrationLoader(None, ignore_no_migrations=True)
    nodes = dict.fromkeys(
        node for leaf in loader.graph.leaf_nodes() for node in loader.graph.forwards_plan(leaf)
    )
    assert nodes, "migration_graph_empty"
    for node in nodes:
        rendered = loader.project_state([node]).apps
        for config in rendered.get_app_configs():
            assert isinstance(config.models, dict), f"invalid_registry_mapping:{node}"
            assert all(hasattr(model, "_meta") for model in config.models.values())
        assert _registry_identity() == before, f"global_registry_changed:{node}"


if __name__ == "__main__":
    import os
    import sys
    from pathlib import Path

    import django

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    os.environ["DJANGO_SETTINGS_MODULE"] = "project.settings.test"
    django.setup()
    test_historical_migration_rendering_preserves_global_registry()
    print("historical-migration-registry: PASS")
