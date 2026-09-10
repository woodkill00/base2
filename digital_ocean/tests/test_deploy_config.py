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


@pytest.mark.parametrize(
    "repo_url",
    (
        "https://token@github.com/example/base2.git",
        "https://github.com/example/base2.git?token=secret",
        "https://github.com/example/base2.git#secret",
        "git@github.com:example/base2.git",
        "http://github.com/example/base2.git",
    ),
)
def test_repository_url_rejects_credentials_and_non_https_transports(repo_url):
    with pytest.raises(DeployConfigError, match="credential-free HTTPS"):
        normalize_deploy_config({"REPO_URL": repo_url})


def test_repository_url_accepts_public_credential_free_https():
    result = normalize_deploy_config({"REPO_URL": "https://github.com/example/base2.git"})
    assert result["REPO_URL"] == "https://github.com/example/base2.git"


@pytest.mark.parametrize(
    "project_name",
    (
        "Bad_Name",
        "bad name",
        "bad'name",
        'bad"name',
        "bad\nname",
        "$(id)",
        "bad;id",
        "../bad",
    ),
)
def test_project_name_rejects_shell_and_path_syntax(project_name):
    with pytest.raises(DeployConfigError, match="PROJECT_NAME"):
        normalize_deploy_config({"PROJECT_NAME": project_name})


@pytest.mark.parametrize(
    "deploy_path",
    (
        "/opt/apps/../root/",
        "/opt/apps/$(id)/",
        "/opt/apps/;id",
        "/tmp/apps/",
        "opt/apps/",
        "/opt//apps/",
        "/opt/apps/'",
        "/opt/apps/\nroot/",
    ),
)
def test_deploy_path_rejects_noncanonical_or_shell_syntax(deploy_path):
    with pytest.raises(DeployConfigError, match="DEPLOY_PATH"):
        normalize_deploy_config({"DEPLOY_PATH": deploy_path})


@pytest.mark.parametrize("deploy_path", ("/opt/apps", "/opt/apps/"))
def test_deploy_path_normalizes_to_fixed_root(deploy_path):
    assert normalize_deploy_config({"DEPLOY_PATH": deploy_path})["DEPLOY_PATH"] == "/opt/apps/"


@pytest.mark.parametrize(
    "values",
    (
        {"DO_IP_POLL_TIMEOUT_SECONDS": "29"},
        {"DO_IP_POLL_TIMEOUT_SECONDS": "601"},
        {"DO_IP_POLL_TIMEOUT_SECONDS": "forever"},
        {"DO_IP_POLL_INTERVAL_SECONDS": "0"},
        {"DO_IP_POLL_INTERVAL_SECONDS": "31"},
        {"DO_IP_POLL_TIMEOUT_SECONDS": "30", "DO_IP_POLL_INTERVAL_SECONDS": "31"},
    ),
)
def test_provider_polling_configuration_is_hard_bounded(values):
    with pytest.raises(DeployConfigError, match="poll|bounded"):
        normalize_deploy_config(values)


def test_provider_polling_defaults_and_maximum_are_normalized():
    assert normalize_deploy_config({})["DO_IP_POLL_TIMEOUT_SECONDS"] == "120"
    result = normalize_deploy_config(
        {"DO_IP_POLL_TIMEOUT_SECONDS": "600", "DO_IP_POLL_INTERVAL_SECONDS": "30"}
    )
    assert result["DO_IP_POLL_TIMEOUT_SECONDS"] == "600"
    assert result["DO_IP_POLL_INTERVAL_SECONDS"] == "30"


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
    script = (root / "digital_ocean/scripts/powershell/deploy.ps1").read_text(encoding="utf-8")
    assert "rollback-partial-failure.txt" in script
    assert "$rollbackExit = $LASTEXITCODE" in script
    assert "if ($rollbackExit -ne 0)" in script
    assert "sed 's/[[:space:]]*#.*$//'" in script
    assert "--build --no-deps redis celery-worker" in script
    assert "up -d --build --no-deps flower" in script
    assert "for s in traefik nginx nginx-static django api redis react-app" in script
    assert "for s in traefik nginx nginx-static django api postgres redis react-app" not in script
    assert "StrictHostKeyChecking=yes" in script
    assert "StrictHostKeyChecking=no" not in script
    assert "UserKnownHostsFile=" in script
    assert "ssh-keygen -F $ip" in script
    assert "/root/logs/build/env-backup.env" not in script


