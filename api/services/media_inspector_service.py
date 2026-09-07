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
import stat
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
        # Loading the signed ClamAV database is deliberately bounded but can
        # take around 40 seconds on the fixed low-cost preview profile.
        timeout=50,
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


def _read_spool_file(
    job_fd: int, name: str, maximum: int, *, owner_uid: int, owner_gid: int
) -> bytes:
    try:
        descriptor = os.open(
            name,
            os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK,
            dir_fd=job_fd,
        )
    except OSError as exc:
        raise MediaInspectorServiceError('media_inspector_request_invalid') from exc
    with os.fdopen(descriptor, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != owner_uid
            or info.st_gid != owner_gid
            or stat.S_IMODE(info.st_mode) not in {0o600, 0o640}
            or not 1 <= info.st_size <= maximum
        ):
            raise MediaInspectorServiceError('media_inspector_request_invalid')
        content = stream.read(maximum + 1)
    if len(content) > maximum:
        raise MediaInspectorServiceError('media_inspector_request_invalid')
    return content


MAX_SPOOL_SCAN_ENTRIES = 256
MAX_CLIENT_WAIT_SECONDS = 60
MAX_INSPECTION_RUNTIME_SECONDS = 60
RECOVERY_SAFETY_MARGIN_SECONDS = 60
CLAIM_STALE_SECONDS = (
    MAX_CLIENT_WAIT_SECONDS
    + MAX_INSPECTION_RUNTIME_SECONDS
    + RECOVERY_SAFETY_MARGIN_SECONDS
)
RECOVERABLE_TEMP_LIMITS = {
    'preview.bin.tmp': 10 * 1024 * 1024,
    'receipt.json.tmp': 32 * 1024,
    'complete.tmp': 1,
    'failed.tmp': 128,
}
_SCAN_CURSOR: tuple[tuple[int, int], Any] | None = None


def _reset_scan_cursor() -> None:
    global _SCAN_CURSOR
    if _SCAN_CURSOR is not None:
        _SCAN_CURSOR[1].close()
        _SCAN_CURSOR = None


def _next_scan_window(root_fd: int) -> list[os.DirEntry[str]]:
    """Return a bounded persistent directory window and close at EOF."""
    global _SCAN_CURSOR
    root_info = os.fstat(root_fd)
    identity = (root_info.st_dev, root_info.st_ino)
    if _SCAN_CURSOR is None or _SCAN_CURSOR[0] != identity:
        _reset_scan_cursor()
        _SCAN_CURSOR = (identity, os.scandir(root_fd))
    iterator = _SCAN_CURSOR[1]
    window: list[os.DirEntry[str]] = []
    for _ in range(MAX_SPOOL_SCAN_ENTRIES):
        try:
            window.append(next(iterator))
        except StopIteration:
            _reset_scan_cursor()
            break
    return window


def _recover_stale_claim(
    job_fd: int,
    *,
    owner_uid: int,
    owner_gid: int,
    now_seconds: float,
) -> bool:
    """Remove only an exact stale local claim and its bounded safe temp files."""
    try:
        claimed = os.stat('claimed', dir_fd=job_fd, follow_symlinks=False)
    except FileNotFoundError:
        return False
    except OSError:
        return False
    cutoff = now_seconds - CLAIM_STALE_SECONDS
    if (
        not stat.S_ISREG(claimed.st_mode)
        or claimed.st_uid != owner_uid
        or claimed.st_gid != owner_gid
        or stat.S_IMODE(claimed.st_mode) != 0o600
        or claimed.st_size != 0
        or claimed.st_mtime > cutoff
    ):
        return False
    names: list[str] = []
    try:
        with os.scandir(job_fd) as entries:
            for entry in entries:
                names.append(entry.name)
                if len(names) > 16:
                    return False
    except OSError:
        return False
    if any(name in names for name in ('complete', 'failed')):
        return False
    temp_names = [name for name in names if name.endswith('.tmp')]
    if any(name not in RECOVERABLE_TEMP_LIMITS for name in temp_names):
        return False
    for name in temp_names:
        try:
            info = os.stat(name, dir_fd=job_fd, follow_symlinks=False)
        except OSError:
            return False
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != owner_uid
            or info.st_gid != owner_gid
            or stat.S_IMODE(info.st_mode) != 0o600
            or info.st_size > RECOVERABLE_TEMP_LIMITS[name]
            or info.st_mtime > cutoff
        ):
            return False
    try:
        for name in temp_names:
            os.unlink(name, dir_fd=job_fd)
        os.unlink('claimed', dir_fd=job_fd)
    except OSError:
        return False
    return True


def _atomic_write_at(
    job_fd: int, name: str, content: bytes, *, owner_uid: int, owner_gid: int
) -> None:
    temporary = name + '.tmp'
    original_euid = os.geteuid()
    original_egid = os.getegid()
    try:
        if original_egid != owner_gid:
            os.setegid(owner_gid)
        if original_euid != owner_uid:
            os.seteuid(owner_uid)
        descriptor = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
            0o600,
            dir_fd=job_fd,
        )
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, name, src_dir_fd=job_fd, dst_dir_fd=job_fd)
    finally:
        if os.geteuid() != original_euid:
            os.seteuid(original_euid)
        if os.getegid() != original_egid:
            os.setegid(original_egid)


