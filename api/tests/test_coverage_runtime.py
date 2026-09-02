from configparser import ConfigParser
from pathlib import Path


def test_repository_coverage_uses_pinned_stable_tracer():
    config = ConfigParser()
    loaded = config.read(Path(__file__).resolve().parents[2] / '.coveragerc')

    assert loaded
    assert config.get('run', 'core') == 'ctrace'