def test_all_tests_use_pinned_tls_and_propagate_transport_failure():
    root = Path(__file__).resolve().parents[2]
    source = (root / "digital_ocean/scripts/powershell/test.ps1").read_text(encoding="utf-8")
    assert "letsencrypt-staging-roots.pem" in source
    assert "--cacert', $script:TrustedCaPath" in source
    assert "curl failed TLS/transport validation" in source
    assert "RemoteCertificateNameMismatch" in source
    assert "AllowUnknownCertificateAuthority" in source
    assert "staging_tls_probe.py" in source
    assert "Pinned staging TLS behavioral probe failed" in source
    assert "return $true\n    }" not in source
    assert "'-k'" not in source


def test_provisioning_is_lease_bound_and_user_data_is_not_persisted_or_logged():
    root = Path(__file__).resolve().parents[2]
    orchestrator = (root / "digital_ocean/scripts/python/orchestrate_deploy.py").read_text(
        encoding="utf-8"
    )
    deploy = (root / "digital_ocean/scripts/powershell/deploy.ps1").read_text(encoding="utf-8")
    assert "GitRemoteLeaseStore.from_environment()" in orchestrator
    assert "acquire_provider_lease(" in orchestrator
    assert "release_provider_lease(lease_store, lease_record)" in orchestrator
    assert "provider_create_attempted = True" in orchestrator
    assert "lease_record is not None and not provider_create_attempted" in orchestrator
    assert "list_named_droplets(client, DO_DROPLET_NAME)" in orchestrator
    assert "sorted(matches" not in orchestrator
    assert 'existing_userdata.pop("user_data", None)' in orchestrator
    assert 'print("--- user_data script ---' not in orchestrator
    assert 'log_json("API Request - droplets.create", droplet_spec)' not in orchestrator
    assert 'log_json("API Response - droplets.create", droplet)' not in orchestrator
    assert "API Response metadata - droplets.create" in orchestrator
    assert "$env:DO_EXPECTED_DROPLET_ID" in deploy
    assert "[string]$DropletIp" not in deploy
    assert "if ($DropletIp)" not in deploy
    assert "SSH source bootstrap after host enrollment" in deploy


def test_provider_dependencies_are_hash_locked_and_bootstrap_versions_are_attested():
    root = Path(__file__).resolve().parents[2]
    requirements = (root / "digital_ocean/requirements.txt").read_text(encoding="utf-8")
    lock = (root / "digital_ocean/requirements.lock").read_text(encoding="utf-8")
    deploy = (root / "digital_ocean/scripts/powershell/deploy.ps1").read_text(encoding="utf-8")
    bootstrap = (root / "digital_ocean/scripts/bash/digital_ocean_base.sh").read_text(
        encoding="utf-8"
    )
    assert "pydo==0.40.0" in requirements
    assert "Pillow==12.3.0" in requirements
    assert "PyYAML==6.0.3" in requirements
    assert "jsonschema==4.25.1" in requirements
    assert "pydo>=0.5.0" not in requirements
    assert "pydo==0.40.0 \\" in lock
    assert "pillow==12.3.0 \\" in lock
    assert "pyyaml==6.0.3 \\" in lock
    assert "jsonschema==4.25.1 \\" in lock
    assert "--hash=sha256:" in lock
    assert "--require-hashes -r .\\digital_ocean\\requirements.lock" in deploy
    assert "pip install --upgrade pip" not in deploy
    assert "base2-bootstrap-packages.txt" in bootstrap
    assert "dpkg-query -W" in bootstrap
    assert "[BOOTSTRAP-PACKAGE]" in bootstrap
    assert "git clone" not in bootstrap
    assert "nodesource.com" not in bootstrap
    assert "curl -fsSL" not in bootstrap
    bash_helper = (root / "scripts/bash/install-python-deps.sh").read_text(encoding="utf-8")
    powershell_helper = (root / "scripts/powershell/install-python-deps.ps1").read_text(
        encoding="utf-8"
    )
    for helper in (bash_helper, powershell_helper):
        assert "digital_ocean/requirements.lock" in helper
        assert "digital_ocean/requirements.txt" not in helper
        assert "--require-hashes" in helper