def _job_candidates(root_fd: int, *, owner_uid: int, owner_gid: int) -> list[str]:
    candidates: list[tuple[int, str]] = []
    for entry in _next_scan_window(root_fd):
        try:
            job_info = entry.stat(follow_symlinks=False)
            if (
                not stat.S_ISDIR(job_info.st_mode)
                or job_info.st_uid != owner_uid
                or job_info.st_gid != owner_gid
                or stat.S_IMODE(job_info.st_mode) not in {0o700, 0o770}
            ):
                continue
            job_fd = os.open(
                entry.name,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                dir_fd=root_fd,
            )
            try:
                ready_info = os.stat('ready', dir_fd=job_fd, follow_symlinks=False)
            finally:
                os.close(job_fd)
        except OSError:
            continue
        if (
            stat.S_ISREG(ready_info.st_mode)
            and ready_info.st_uid == owner_uid
            and ready_info.st_gid == owner_gid
            and stat.S_IMODE(ready_info.st_mode) in {0o600, 0o640}
            and ready_info.st_size == 1
        ):
            candidates.append((ready_info.st_mtime_ns, entry.name))
    return [name for _, name in sorted(candidates)]


def _has_terminal(job_fd: int) -> bool:
    for name in ('complete', 'failed'):
        try:
            os.stat(name, dir_fd=job_fd, follow_symlinks=False)
        except FileNotFoundError:
            continue
        except OSError:
            return True
        return True
    return False


def serve_once(
    root: Path, *, key, build_identity: str, producer_uid: int, producer_gid: int
) -> bool:
    root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        for name in _job_candidates(root_fd, owner_uid=producer_uid, owner_gid=producer_gid):
            job_fd: int | None = None
            try:
                job_fd = os.open(
                    name,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                    dir_fd=root_fd,
                )
                job_info = os.fstat(job_fd)
                if (
                    job_info.st_uid != producer_uid
                    or job_info.st_gid != producer_gid
                    or stat.S_IMODE(job_info.st_mode) not in {0o700, 0o770}
                    or not stat.S_ISDIR(job_info.st_mode)
                ):
                    os.close(job_fd)
                    job_fd = None
                    continue
                if _has_terminal(job_fd):
                    os.close(job_fd)
                    job_fd = None
                    continue
                _recover_stale_claim(
                    job_fd,
                    owner_uid=producer_uid,
                    owner_gid=producer_gid,
                    now_seconds=time.time(),
                )
                original_euid = os.geteuid()
                original_egid = os.getegid()
                try:
                    if original_egid != producer_gid:
                        os.setegid(producer_gid)
                    if original_euid != producer_uid:
                        os.seteuid(producer_uid)
                    claimed_fd = os.open(
                        'claimed',
                        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                        0o600,
                        dir_fd=job_fd,
                    )
                    os.close(claimed_fd)
                finally:
                    if os.geteuid() != original_euid:
                        os.seteuid(original_euid)
                    if os.getegid() != original_egid:
                        os.setegid(original_egid)
            except OSError:
                if job_fd is not None:
                    os.close(job_fd)
                continue
            assert job_fd is not None
            try:
                _read_spool_file(
                    job_fd, 'ready', 1, owner_uid=producer_uid, owner_gid=producer_gid
                )
                request_bytes = _read_spool_file(
                    job_fd,
                    'request.json',
                    8192,
                    owner_uid=producer_uid,
                    owner_gid=producer_gid,
                )
                content = _read_spool_file(
                    job_fd,
                    'content.bin',
                    MAX_INPUT_BYTES,
                    owner_uid=producer_uid,
                    owner_gid=producer_gid,
                )
                receipt, preview = inspect_request(
                    json.loads(request_bytes), content, key=key, build_identity=build_identity
                )
                _atomic_write_at(
                    job_fd,
                    'preview.bin',
                    preview,
                    owner_uid=producer_uid,
                    owner_gid=producer_gid,
                )
                _atomic_write_at(
                    job_fd,
                    'receipt.json',
                    json.dumps(receipt, sort_keys=True, separators=(',', ':')).encode('ascii'),
                    owner_uid=producer_uid,
                    owner_gid=producer_gid,
                )
                _atomic_write_at(
                    job_fd,
                    'complete',
                    b'1',
                    owner_uid=producer_uid,
                    owner_gid=producer_gid,
                )
            except Exception as exc:
                code = str(exc) if str(exc).startswith('media_') else 'media_inspector_failed'
                # The bounded client may have timed out and removed its private
                # spool directory. That must not terminate the supervisor.
                with contextlib.suppress(OSError):
                    _atomic_write_at(
                        job_fd,
                        'failed',
                        code.encode('ascii', 'ignore')[:128] or b'media_inspector_failed',
                        owner_uid=producer_uid,
                        owner_gid=producer_gid,
                    )
            finally:
                os.close(job_fd)
            return True
        return False
    finally:
        os.close(root_fd)


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
    try:
        producer_uid = int(os.getenv('MEDIA_INSPECTOR_SPOOL_PRODUCER_UID', ''))
        producer_gid = int(os.getenv('MEDIA_INSPECTOR_SPOOL_PRODUCER_GID', ''))
    except ValueError:
        return 74
    if not 0 <= producer_uid <= 2**32 - 2 or not 0 <= producer_gid <= 2**32 - 2:
        return 74
    root = Path(os.getenv('MEDIA_INSPECTOR_SPOOL_ROOT', '/var/lib/base2/media-inspector'))
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    while True:
        if not serve_once(
            root,
            key=key,
            build_identity=build_identity,
            producer_uid=producer_uid,
            producer_gid=producer_gid,
        ):
            time.sleep(0.1)


if __name__ == '__main__':
    raise SystemExit(main())
