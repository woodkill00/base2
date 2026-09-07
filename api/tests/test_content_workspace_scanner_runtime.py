from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]


def test_clamav_runtime_is_opt_in_private_and_resource_bounded():
    for filename in ('local.docker.yml', 'development.docker.yml'):
        document = yaml.safe_load((ROOT / filename).read_text(encoding='utf-8'))
        service = document['services']['clamav']

        assert service['profiles'] == ['media-scan']
        assert service['networks'] == ['clamav_egress']
        assert 'ports' not in service
        assert service['mem_limit'] == '512m'
        assert service['cpus'] == '0.25'
        assert service['read_only'] is True
        assert service['cap_drop'] == ['ALL']
        assert service['security_opt'] == ['no-new-privileges:true']
        assert service['entrypoint'] == ['/usr/bin/freshclam']
        assert service['image'].startswith('clamav/clamav@sha256:')
        assert 'clamav_db:/var/lib/clamav' in service['volumes']
        assert document['networks']['clamav_egress'] == {
            'name': '${COMPOSE_PROJECT_NAME}_clamav_egress',
            'internal': False,
        }
        assert document['volumes']['clamav_db'] is None
