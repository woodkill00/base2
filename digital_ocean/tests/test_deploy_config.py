from __future__ import annotations

from pathlib import Path

import pytest

from digital_ocean.scripts.python.deploy_config import (
    KNOWN_DO_KEYS,
    DeployConfigError,
    load_deploy_config,
    normalize_deploy_config,
    parse_env_text,
    redact_config,
)


def test_quotes_whitespace_crlf_and_comments_are_normalized():
    parsed = parse_env_text(
        '  # comment\r\nDO_API_REGION = "fra1"\r\nDO_APP_NAME=base2-preview # note\r\n'
    )
    assert parsed == {"DO_API_REGION": "fra1", "DO_APP_NAME": "base2-preview"}


def test_hash_inside_quotes_is_preserved():
    assert parse_env_text("DO_API_TOKEN='token#value'\n") == {"DO_API_TOKEN": "token#value"}


@pytest.mark.parametrize(
    "text,match",
    [
        ("DO_API_REGION=fra1\nDO_API_REGION=nyc3\n", "duplicate"),
        ("DO_UNKNOWN=value\n", "unknown DigitalOcean key"),
        ('DO_API_REGION="fra1\n', "unterminated quote"),
        ("NOT A KEY=value\n", "invalid key"),
        ("DO_API_TOKEN\n", "missing equals"),
    ],
)
def test_malformed_or_ambiguous_env_fails(text, match):
    with pytest.raises(DeployConfigError, match=match):
        parse_env_text(text)


@pytest.mark.parametrize(
    "field,value",
    [
        ("DO_API_REGION", "not-a-region"),
        ("DO_APP_NAME", "Bad Name"),
        ("DO_DROPLET_NAME", "-leading-dash"),
        ("DO_API_IMAGE", "bad image!"),
    ],
)
def test_malformed_provider_identity_fails(field, value):
    values = {
        "DO_API_REGION": "fra1",
        "DO_APP_NAME": "base2",
        "DO_DROPLET_NAME": "base2-preview",
        "DO_API_IMAGE": "ubuntu-22-04-x64",
    }
    values[field] = value
    with pytest.raises(DeployConfigError, match=field):
        normalize_deploy_config(values)


def test_templates_expand_before_identity_validation():
    result = normalize_deploy_config(
        {
            "DO_API_REGION": "fra1",
            "DO_APP_NAME": "${PROJECT_NAME}",
            "DO_DROPLET_NAME": "${PROJECT_NAME}-preview",
            "DO_API_IMAGE": "ubuntu-22-04-x64",
        },
        environment={"PROJECT_NAME": "base2"},
    )
    assert result["DO_APP_NAME"] == "base2"
    assert result["DO_DROPLET_NAME"] == "base2-preview"


def test_secret_redaction_never_returns_values():
    redacted = redact_config(
        {
            "DO_API_TOKEN": "secret-value",
            "DO_SPACES_SECRET": "another-secret",
            "DO_API_REGION": "fra1",
        }
    )
    assert redacted == {
        "DO_API_REGION": "fra1",
        "DO_API_TOKEN": "[REDACTED]",
        "DO_SPACES_SECRET": "[REDACTED]",
    }
    assert "secret-value" not in str(redacted)


def test_example_has_no_unknown_provider_keys():
    root = Path(__file__).resolve().parents[2]
    keys = {
        line.strip().split("=", 1)[0]
        for line in (root / ".env.example").read_text(encoding="utf-8").splitlines()
        if line.strip().startswith("DO_") and "=" in line
    }
    assert keys <= KNOWN_DO_KEYS


def test_missing_file_has_typed_sanitized_error(tmp_path):
    with pytest.raises(DeployConfigError, match="environment file is unavailable") as error:
        load_deploy_config(tmp_path / "contains-secret-in-name.env")
    assert "secret" not in str(error.value)


