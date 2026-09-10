from pathlib import Path


def test_database_recovery_acceptance_is_pinned_isolated_and_reconciled():
    source = (
        Path(__file__).resolve().parents[2] / "scripts/python/run_database_recovery_acceptance.py"
    ).read_text(encoding="utf-8")
    assert "postgres@sha256:" in source
    assert "restore_drill_001" in source
    assert "pg_dump" in source and "pg_restore" in source
    assert "--exit-on-error" in source
    assert "create_database_object_bundle(" in source
    assert "restore_stream_backup(" in source
    assert "reconcile_restore(components)" in source
    assert 'run("docker", "rm", "-f"' in source
