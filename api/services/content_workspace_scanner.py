from __future__ import annotations

import socket
import struct
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from collections.abc import Callable


MAX_SCAN_BYTES = 100 * 1024 * 1024
MAX_REPLY_BYTES = 4096
CHUNK_BYTES = 64 * 1024
ALLOWED_HOSTS = {'clamav', '127.0.0.1', '::1'}


class ScannerError(RuntimeError):
    pass


@dataclass(frozen=True)
class ScannerHealth:
    engine: str
    engine_version: str
    definitions_version: str
    definitions_updated_at: datetime


VERSION_REPLY = re.compile(
    rb'^ClamAV (?P<engine>[0-9][A-Za-z0-9._-]{0,31})/'
    rb'(?P<definitions>[0-9]{1,12})/(?P<updated>[^\x00\r\n]{8,80})$'
)


def clamav_health(
    *,
    host: str = 'clamav',
    port: int = 3310,
    timeout: float = 5.0,
    connector: Callable = socket.create_connection,
) -> ScannerHealth:
    """Read and strictly normalize the scanner identity and definition timestamp."""
    if host not in ALLOWED_HOSTS or port != 3310 or not 0.1 <= timeout <= 10.0:
        raise ScannerError('content_scanner_request_invalid')
    try:
        with connector((host, port), timeout) as stream:
            stream.sendall(b'zVERSION\0')
            response = bytearray()
            while len(response) <= MAX_REPLY_BYTES:
                received = stream.recv(min(1024, MAX_REPLY_BYTES + 1 - len(response)))
                if not received:
                    break
                response.extend(received)
                if b'\0' in received:
                    break
    except OSError as exc:
        raise ScannerError('content_scanner_unavailable') from exc
    if len(response) > MAX_REPLY_BYTES:
        raise ScannerError('content_scanner_response_invalid')
    reply = bytes(response).split(b'\0', 1)[0]
    match = VERSION_REPLY.fullmatch(reply)
    if match is None:
        raise ScannerError('content_scanner_response_invalid')
    try:
        updated = parsedate_to_datetime(match.group('updated').decode('ascii'))
    except (TypeError, ValueError, UnicodeDecodeError) as exc:
        raise ScannerError('content_scanner_response_invalid') from exc
    if updated.tzinfo is None:
        updated = updated.replace(tzinfo=UTC)
    return ScannerHealth(
        engine='clamav',
        engine_version=match.group('engine').decode('ascii'),
        definitions_version=match.group('definitions').decode('ascii'),
        definitions_updated_at=updated.astimezone(UTC),
    )


def scan_content(
    content: bytes,
    *,
    host: str = 'clamav',
    port: int = 3310,
    timeout: float = 10.0,
    connector: Callable = socket.create_connection,
) -> str:
    """Stream one bounded payload to an internal clamd and return a closed verdict."""
    if (
        host not in ALLOWED_HOSTS
        or port != 3310
        or not 1 <= len(content) <= MAX_SCAN_BYTES
        or not 0.1 <= timeout <= 30.0
    ):
        raise ScannerError('content_scanner_request_invalid')
    try:
        with connector((host, port), timeout) as stream:
            stream.sendall(b'zINSTREAM\0')
            for offset in range(0, len(content), CHUNK_BYTES):
                chunk = content[offset : offset + CHUNK_BYTES]
                stream.sendall(struct.pack('>I', len(chunk)) + chunk)
            stream.sendall(struct.pack('>I', 0))
            response = bytearray()
            while len(response) <= MAX_REPLY_BYTES:
                received = stream.recv(min(1024, MAX_REPLY_BYTES + 1 - len(response)))
                if not received:
                    break
                response.extend(received)
                if b'\0' in received:
                    break
    except OSError as exc:
        raise ScannerError('content_scanner_unavailable') from exc
    if len(response) > MAX_REPLY_BYTES:
        raise ScannerError('content_scanner_response_invalid')
    verdict = bytes(response).split(b'\0', 1)[0]
    if verdict == b'stream: OK':
        return 'clean'
    if verdict.startswith(b'stream: ') and verdict.endswith(b' FOUND'):
        return 'infected'
    raise ScannerError('content_scanner_response_invalid')
