from __future__ import annotations

import socket
import struct
from collections.abc import Callable


MAX_SCAN_BYTES = 10 * 1024 * 1024
MAX_REPLY_BYTES = 4096
CHUNK_BYTES = 64 * 1024
ALLOWED_HOSTS = {'clamav', '127.0.0.1', '::1'}


class ScannerError(RuntimeError):
    pass


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
