"""Producer-side acceptance for the two-UID inspector spool contract."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
import stat
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from api.services.media_inspector_client import inspect_media_via_spool
from api.services.media_inspector_receipt import verify_receipt
from api.services.media_inspector_service import CLAIM_STALE_SECONDS

ROOT = Path('/var/lib/base2/media-inspector')
PNG = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII='
)
EICAR = b'X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*'
VERIFY_KEY = Ed25519PrivateKey.from_private_bytes(b'k' * 32).public_key()


def _write(path: Path, content: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o640)
    with os.fdopen(descriptor, 'wb') as stream:
        os.fchmod(stream.fileno(), 0o640)
        stream.write(content)


def _submit(name: str, content: bytes) -> tuple[Path, str]:
    job = ROOT / name
    job.mkdir(mode=0o770)
    job.chmod(0o770)
    request = {
        'schemaVersion': 'base2-media-inspection-request-v1',
        'jobId': name,
        'nonce': name + '-nonce',
        'assetId': '00000000-0000-0000-0000-000000000110',
        'objectVersion': 1,
        'sourceSha256': hashlib.sha256(content).hexdigest(),
        'mediaType': 'image/png',
    }
    _write(job / 'content.bin', content)
    _write(job / 'request.json', json.dumps(request, separators=(',', ':')).encode())
    _write(job / 'ready', b'1')
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        for terminal in ('complete', 'failed'):
            if (job / terminal).is_file():
                return job, terminal
        time.sleep(0.02)
    raise AssertionError(f'{name} did not reach a terminal state')


def _job_with_residue(name: str, *, claim: str = 'regular', temp: str | None = None) -> Path:
    job = ROOT / name
    job.mkdir(mode=0o770)
    job.chmod(0o770)
    request = {
        'schemaVersion': 'base2-media-inspection-request-v1',
        'jobId': name,
        'nonce': name + '-nonce',
        'assetId': '00000000-0000-0000-0000-000000000110',
        'objectVersion': 1,
        'sourceSha256': hashlib.sha256(EICAR).hexdigest(),
        'mediaType': 'image/png',
    }
    _write(job / 'content.bin', EICAR)
    _write(job / 'request.json', json.dumps(request, separators=(',', ':')).encode())
    if claim == 'symlink':
        (job / 'claimed').symlink_to('/dev/zero')
    else:
        _write(job / 'claimed', b'')
        (job / 'claimed').chmod(0o600)
    if temp == 'regular':
        _write(job / 'failed.tmp', b'crash')
        (job / 'failed.tmp').chmod(0o600)
    elif temp == 'fifo':
        os.mkfifo(job / 'failed.tmp', mode=0o600)
    _write(job / 'ready', b'1')
    return job


def _stage_recovery() -> int:
    for index in range(272):
        preserved = ROOT / f'preserved-terminal-{index:04d}'
        preserved.mkdir(mode=0o770)
        preserved.chmod(0o770)
        _write(preserved / 'ready', b'1')
        _write(preserved / 'complete', b'1')
    stale = _job_with_residue('crash-residue', temp='regular')
    old = time.time() - CLAIM_STALE_SECONDS - 1
    os.utime(stale / 'claimed', (old, old), follow_symlinks=False)
    os.utime(stale / 'failed.tmp', (old, old), follow_symlinks=False)
    _job_with_residue('active-residue')
    _job_with_residue('symlink-residue', claim='symlink')
    special = _job_with_residue('special-residue', temp='fifo')
    os.utime(special / 'claimed', (old, old), follow_symlinks=False)
    os.utime(special / 'failed.tmp', (old, old), follow_symlinks=False)
    return 0


def _verify_recovery() -> int:
    recovered = ROOT / 'crash-residue'
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline and not (recovered / 'failed').is_file():
        time.sleep(0.02)
    assert (recovered / 'failed').read_bytes() == b'media_inspection_rejected'
    _assert_private_producer_file(recovered / 'failed')
    assert not (recovered / 'failed.tmp').exists()
    assert all(
        (ROOT / f'preserved-terminal-{index:04d}' / 'complete').is_file()
        for index in range(272)
    )
    for name in ('active-residue', 'symlink-residue', 'special-residue'):
        job = ROOT / name
        assert (job / 'claimed').exists() or (job / 'claimed').is_symlink()
        assert not (job / 'complete').exists() and not (job / 'failed').exists()
    for name in ('crash-residue', 'active-residue', 'symlink-residue', 'special-residue'):
        shutil.rmtree(ROOT / name)
    for index in range(272):
        shutil.rmtree(ROOT / f'preserved-terminal-{index:04d}')
    print(json.dumps({'restartRecovery': True, 'unsafeResidueRejected': True}))
    return 0


def _assert_private_producer_file(path: Path) -> None:
    info = path.stat(follow_symlinks=False)
    assert stat.S_ISREG(info.st_mode)
    assert info.st_uid == 1000
    assert info.st_gid == 1000
    assert stat.S_IMODE(info.st_mode) == 0o600


def main() -> int:
    root = ROOT.stat(follow_symlinks=False)
    assert root.st_uid == 1000 and root.st_gid == 1000
    assert stat.S_IMODE(root.st_mode) == 0o770

    verify_key = base64.urlsafe_b64encode(VERIFY_KEY.public_bytes_raw()).decode()
    result = inspect_media_via_spool(
        content=PNG,
        expected_sha256=hashlib.sha256(PNG).hexdigest(),
        media_type='image/png',
        asset_id=__import__('uuid').UUID(int=110),
        object_version=1,
        observed_at=datetime.now(UTC),
        spool_root=str(ROOT),
        encoded_verify_key=verify_key,
        timeout_seconds=30,
    )
    assert result.observed_media_type == 'image/png'

    clean, terminal = _submit('manual-clean', PNG)
    assert terminal == 'complete'
    for name in ('claimed', 'preview.bin', 'receipt.json', 'complete'):
        _assert_private_producer_file(clean / name)
    receipt = json.loads((clean / 'receipt.json').read_text(encoding='ascii'))
    verify_receipt(
        receipt,
        key=VERIFY_KEY,
        expected_job_id='manual-clean',
        expected_nonce='manual-clean-nonce',
        expected_asset_id='00000000-0000-0000-0000-000000000110',
        expected_object_version=1,
        expected_source_sha256=hashlib.sha256(PNG).hexdigest(),
        expected_media_type='image/png',
        now=datetime.now(UTC),
    )

    infected, terminal = _submit('manual-infected', EICAR)
    assert terminal == 'failed'
    _assert_private_producer_file(infected / 'failed')
    assert (infected / 'failed').read_bytes() == b'media_inspection_rejected'

    shutil.rmtree(clean)
    shutil.rmtree(infected)
    print(
        json.dumps(
            {
                'freshVolumeOwner': '1000:1000',
                'permanentFailure': True,
                'privateTerminalMode': '0600',
                'signedSuccess': True,
                'status': 'pass',
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == '__main__':
    if sys.argv[1:] == ['--stage-recovery']:
        raise SystemExit(_stage_recovery())
    if sys.argv[1:] == ['--verify-recovery']:
        raise SystemExit(_verify_recovery())
    raise SystemExit(main())