def test_powershell_deploy_fails_closed_for_partial_rollback_and_inline_commit_comments():
    root = Path(__file__).resolve().parents[2]
    script = (root / 'digital_ocean/scripts/powershell/deploy.ps1').read_text(encoding='utf-8')
    assert "rollback-partial-failure.txt" in script
    assert "$rollbackExit = $LASTEXITCODE" in script
    assert "if ($rollbackExit -ne 0)" in script
    assert "sed 's/[[:space:]]*#.*$//'" in script
    assert '--build --no-deps redis celery-worker' in script
    assert 'up -d --build --no-deps flower' in script
    assert 'for s in traefik nginx nginx-static django api redis react-app' in script
    assert 'for s in traefik nginx nginx-static django api postgres redis react-app' not in script
    assert "StrictHostKeyChecking=yes" in script
    assert "StrictHostKeyChecking=no" not in script
    assert "UserKnownHostsFile=" in script
    assert "ssh-keygen -F $ip" in script
    assert "/root/logs/build/env-backup.env" not in script
    assert 'mktemp -d /root/base2-deploy-private.' in script
    assert 'config --no-interpolate > /root/logs/compose-config.template.yml' in script
    assert 'scan_artifact_secrets.py' in script
    assert script.count('config --no-interpolate') >= 3
    assert 'Invoke-FinalArtifactSecretGate' in script
    assert 'workspace-db-role > /root/logs/workspace-role-bootstrap.txt' in script
    assert script.index('workspace-role-bootstrap.txt') < script.index('compose-up-after-migrations.txt')
    assert 'rollback-schema-compat.json' in script
    assert 'rollback_api_migrate' not in script


def test_python_orchestrator_rejects_unknown_ssh_hosts_everywhere():
    root = Path(__file__).resolve().parents[2]
    script = (root / 'digital_ocean/scripts/python/orchestrate_deploy.py').read_text(
        encoding='utf-8'
    )
    policy = (root / 'digital_ocean/scripts/python/trusted_ssh.py').read_text(encoding='utf-8')
    assert 'AutoAddPolicy' not in script
    assert 'StrictHostKeyChecking=no' not in script
    assert 'paramiko.RejectPolicy()' in policy
    assert 'client.load_host_keys' in policy
    assert 'StrictHostKeyChecking=yes' in policy
    assert 'UserKnownHostsFile=' in policy
    assert '_trusted_ssh_client()' in script
    assert '*_strict_openssh_options()' in script


def test_deploy_has_one_exact_lifecycle_and_separate_first_host_enrollment():
    root = Path(__file__).resolve().parents[2]
    deploy = (root / 'digital_ocean/scripts/powershell/deploy.ps1').read_text(encoding='utf-8')
    orchestrator = (
        root / 'digital_ocean/scripts/python/orchestrate_deploy.py'
    ).read_text(encoding='utf-8')
    assert 'Run-Orchestrator -ProvisionOnly' in deploy
    assert deploy.count('Run-Orchestrator') == 2  # definition plus provision-only call
    assert 'host-key-enrollment-required.txt' in deploy
    assert 'rerun without CreateIfMissing' in deploy
    assert '--provision-only' in orchestrator
    assert 'if PROVISION_ONLY:' in orchestrator
    assert 'if not PROVISION_ONLY:' in orchestrator
    assert 'direct_deployment_disabled' in orchestrator
    assert orchestrator.index('if PROVISION_ONLY:') < orchestrator.index(
        'ensure_dns_records_for_droplet', orchestrator.index('if PROVISION_ONLY:')
    )


def test_deploy_tls_probes_validate_trust_and_hostname():
    root = Path(__file__).resolve().parents[2]
    deploy = (root / 'digital_ocean/scripts/powershell/deploy.ps1').read_text(encoding='utf-8')
    trust_store = root / 'digital_ocean/config/letsencrypt-staging-roots.pem'
    assert trust_store.read_text(encoding='utf-8').count('BEGIN CERTIFICATE') == 4
    probe = (root / 'digital_ocean/scripts/python/staging_tls_probe.py').read_text(
        encoding='utf-8'
    )
    assert 'staging_tls_probe.py' in deploy
    assert "ssl.create_default_context(cafile=str(ca_file))" in probe
    assert 'context.verify_mode != ssl.CERT_REQUIRED' in probe
    assert 'not context.check_hostname' in probe
    assert '--cacert "$STAGING_CA"' in deploy
    assert 'ssl.CERT_NONE' not in deploy
    assert 'check_hostname = False' not in deploy
    assert 'curl -sk' not in deploy
    assert 'curl -sS "${RESOLVE_DOMAIN[@]}"' in deploy


