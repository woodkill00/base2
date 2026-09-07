"""Networkless spool supervisor for disposable media decoding."""

from __future__ import annotations
import base64
import contextlib
import ctypes
import hashlib
import json
import os
import platform
import re
import resource
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Callable
from api.services.media_inspector_receipt import load_signing_key, sign_receipt

MAX_INPUT_BYTES = 100 * 1024 * 1024
MAX_RUNNER_OUTPUT = 15 * 1024 * 1024
# The decoder may launch the separately bounded 512 MiB ffprobe subprocess;
# its parent's hard ceiling must remain above that nested limit.
DECODER_ADDRESS_SPACE_BYTES = 640 * 1024 * 1024
SCANNER_ADDRESS_SPACE_BYTES = 1024 * 1024 * 1024
MAX_DEFINITION_AGE = timedelta(hours=24)
MAX_DEFINITION_FUTURE_SKEW = timedelta(minutes=5)
REQUEST_KEYS = {
    'schemaVersion',
    'jobId',
    'nonce',
    'assetId',
    'objectVersion',
    'sourceSha256',
    'mediaType',
}
RUNNER_KEYS = {
    'decoderName',
    'decoderVersion',
    'observedMediaType',
    'measurements',
    'preview',
    'previewBase64',
}
CLAM_VERSION = re.compile(r'^ClamAV ([0-9][A-Za-z0-9._-]{0,31})/([0-9]{1,12})/(.{8,80})$')


class MediaInspectorServiceError(ValueError):
    pass


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _stamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec='microseconds').replace('+00:00', 'Z')


def _limits(address_space_bytes: int = DECODER_ADDRESS_SPACE_BYTES) -> None:
    resource.setrlimit(resource.RLIMIT_CPU, (20, 20))
    resource.setrlimit(resource.RLIMIT_AS, (address_space_bytes,) * 2)
    resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_RUNNER_OUTPUT,) * 2)
    resource.setrlimit(resource.RLIMIT_NOFILE, (32, 32))
    resource.setrlimit(resource.RLIMIT_NPROC, (8, 8))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def _scanner_limits() -> None:
    # Current signed ClamAV databases need a larger virtual address-space ceiling
    # than decoders. The container memory and PID ceilings remain authoritative.
    _limits(SCANNER_ADDRESS_SPACE_BYTES)


SANDBOX_PREFIX = [
    '/usr/bin/setpriv',
    '--reuid=65534',
    '--regid=65534',
    '--clear-groups',
    '--no-new-privs',
    '--inh-caps=-all',
    '--ambient-caps=-all',
    '--bounding-set=-all',
]