def test_provider_activation_and_terminal_evidence_are_bounded_and_required():
    root = Path(__file__).resolve().parents[2]
    orchestrator = (root / "digital_ocean/scripts/python/orchestrate_deploy.py").read_text(
        encoding="utf-8"
    )
    deploy = (root / "digital_ocean/scripts/powershell/deploy.ps1").read_text(encoding="utf-8")
    assert "wait_for_active_public_ipv4(" in orchestrator
    assert "while True:" not in orchestrator[orchestrator.index('stage("create droplet")') :]
    assert '"provider-create-outcome.json"' in orchestrator
    assert "required=True" in orchestrator
    assert "bootstrap-packages.txt" in deploy
    assert "Failed to write required deployment mode evidence" in deploy
    assert "$modePayload.resolvedAction = $deploymentAction" in deploy
    assert "Failed to bind resolved deployment action evidence" in deploy


def test_htpasswd_validation_failure_is_terminal():
    root = Path(__file__).resolve().parents[2]
    source = (root / "digital_ocean/scripts/powershell/deploy.ps1").read_text(encoding="utf-8")
    status = source.index("STATUS=$?")
    terminal = source.index('if [ "$STATUS" != 0 ]; then exit "$STATUS"; fi')
    diff = source.index('status "diff" "detecting changed files"')
    assert status < terminal < diff
    assert "mktemp -d /root/base2-deploy-private." in source
    assert "config --no-interpolate > /root/logs/compose-config.template.yml" in source
    assert "scan_artifact_secrets.py" in source
    assert source.count("config --no-interpolate") >= 3
    assert "Invoke-FinalArtifactSecretGate" in source
    assert "workspace-db-role > /root/logs/workspace-role-bootstrap.txt" in source
    assert source.index("workspace-role-bootstrap.txt") < source.index(
        "compose-up-after-migrations.txt"
    )
    assert "rollback-schema-compat.json" in source
    assert "rollback_api_migrate" not in source


def test_python_orchestrator_rejects_unknown_ssh_hosts_everywhere():
    root = Path(__file__).resolve().parents[2]
    script = (root / "digital_ocean/scripts/python/orchestrate_deploy.py").read_text(
        encoding="utf-8"
    )
    policy = (root / "digital_ocean/scripts/python/trusted_ssh.py").read_text(encoding="utf-8")
    assert "AutoAddPolicy" not in script
    assert "StrictHostKeyChecking=no" not in script
    assert "paramiko.RejectPolicy()" in policy
    assert "client.load_host_keys" in policy
    assert "StrictHostKeyChecking=yes" in policy
    assert "UserKnownHostsFile=" in policy
    assert "_trusted_ssh_client()" in script
    assert "*_strict_openssh_options()" in script


def test_deploy_has_one_exact_lifecycle_and_separate_first_host_enrollment():
    root = Path(__file__).resolve().parents[2]
    deploy = (root / "digital_ocean/scripts/powershell/deploy.ps1").read_text(encoding="utf-8")
    orchestrator = (root / "digital_ocean/scripts/python/orchestrate_deploy.py").read_text(
        encoding="utf-8"
    )
    assert "Run-Orchestrator -ProvisionOnly" in deploy
    assert deploy.count("Run-Orchestrator") == 2  # definition plus provision-only call
    assert "host-key-enrollment-required.txt" in deploy
    assert "rerun without CreateIfMissing" in deploy
    assert "--provision-only" in orchestrator
    assert "if PROVISION_ONLY:" in orchestrator
    assert "if not PROVISION_ONLY:" in orchestrator
    assert "direct_deployment_disabled" in orchestrator
    assert orchestrator.index("if PROVISION_ONLY:") < orchestrator.index(
        "ensure_dns_records_for_droplet", orchestrator.index("if PROVISION_ONLY:")
    )


