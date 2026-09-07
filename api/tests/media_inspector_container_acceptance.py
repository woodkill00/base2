"""Unmocked E2E acceptance for the hardened media-inspector supervisor."""

from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from pypdf import PdfWriter

from api.services.media_inspector_client import (
    MAX_SOURCE_BYTES,
    MediaInspectorClientError,
    inspect_media_via_spool,
)
from api.services.media_inspector_service import (
    SCANNER_ADDRESS_SPACE_BYTES,
    _fixed_run,
    _scanner_health,
)


PNG_1X1 = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII='
)
EICAR = b'X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*'
SPOOL_ROOT = '/var/lib/base2/media-inspector'
BUILD_IDENTITY = 'base2-media-inspector:' + 'b' * 64


def _ffmpeg(*arguments: str) -> bytes:
    completed = subprocess.run(
        ['/usr/bin/ffmpeg', '-hide_banner', '-loglevel', 'error', *arguments],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=20,
        check=False,
        shell=False,
        close_fds=True,
        env={'PATH': '/usr/bin:/bin', 'LC_ALL': 'C', 'HOME': '/nonexistent'},
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout
    return completed.stdout


def _fixtures() -> list[tuple[str, bytes]]:
    pdf_output = io.BytesIO()
    pdf = PdfWriter()
    pdf.add_blank_page(width=72, height=72)
    pdf.write(pdf_output)
    audio = _ffmpeg(
        '-f',
        'lavfi',
        '-i',
        'sine=frequency=440:duration=0.1',
        '-c:a',
        'libvorbis',
        '-f',
        'ogg',
        'pipe:1',
    )
    video = _ffmpeg(
        '-f',
        'lavfi',
        '-i',
        'color=black:size=16x16:duration=0.1',
        '-c:v',
        'libx264',
        '-pix_fmt',
        'yuv420p',
        '-movflags',
        'frag_keyframe+empty_moov',
        '-f',
        'mp4',
        'pipe:1',
    )
    large_png = PNG_1X1 + b'\0' * (8 * 1024 * 1024 - len(PNG_1X1))
    return [
        ('image/png', large_png),
        ('application/pdf', pdf_output.getvalue()),
        ('audio/ogg', audio),
        ('video/mp4', video),
    ]


def _inspect(content: bytes, media_type: str, verify_key: str, sequence: int):
    return inspect_media_via_spool(
        content=content,
        expected_sha256=hashlib.sha256(content).hexdigest(),
        media_type=media_type,
        asset_id=UUID(int=sequence),
        object_version=1,
        observed_at=datetime.now(UTC),
        spool_root=SPOOL_ROOT,
        encoded_verify_key=verify_key,
        timeout_seconds=60,
    )


def main() -> int:
    assert os.listdir('/sys/class/net') == ['lo']
    try:
        open('/root/media-inspector-write-probe', 'wb').close()
    except OSError:
        pass
    else:
        raise AssertionError('container root filesystem is writable')
    spool = os.statvfs(SPOOL_ROOT)
    spool_capacity = spool.f_blocks * spool.f_frsize
    assert MAX_SOURCE_BYTES + 16 * 1024 * 1024 <= spool_capacity <= 128 * 1024 * 1024
    memory_limit = int(Path('/sys/fs/cgroup/memory.max').read_text(encoding='ascii'))
    assert memory_limit == 1536 * 1024 * 1024
    assert memory_limit > SCANNER_ADDRESS_SPACE_BYTES

    health = _scanner_health()
    assert health['engine'] == 'clamav' and health['version'] == '1.5.4'
    assert health['definitionsVersion'].isdigit() and health['definitionsAt'].endswith('Z')
    health_process = subprocess.run(
        [sys.executable, '-m', 'api.services.media_inspector_service', '--healthcheck'],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        timeout=10,
        check=False,
        close_fds=True,
    )
    assert health_process.returncode == 0, health_process.stderr

    seed = b'k' * 32
    private_key = Ed25519PrivateKey.from_private_bytes(seed)
    signing_key = base64.urlsafe_b64encode(seed).decode('ascii')
    verify_key = base64.urlsafe_b64encode(
        private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
    ).decode('ascii')
    os.environ['MEDIA_INSPECTOR_SIGNING_KEY'] = signing_key
    supervisor_env = {
        **os.environ,
        'MEDIA_INSPECTOR_SIGNING_KEY': signing_key,
        'MEDIA_INSPECTOR_BUILD_IDENTITY': BUILD_IDENTITY,
        'MEDIA_INSPECTOR_SPOOL_ROOT': SPOOL_ROOT,
    }
    supervisor = subprocess.Popen(
        [sys.executable, '-m', 'api.services.media_inspector_service'],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        close_fds=True,
        env=supervisor_env,
    )
    signing_probe = Path('/tmp/base2-supervisor-signing-key')
    try:
        time.sleep(0.25)
        if supervisor.poll() is not None:
            startup_error = supervisor.stderr.read(4096) if supervisor.stderr is not None else b''
            raise AssertionError(startup_error)
        signing_probe.write_text(signing_key, encoding='ascii')
        signing_probe.chmod(0o600)
        child_source = """
import json
import os
import sys

supervisor_pid = int(sys.argv[1])

def denied(path):
    try:
        with open(path, 'rb', buffering=0) as handle:
            handle.read(1)
    except OSError:
        return True
    return False

status = open('/proc/self/status', encoding='ascii').read()
print(json.dumps({
    'uid': os.getuid(),
    'noNewPrivs': 'NoNewPrivs:\\t1' in status,
    'effectiveCaps': 'CapEff:\\t0000000000000000' in status,
    'hasSigningKey': 'MEDIA_INSPECTOR_SIGNING_KEY' in os.environ,
    'supervisorEnvironmentDenied': denied(f'/proc/{supervisor_pid}/environ'),
    'supervisorMemoryDenied': denied(f'/proc/{supervisor_pid}/mem'),
    'signerFileDenied': denied('/tmp/base2-supervisor-signing-key'),
    'signerThroughSupervisorRootDenied': denied(
        f'/proc/{supervisor_pid}/root/tmp/base2-supervisor-signing-key'
    ),
}))
"""
        child = _fixed_run(
            ['/usr/bin/python', '-c', child_source, str(supervisor.pid)],
            timeout=5,
            maximum_output=4096,
        )
        assert child.returncode == 0, child.stderr
        isolation = json.loads(child.stdout)
        assert isolation == {
            'uid': 65534,
            'noNewPrivs': True,
            'effectiveCaps': True,
            'hasSigningKey': False,
            'supervisorEnvironmentDenied': True,
            'supervisorMemoryDenied': True,
            'signerFileDenied': True,
            'signerThroughSupervisorRootDenied': True,
        }
        observed = []
        for sequence, (media_type, content) in enumerate(_fixtures(), start=1):
            try:
                result = _inspect(content, media_type, verify_key, sequence)
            except Exception as exc:
                raise AssertionError(f'{media_type} E2E failed: {exc}') from exc
            assert result.observed_media_type == media_type
            assert result.scanner_ref.startswith('clamav:1.5.4-')
            assert result.result_sha256
            observed.append(media_type)

        try:
            _inspect(EICAR, 'image/png', verify_key, 10)
        except MediaInspectorClientError as exc:
            assert str(exc) == 'media_inspection_rejected'
        else:
            raise AssertionError('EICAR was not rejected')

        oversized = b'x' * (MAX_SOURCE_BYTES + 1)
        try:
            _inspect(oversized, 'image/png', verify_key, 11)
        except MediaInspectorClientError as exc:
            assert str(exc) == 'media_integrity_failed'
        else:
            raise AssertionError('oversized payload was not rejected before spooling')
        finally:
            del oversized
    finally:
        signing_probe.unlink(missing_ok=True)
        supervisor.terminate()
        supervisor.wait(timeout=10)

    memory_peak = int(Path('/sys/fs/cgroup/memory.peak').read_text(encoding='ascii'))
    assert memory_limit - memory_peak >= 128 * 1024 * 1024

    print(
        json.dumps(
            {
                'definitionsVersion': health['definitionsVersion'],
                'isolation': isolation,
                'memoryLimitBytes': memory_limit,
                'memoryPeakBytes': memory_peak,
                'observedMediaTypes': observed,
                'scanner': health['version'],
                'signedSpoolE2E': True,
                'spoolCapacityBytes': spool_capacity,
                'status': 'pass',
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
