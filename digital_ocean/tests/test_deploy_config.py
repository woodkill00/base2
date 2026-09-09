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
    assert 'ssl.create_default_context()' in deploy
    assert 'ssl.CERT_NONE' not in deploy
    assert 'check_hostname = False' not in deploy
    assert 'curl -sk' not in deploy
    assert 'curl -sS "${RESOLVE_DOMAIN[@]}"' in deploy
