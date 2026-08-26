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
