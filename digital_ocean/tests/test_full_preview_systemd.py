from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_expiry_timer_calls_one_unified_lifecycle_operation():
    service = (ROOT / "digital_ocean/systemd/base2-full-preview-expiry@.service").read_text()
    timer = (ROOT / "digital_ocean/systemd/base2-full-preview-expiry@.timer").read_text()
    assert "full_preview_expire" in service
    assert "--run-id %i" in service
    assert "--early-approved" not in service
    assert "ProtectSystem=strict" in service and "NoNewPrivileges=yes" in service
    assert "Persistent=true" in timer
    assert "Unit=base2-full-preview-expiry@%i.service" in timer


def test_timer_has_no_parallel_or_legacy_dns_cleanup_command():
    combined = "\n".join(
        path.read_text() for path in (ROOT / "digital_ocean/systemd").glob("base2-full-preview-expiry@.*")
    )
    assert "delete_record" not in combined
    assert "destroy_droplet" not in combined
    assert combined.count("ExecStart=") == 1


def test_remote_bootstrap_identifies_every_silent_failure_stage_without_values():
    script = (ROOT / "digital_ocean/scripts/bash/full-preview-remote.sh").read_text()
    assert 'full-preview-stage-failed:%s exit=%s' in script
    for stage in (
        "cloud-init-wait",
        "docker-install",
        "docker-start",
        "env-render",
        "acme-bootstrap",
        "compose-build",
        "compose-up",
        "api-migrations",
        "service-inventory",
        "service-health",
        "traefik-policy",
        "receipt",
    ):
        assert f'stage="{stage}"' in script
    assert "password" not in script.split("full-preview-stage-failed", 1)[1].split("ERR", 1)[0]


def test_remote_renderer_runs_as_repository_module_on_a_fresh_host():
    script = (ROOT / "digital_ocean/scripts/bash/full-preview-remote.sh").read_text()
    assert 'cd "$repo_root"' in script
    assert "python3 -m digital_ocean.scripts.python.render_full_preview_env" in script
    assert 'python3 "$repo_root/digital_ocean/scripts/python/render_full_preview_env.py"' not in script


def test_remote_bootstrap_applies_api_migrations_before_acceptance():
    script = (ROOT / "digital_ocean/scripts/bash/full-preview-remote.sh").read_text()
    assert "python -m api.scripts.migrate" in script
    assert script.index('stage="api-migrations"') < script.index('stage="service-inventory"')
    assert script.index('stage="api-migrations"') < script.index('stage="receipt"')


def test_media_enabled_preview_builds_and_starts_isolated_inspector_with_image_identity():
    script = (ROOT / "digital_ocean/scripts/bash/full-preview-remote.sh").read_text()
    example = (ROOT / ".env.example").read_text()
    validator = (ROOT / "scripts/python/validate_compose_config.py").read_text()
    assert '--profile celery --profile media-scan' in script
    assert 'openssl genpkey -algorithm ED25519' in script
    assert "'/^MEDIA_INSPECTOR_SIGNING_KEY=/d'" in script
    assert 'inspector_image_ref="${project}-media-inspector"' in script
    assert "docker image inspect --format '{{.Id}}'" in script
    assert 'inspector_image_id#sha256:' in script
    assert "running_inspector_image" in script
    assert '[[ "$running_inspector_image" == "$inspector_image_id" ]]' in script
    assert 'rm -f -- "$inspector_private_pem"' in script
    assert '|| fail_stage 3' in script
    for key in (
        'MEDIA_INSPECTOR_SIGNING_KEY=',
        'MEDIA_INSPECTOR_VERIFY_KEY=',
        'MEDIA_INSPECTOR_BUILD_IDENTITY=',
    ):
        assert example.count(key) == 1
        assert key + '\n' in example
    assert 'ephemeral_inspector_attestation' in validator
    assert '"media-inspector", "celery-worker", "celery-beat"' in validator
    assert '"--profile", "media-scan"' in validator


def test_remote_bootstrap_accepts_only_the_successful_workspace_role_one_shot():
    script = (ROOT / "digital_ocean/scripts/bash/full-preview-remote.sh").read_text()
    assert (
        "one_shot_services=(workspace-db-role media-inspector-spool-init)" in script
    )
    assert '"${compose[@]}" ps -a -q "$service"' in script
    assert '"${compose[@]}" ps -q "$service"' not in script
    assert "'{{.State.ExitCode}}'" in script
    assert '[[ "$state" == "exited" && "$exit_code" == "0" ]]' in script
    assert 'pending+=("$service:$state:exit-$exit_code")' in script
    assert script.index(
        "one_shot_services=(workspace-db-role media-inspector-spool-init)"
    ) < script.index('stage="service-health"')