def test_deploy_tls_probes_validate_trust_and_hostname():
    root = Path(__file__).resolve().parents[2]
    deploy = (root / "digital_ocean/scripts/powershell/deploy.ps1").read_text(encoding="utf-8")
    trust_store = root / "digital_ocean/config/letsencrypt-staging-roots.pem"
    assert trust_store.read_text(encoding="utf-8").count("BEGIN CERTIFICATE") == 4
    probe = (root / "digital_ocean/scripts/python/staging_tls_probe.py").read_text(encoding="utf-8")
    assert "staging_tls_probe.py" in deploy
    assert "ssl.create_default_context(cafile=str(ca_file))" in probe
    assert "context.verify_mode != ssl.CERT_REQUIRED" in probe
    assert "not context.check_hostname" in probe
    assert '--cacert "$STAGING_CA"' in deploy
    assert "ssl.CERT_NONE" not in deploy
    assert "check_hostname = False" not in deploy
    assert "curl -sk" not in deploy
    assert 'curl -sS "${RESOLVE_DOMAIN[@]}"' in deploy


def test_traefik_receives_only_allowlisted_configuration_and_scoped_secrets():
    root = Path(__file__).resolve().parents[2]
    allowed = {
        "WEBSITE_DOMAIN",
        "TRAEFIK_CERT_EMAIL",
        "TRAEFIK_CERT_RESOLVER",
        "TRAEFIK_PREVIEW_MODE",
        "OWNER_ALLOWLIST_CSV",
        "FASTAPI_PORT",
        "DJANGO_PORT",
    }
    for name in ("local.docker.yml", "development.docker.yml"):
        source = (root / name).read_text(encoding="utf-8")
        service = source.split("  traefik:\n", 1)[1].split("\n  postgres:", 1)[0]
        assert "env_file:" not in service
        environment = service.split("    environment:\n", 1)[1].split("    secrets:\n", 1)[0]
        keys = {
            line.strip()[2:].split("=", 1)[0]
            for line in environment.splitlines()
            if line.strip().startswith("- ")
        }
        assert keys == allowed
        secret_block = service.split("    secrets:\n", 1)[1]
        assert "      - traefik_dash_basic_users" in secret_block
        assert "      - flower_basic_users" in secret_block
        serialized = environment
        for forbidden in ("DO_", "DB_", "POSTGRES_", "SMTP_", "PASSWORD", "TOKEN", "SECRET"):
            assert forbidden not in serialized


def test_deploy_never_captures_raw_container_environment():
    root = Path(__file__).resolve().parents[2]
    for path in (
        "digital_ocean/scripts/powershell/deploy.ps1",
        "digital_ocean/scripts/bash/remote_verify_min.sh",
    ):
        source = (root / path).read_text(encoding="utf-8")
        assert "env | sort" not in source
        assert "TRAEFIK_DASH_BASIC_USERS=present" not in source
        assert "for key in WEBSITE_DOMAIN TRAEFIK_CERT_EMAIL" in source

    deploy = (root / "digital_ocean/scripts/powershell/deploy.ps1").read_text(encoding="utf-8")
    assert deploy.count("sanitize_traefik_config.py") == 2
    assert "cat /tmp/dynamic.yml > /root/logs/traefik-dynamic.yml" not in deploy


