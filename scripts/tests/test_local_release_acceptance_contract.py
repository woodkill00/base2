from pathlib import Path


def test_local_release_acceptance_is_disposable_pinned_and_traffic_bearing():
    source = (
        Path(__file__).resolve().parents[2]
        / 'scripts/python/run_local_release_acceptance.py'
    ).read_text(encoding='utf-8')
    assert 'nginx@sha256:' in source
    assert "'docker', 'network', 'create'" in source
    assert "'docker', 'run', '-d'" in source
    assert 'proxy_pass http://' in source
    assert "'docker', 'rm', '-f'" in source
    assert "'docker', 'network', 'rm'" in source
    assert "health=lambda action: False" in source
    assert "action='rollback'" in source
