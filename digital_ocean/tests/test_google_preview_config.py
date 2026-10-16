from pathlib import Path
import os

import pytest
import yaml

from digital_ocean.scripts.python.google_preview_config import read_client_id
from digital_ocean.scripts.python.render_full_preview_env import render
from digital_ocean.scripts.python.deploy_config import parse_env_text

VALUE = 'synthetic.apps.googleusercontent.com'
ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize('profile', ['local.docker.yml', 'development.docker.yml'])
def test_compose_exposes_only_popup_inputs(profile):
    env = yaml.safe_load((ROOT / profile).read_text())['services']['api']['environment']
    assert 'GOOGLE_OAUTH_ENABLED=${GOOGLE_OAUTH_ENABLED:-false}' in env
    assert 'GOOGLE_OAUTH_CLIENT_ID=${GOOGLE_OAUTH_CLIENT_ID:-}' in env
    assert not any(line.startswith(('GOOGLE_OAUTH_CLIENT_SECRET=', 'GOOGLE_OAUTH_REDIRECT_URI=')) for line in env)


def private_file(tmp_path, value=VALUE):
    path = tmp_path / 'client'
    path.write_text(value)
    path.chmod(0o600)
    return path


def test_private_client_file(tmp_path, capsys):
    assert read_client_id(private_file(tmp_path)) == VALUE
    assert capsys.readouterr() == ('', '')


@pytest.mark.parametrize('case', ['missing', 'public', 'link', 'hardlink', 'directory', 'empty', 'large', 'injection', 'utf8'])
def test_unsafe_inputs_fail_silently(tmp_path, case):
    path = private_file(tmp_path)
    if case == 'missing':
        path.unlink()
    elif case == 'public':
        path.chmod(0o644)
    elif case == 'link':
        linked = tmp_path / 'linked'
        linked.symlink_to(path)
        path = linked
    elif case == 'hardlink':
        os.link(path, tmp_path / 'hardlink')
    elif case == 'directory':
        path = tmp_path
    elif case == 'utf8':
        path.write_bytes(b'\xff')
    else:
        path.write_text({'empty': '', 'large': 'x' * 513, 'injection': VALUE + '\nEVIL=1'}[case])
    with pytest.raises(ValueError, match='^google-preview-client-input-invalid$'):
        read_client_id(path)


@pytest.mark.parametrize('enabled', [False, True])
def test_render_matches_browser_and_api_without_enabling_code_flow(tmp_path, enabled):
    target = tmp_path / 'preview.env'
    render(
        ROOT / '.env.example', target, 'woodkilldev.com', 'base2-test', ['8.8.8.8/32'],
        operator_basic_auth='preview:$apr1$abc$hash', flower_basic_auth='flower:$apr1$def$hash',
        django_username='synthetic', django_email='synthetic@example.test', django_password='synthetic',
        pgadmin_email='synthetic@example.test', pgadmin_password='synthetic',
        google_client_id_file=private_file(tmp_path) if enabled else None,
    )
    values = parse_env_text(target.read_text())
    assert values['GOOGLE_OAUTH_ENABLED'] == ('true' if enabled else 'false')
    assert values['REACT_APP_GOOGLE_CLIENT_ID'] == values['GOOGLE_OAUTH_CLIENT_ID'] == (VALUE if enabled else 'disabled')
    assert values['GOOGLE_OAUTH_CLIENT_SECRET'] == ''
    assert values['GOOGLE_OAUTH_REDIRECT_URI'] == ''
    assert target.stat().st_mode & 0o777 == 0o600