def _fixed_run(
    argv: list[str],
    *,
    content: bytes | None = None,
    timeout: int = 25,
    maximum_output: int = 64 * 1024,
    scanner_memory: bool = False,
) -> subprocess.CompletedProcess[bytes]:
    command = [*SANDBOX_PREFIX, *argv]
    with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
        try:
            completed = subprocess.run(
                command,
                input=content,
                stdout=output,
                stderr=errors,
                timeout=timeout,
                check=False,
                shell=False,
                close_fds=True,
                cwd='/tmp',
                env={
                    'PATH': '/usr/bin:/bin',
                    'LC_ALL': 'C',
                    'HOME': '/nonexistent',
                    'LD_LIBRARY_PATH': '/usr/local/lib',
                    'PYTHONPATH': '/app/vendor:/app',
                },
                preexec_fn=_scanner_limits if scanner_memory else _limits,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise MediaInspectorServiceError('media_inspector_dependency_unavailable') from exc
        output.seek(0)
        errors.seek(0)
        stdout = output.read(maximum_output + 1)
        stderr = errors.read(4097)
    if len(stdout) > maximum_output or len(stderr) > 4096:
        raise MediaInspectorServiceError('media_inspector_output_invalid')
    return subprocess.CompletedProcess(command, completed.returncode, stdout, stderr)


def _scanner_health(
    run: Callable[..., subprocess.CompletedProcess[bytes]] = _fixed_run,
    now: Callable[[], datetime] = _utc_now,
) -> dict[str, Any]:
    completed = run(
        ['/usr/bin/clamscan', '--database=/var/lib/clamav', '--version'],
        timeout=5,
        maximum_output=4096,
        scanner_memory=True,
    )
    if completed.returncode != 0:
        raise MediaInspectorServiceError('media_scanner_unavailable')
    try:
        text = completed.stdout.decode('ascii').strip()
    except UnicodeDecodeError as exc:
        raise MediaInspectorServiceError('media_scanner_response_invalid') from exc
    match = CLAM_VERSION.fullmatch(text)
    if match is None:
        raise MediaInspectorServiceError('media_scanner_response_invalid')
    try:
        updated = parsedate_to_datetime(match.group(3))
    except (TypeError, ValueError) as exc:
        raise MediaInspectorServiceError('media_scanner_response_invalid') from exc
    if updated.tzinfo is None:
        updated = updated.replace(tzinfo=UTC)
    age = now().astimezone(UTC) - updated.astimezone(UTC)
    if age > MAX_DEFINITION_AGE or age < -MAX_DEFINITION_FUTURE_SKEW:
        raise MediaInspectorServiceError('media_scanner_definitions_stale')
    return {
        'engine': 'clamav',
        'version': match.group(1),
        'definitionsVersion': match.group(2),
        'definitionsAt': _stamp(updated),
    }


def _scan(
    content: bytes, run: Callable[..., subprocess.CompletedProcess[bytes]] = _fixed_run
) -> str:
    completed = run(
        [
            '/usr/bin/clamscan',
            '--database=/var/lib/clamav',
            '--stdout',
            '--no-summary',
            '-',
        ],
        content=content,
        timeout=25,
        maximum_output=4096,
        scanner_memory=True,
    )
    if completed.returncode == 0 and completed.stdout.endswith(b': OK\n'):
        return 'clean'
    if completed.returncode == 1 and b' FOUND\n' in completed.stdout:
        return 'infected'
    raise MediaInspectorServiceError('media_scanner_response_invalid')


def _decode(
    content: bytes,
    media_type: str,
    run: Callable[..., subprocess.CompletedProcess[bytes]] = _fixed_run,
) -> dict[str, Any]:
    completed = run(
        ['/usr/bin/python', '-m', 'api.services.media_inspector_runner', media_type],
        content=content,
        timeout=25,
        maximum_output=MAX_RUNNER_OUTPUT,
    )
    if completed.returncode != 0:
        raise MediaInspectorServiceError('media_decoder_failed')
    try:
        result = json.loads(completed.stdout)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MediaInspectorServiceError('media_decoder_response_invalid') from exc
    if not isinstance(result, dict) or set(result) != RUNNER_KEYS:
        raise MediaInspectorServiceError('media_decoder_response_invalid')
    return result


def inspect_request(
    request: Any,
    content: bytes,
    *,
    key,
    build_identity: str,
    now: Callable[[], datetime] = _utc_now,
    health_reader: Callable[[], dict[str, Any]] = _scanner_health,
    scanner: Callable[[bytes], str] = _scan,
    decoder: Callable[[bytes, str], dict[str, Any]] = _decode,
) -> tuple[dict[str, Any], bytes]:
    if (
        not isinstance(request, dict)
        or set(request) != REQUEST_KEYS
        or request.get('schemaVersion') != 'base2-media-inspection-request-v1'
    ):
        raise MediaInspectorServiceError('media_inspector_request_invalid')
    if (
        not isinstance(content, bytes)
        or not 1 <= len(content) <= MAX_INPUT_BYTES
        or hashlib.sha256(content).hexdigest() != request.get('sourceSha256')
    ):
        raise MediaInspectorServiceError('media_integrity_failed')
    if not re.fullmatch(r'base2-media-inspector:[a-f0-9]{64}', build_identity or ''):
        raise MediaInspectorServiceError('media_inspector_identity_unavailable')
    started = now()
    before = health_reader()
    if scanner(content) != 'clean':
        raise MediaInspectorServiceError('media_inspection_rejected')
    after = health_reader()
    if before != after:
        raise MediaInspectorServiceError('media_scanner_identity_changed')
    decoded = decoder(content, request['mediaType'])
    try:
        preview = base64.b64decode(decoded['previewBase64'], validate=True)
    except (KeyError, ValueError) as exc:
        raise MediaInspectorServiceError('media_decoder_response_invalid') from exc
    meta = decoded.get('preview')
    if (
        not isinstance(meta, dict)
        or hashlib.sha256(preview).hexdigest() != meta.get('sha256')
        or len(preview) != meta.get('byteSize')
    ):
        raise MediaInspectorServiceError('media_decoder_response_invalid')
    scanner_evidence = dict(after)
    scanner_evidence['verdict'] = 'clean'
    payload = {
        'schemaVersion': 'base2-media-inspection-v1',
        'jobId': request['jobId'],
        'nonce': request['nonce'],
        'assetId': request['assetId'],
        'objectVersion': request['objectVersion'],
        'sourceSha256': request['sourceSha256'],
        'requestedMediaType': request['mediaType'],
        'observedMediaType': decoded['observedMediaType'],
        'decision': 'accepted',
        'scanner': scanner_evidence,
        'decoder': {
            'name': decoded['decoderName'],
            'version': decoded['decoderVersion'],
            'buildIdentity': build_identity,
        },
        'measurements': decoded['measurements'],
        'preview': meta,
        'startedAt': _stamp(started),
        'finishedAt': _stamp(now()),
    }
    return sign_receipt(payload, key), preview


def _atomic_write(path: Path, content: bytes) -> None:
    temporary = path.with_suffix(path.suffix + '.tmp')
    with temporary.open('xb') as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def serve_once(root: Path, *, key, build_identity: str) -> bool:
    for ready in sorted(root.glob('*/ready'), key=lambda item: item.stat().st_mtime):
        job = ready.parent
        try:
            (job / 'claimed').touch(exist_ok=False)
        except FileExistsError:
            continue
        try:
            request_bytes = (job / 'request.json').read_bytes()
            content = (job / 'content.bin').read_bytes()
            if len(request_bytes) > 8192 or len(content) > MAX_INPUT_BYTES:
                raise MediaInspectorServiceError('media_inspector_request_invalid')
            receipt, preview = inspect_request(
                json.loads(request_bytes), content, key=key, build_identity=build_identity
            )
            _atomic_write(job / 'preview.bin', preview)
            _atomic_write(
                job / 'receipt.json',
                json.dumps(receipt, sort_keys=True, separators=(',', ':')).encode('ascii'),
            )
            _atomic_write(job / 'complete', b'1')
        except Exception as exc:
            code = str(exc) if str(exc).startswith('media_') else 'media_inspector_failed'
            # The bounded client may have timed out and removed its private
            # spool directory. That must not terminate the supervisor.
            with contextlib.suppress(OSError):
                _atomic_write(
                    job / 'failed',
                    code.encode('ascii', 'ignore')[:128] or b'media_inspector_failed',
                )
        return True
    return False


def main() -> int:
    if platform.machine().lower() not in {'x86_64', 'amd64'}:
        return 68
    if sys.argv[1:] == ['--healthcheck']:
        try:
            _scanner_health()
        except MediaInspectorServiceError:
            return 73
        return 0
    if os.geteuid() != 0:
        return 69
    if ctypes.CDLL(None).prctl(4, 0, 0, 0, 0) != 0:
        return 70
    try:
        key = load_signing_key(os.getenv('MEDIA_INSPECTOR_SIGNING_KEY', ''))
    except ValueError:
        return 71
    build_identity = os.getenv('MEDIA_INSPECTOR_BUILD_IDENTITY', '')
    if not re.fullmatch(r'base2-media-inspector:[a-f0-9]{64}', build_identity):
        return 72
    try:
        _scanner_health()
    except MediaInspectorServiceError:
        return 73
    root = Path(os.getenv('MEDIA_INSPECTOR_SPOOL_ROOT', '/var/lib/base2/media-inspector'))
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    while True:
        if not serve_once(root, key=key, build_identity=build_identity):
            time.sleep(0.1)


if __name__ == '__main__':
    raise SystemExit(main())
