import pytest

from digital_ocean.scripts.python.refresh_full_preview_allowlist import AllowlistRefreshError, approval_digest, refresh


def target(tmp_path):
    path = tmp_path / "preview.env"
    path.write_text("TRAEFIK_PREVIEW_MODE=full-preview\nOWNER_ALLOWLIST_CSV=8.8.8.8/32\nDJANGO_ADMIN_ALLOWLIST=8.8.8.8/32\nPGADMIN_ALLOWLIST=8.8.8.8/32\nFLOWER_ALLOWLIST=8.8.8.8/32\nSECRET=retained\n")
    path.chmod(0o600)
    return path


def test_exact_approval_updates_only_allowlist_fields_and_preserves_secrets(tmp_path):
    path = target(tmp_path); cidrs = ["1.1.1.1/32", "8.8.4.4/32"]
    receipt = refresh(path, "base2-full-20260826-001", cidrs, approval_digest("base2-full-20260826-001", cidrs))
    text = path.read_text()
    assert receipt["ownerCidrCount"] == 2 and receipt["secretValuesEmitted"] == 0
    assert "OWNER_ALLOWLIST_CSV=1.1.1.1/32,8.8.4.4/32" in text
    assert "SECRET=retained" in text


def test_wrong_approval_or_broad_cidr_performs_zero_write(tmp_path):
    path = target(tmp_path); before = path.read_bytes()
    with pytest.raises(AllowlistRefreshError, match="approval"):
        refresh(path, "base2-full-20260826-001", ["1.1.1.1/32"], "0" * 64)
    assert path.read_bytes() == before
    with pytest.raises(ValueError):
        approval_digest("base2-full-20260826-001", ["1.1.1.0/24"])