def test_deploy_captures_prior_state_before_mutation_and_rolls_back_core_failures():
    root = Path(__file__).resolve().parents[2]
    source = (root / "digital_ocean/scripts/powershell/deploy.ps1").read_text(encoding="utf-8")
    capture = source.index("SSH capture prior deployment state")
    upload = source.index("SCP upload .env", capture)
    mutation = source.index("$script:RemoteMutationStarted = $true", capture)
    assert capture < mutation < upload
    assert "/root/base2-rollback-private/env-backup.env" in source
    assert "cp -f /root/base2-rollback-private/env-backup.env .env" in source
    assert "printf 'fresh\\n' > /root/base2-rollback-private/deployment-kind.txt" in source
    assert "DEPLOYMENT_KIND=$(tr -d" in source
    assert "--profile celery ps -aq" in source
    assert "rollback-fresh-down.txt 2>&1 || true" not in source
    assert "rm -f .env" in source
    outer_catch = source.index("} catch {", source.index('Write-Section "Deploy"'))
    rollback = source.index("Invoke-RollbackOnFailureIfEnabled", outer_catch)
    failure_artifact = source.index("Write-FailureArtifacts", rollback)
    assert outer_catch < rollback < failure_artifact
    cleanup = "rm -rf /root/base2-rollback-private /root/logs /root/logs.tgz"
    assert cleanup in source
    assert source.index(cleanup) < source.index('Write-Section "Done"')


def test_deploy_fails_closed_on_provider_uncertainty_tests_and_evidence_loss():
    root = Path(__file__).resolve().parents[2]
    source = (root / "digital_ocean/scripts/powershell/deploy.ps1").read_text(encoding="utf-8")
    assert "droplet_lookup.py" in source
    assert "Get-DropletIp -Authoritative" in source
    assert "DigitalOcean lookup failed closed" in source
    assert "DigitalOcean lookup returned a nonterminal state" in source
    assert "continuing. Attempting minimal log capture" not in source
    assert "throw $msg" in source
    assert "$LocalTests = $true" in source
    remote_tests = source.split('if [ "${RUN_REMOTE_TESTS:-}" = "1" ]; then', 1)[1].split(
        'else\n    status "tests" "skipped', 1
    )[0]
    assert "pytest -q" in remote_tests
    assert "ruff check ." in remote_tests
    assert "mypy --show-error-codes" in remote_tests
    assert "|| true" not in remote_tests
    manifest = source.index("Assert-CompleteLocalEvidence -dest $terminalDir")
    secret_gate = source.index("Invoke-FinalArtifactSecretGate -dest $terminalDir", manifest)
    cleanup = source.index("SSH terminal evidence cleanup", secret_gate)
    assert manifest < secret_gate < cleanup
    assert '--cacert "$STAGING_CA" --resolve "$FHOST:443:127.0.0.1"' in source
    assert '--cacert "$STAGING_CA" --resolve "$AHOST:443:127.0.0.1"' in source
    assert "use -AsyncVerify" not in source


def test_deploy_builds_one_exact_api_image_for_runtime_migration_and_rollback():
    root = Path(__file__).resolve().parents[2]
    source = (root / "digital_ocean/scripts/powershell/deploy.ps1").read_text(encoding="utf-8")
    assert "build --no-cache api api-migrate" in source
    assert "build api api-migrate > /root/logs/build/api-up.txt" in source
    assert "build django api api-migrate >/root/logs/build/rollback-build.txt" in source


def test_deploy_disables_nonterminal_async_success_and_fails_closed_on_git_inspection():
    root = Path(__file__).resolve().parents[2]
    source = (root / "digital_ocean/scripts/powershell/deploy.ps1").read_text(encoding="utf-8")
    assert "if ($AsyncVerify)" in source
    assert "-AsyncVerify is non-authoritative and disabled" in source
    env_guard = source.split("function Assert-EnvNotTracked", 1)[1].split(
        "function Update-Allowlist", 1
    )[0]
    assert "Get-Command git -ErrorAction Stop" in env_guard
    assert "git ls-files --error-unmatch .env" in env_guard
    assert "Unable to verify whether .env is tracked" in env_guard
    assert "catch" not in env_guard
