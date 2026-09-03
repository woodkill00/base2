from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]


def test_clamav_runtime_is_opt_in_private_and_resource_bounded():
    for filename in ('local.docker.yml', 'development.docker.yml'):
        document = yaml.safe_load((ROOT / filename).read_text(encoding='utf-8'))
        service = document['services']['clamav']

        assert service['profiles'] == ['media-scan']
        assert service['networks'] == ['app_network']
        assert 'ports' not in service
        assert service['mem_limit'] == '3g'
        assert service['cpus'] == '1.0'
        assert service['volumes'] == ['clamav_db:/var/lib/clamav']
        assert document['volumes']['clamav_db'] is None