def test_traefik_receives_only_allowlisted_configuration_and_scoped_secrets():
    root = Path(__file__).resolve().parents[2]
    allowed = {
        'WEBSITE_DOMAIN',
        'TRAEFIK_CERT_EMAIL',
        'TRAEFIK_CERT_RESOLVER',
        'TRAEFIK_PREVIEW_MODE',
        'OWNER_ALLOWLIST_CSV',
    }
    for name in ('local.docker.yml', 'development.docker.yml'):
        source = (root / name).read_text(encoding='utf-8')
        service = source.split('  traefik:\n', 1)[1].split('\n  postgres:', 1)[0]
        assert 'env_file:' not in service
        environment = service.split('    environment:\n', 1)[1].split(
            '    secrets:\n', 1
        )[0]
        keys = {
            line.strip()[2:].split('=', 1)[0]
            for line in environment.splitlines()
            if line.strip().startswith('- ')
        }
        assert keys == allowed
        secret_block = service.split('    secrets:\n', 1)[1]
        assert '      - traefik_dash_basic_users' in secret_block
        assert '      - flower_basic_users' in secret_block
        serialized = environment
        for forbidden in ('DO_', 'DB_', 'POSTGRES_', 'SMTP_', 'PASSWORD', 'TOKEN', 'SECRET'):
            assert forbidden not in serialized


def test_deploy_never_captures_raw_container_environment():
    root = Path(__file__).resolve().parents[2]
    for path in (
        'digital_ocean/scripts/powershell/deploy.ps1',
        'digital_ocean/scripts/bash/remote_verify_min.sh',
    ):
        source = (root / path).read_text(encoding='utf-8')
        assert "env | sort" not in source
        assert 'TRAEFIK_DASH_BASIC_USERS=present' not in source
        assert 'for key in WEBSITE_DOMAIN TRAEFIK_CERT_EMAIL' in source

    deploy = (root / 'digital_ocean/scripts/powershell/deploy.ps1').read_text(
        encoding='utf-8'
    )
    assert deploy.count('sanitize_traefik_config.py') == 2
    assert 'cat /tmp/dynamic.yml > /root/logs/traefik-dynamic.yml' not in deploy


def test_deploy_captures_prior_state_before_mutation_and_rolls_back_core_failures():
    root = Path(__file__).resolve().parents[2]
    source = (root / 'digital_ocean/scripts/powershell/deploy.ps1').read_text(encoding='utf-8')
    capture = source.index('SSH capture prior deployment state')
    upload = source.index('SCP upload .env', capture)
    mutation = source.index('$script:RemoteMutationStarted = $true', capture)
    assert capture < mutation < upload
    assert '/root/base2-rollback-private/env-backup.env' in source
    assert 'cp -f /root/base2-rollback-private/env-backup.env .env' in source
    assert "printf 'fresh\\n' > /root/base2-rollback-private/deployment-kind.txt" in source
    assert 'DEPLOYMENT_KIND=$(tr -d' in source
    assert 'Fresh-target rollback left a Base2 container active' in source
    assert 'rm -f .env' in source
    outer_catch = source.index('} catch {', source.index('Write-Section "Deploy"'))
    rollback = source.index('Invoke-RollbackOnFailureIfEnabled', outer_catch)
    failure_artifact = source.index('Write-FailureArtifacts', rollback)
    assert outer_catch < rollback < failure_artifact
    cleanup = 'rm -rf /root/base2-rollback-private /root/logs /root/logs.tgz'
    assert cleanup in source
    assert source.index(cleanup) < source.index('Write-Section "Done"')


def test_deploy_disables_nonterminal_async_success_and_fails_closed_on_git_inspection():
    root = Path(__file__).resolve().parents[2]
    source = (root / 'digital_ocean/scripts/powershell/deploy.ps1').read_text(encoding='utf-8')
    assert "if ($AsyncVerify)" in source
    assert "-AsyncVerify is non-authoritative and disabled" in source
    env_guard = source.split('function Assert-EnvNotTracked', 1)[1].split(
        'function Update-Allowlist', 1
    )[0]
    assert 'Get-Command git -ErrorAction Stop' in env_guard
    assert 'git ls-files --error-unmatch .env' in env_guard
    assert 'Unable to verify whether .env is tracked' in env_guard
    assert 'catch' not in env_guard
