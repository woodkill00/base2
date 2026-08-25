from __future__ import annotations

import shutil
from pathlib import Path

from scripts.python.validate_acme_mode import STAGING_ENDPOINT, validate


def _fixture(tmp_path: Path) -> Path:
    root = Path(__file__).resolve().parents[2]
    for relative in (
        "traefik/traefik.yml",
        "traefik/entrypoint.sh",
        ".env.example",
        "digital_ocean/scripts/powershell/deploy.ps1",
        "digital_ocean/scripts/powershell/test.ps1",
        "digital_ocean/scripts/powershell/smoke-tests.ps1",
    ):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / relative, target)
    return tmp_path


def test_repository_is_staging_only() -> None:
    root = Path(__file__).resolve().parents[2]
    assert validate(root) == []


def test_live_endpoint_is_rejected(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    path = root / "traefik/traefik.yml"
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            STAGING_ENDPOINT, "https://acme-v02.api.letsencrypt.org/directory"
        ),
        encoding="utf-8",
    )
    assert any("live Let's Encrypt endpoint" in item for item in validate(root))


def test_live_resolver_and_storage_are_rejected(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    path = root / "traefik/traefik.yml"
    path.write_text(
        path.read_text(encoding="utf-8")
        + "\n  le:\n    acme:\n      storage: /etc/traefik/acme/acme.json\n",
        encoding="utf-8",
    )
    errors = validate(root)
    assert any("live le resolver" in item for item in errors)
    assert any("live ACME storage" in item for item in errors)


def test_entrypoint_override_escape_is_rejected(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    path = root / "traefik/entrypoint.sh"
    path.write_text(
        path.read_text(encoding="utf-8") + '\nTRAEFIK_CERT_RESOLVER="le"\n',
        encoding="utf-8",
    )
    assert any("live resolver" in item for item in validate(root))
