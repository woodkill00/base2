"""One-shot hostile-byte decoder, executed only in the networkless inspector."""

from __future__ import annotations
import base64
import hashlib
import importlib.metadata
import json
import subprocess
import sys
from api.services.media_library_parser import probe_media_no_network
from api.services.media_library_processor import generate_media_preview

ALLOWED_TYPES = {
    'image/jpeg',
    'image/png',
    'image/webp',
    'application/pdf',
    'audio/mpeg',
    'audio/ogg',
    'video/mp4',
    'video/webm',
}
MAX_INPUT_BYTES = 100 * 1024 * 1024


def _ffprobe_version() -> str:
    completed = subprocess.run(
        ['/usr/bin/ffprobe', '-version'],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        timeout=3,
        check=False,
        shell=False,
        close_fds=True,
        env={'PATH': '/usr/bin:/bin', 'LC_ALL': 'C', 'HOME': '/nonexistent'},
    )
    first = (
        completed.stdout.splitlines()[0].decode('ascii')
        if completed.returncode == 0 and completed.stdout
        else ''
    )
    parts = first.split()
    if len(parts) < 3 or parts[:2] != ['ffprobe', 'version']:
        raise ValueError('media_decoder_identity_invalid')
    return parts[2][:64]


def decode(content: bytes, media_type: str) -> dict:
    if media_type not in ALLOWED_TYPES or not 1 <= len(content) <= MAX_INPUT_BYTES:
        raise ValueError('media_inspector_request_invalid')
    measurements: dict[str, int | float] = {}
    if media_type.startswith(('audio/', 'video/')):
        probe = probe_media_no_network(content, media_type)
        if probe.duration_seconds is not None:
            measurements['durationSeconds'] = probe.duration_seconds
        measurements['streams'] = probe.stream_count
        if probe.width is not None and probe.height is not None:
            measurements['pixels'] = probe.width * probe.height
        decoder_name, decoder_version = 'ffprobe', _ffprobe_version()
    elif media_type == 'application/pdf':
        decoder_name, decoder_version = 'pypdf', importlib.metadata.version('pypdf')
    else:
        decoder_name, decoder_version = 'pillow', importlib.metadata.version('Pillow')
    preview = generate_media_preview(content=content, media_type=media_type)
    if preview.width is not None and preview.height is not None:
        measurements['pixels'] = preview.width * preview.height
    return {
        'decoderName': decoder_name,
        'decoderVersion': decoder_version,
        'observedMediaType': media_type,
        'measurements': measurements,
        'preview': {
            'mediaType': preview.media_type,
            'sha256': preview.sha256,
            'byteSize': len(preview.content),
            'width': preview.width,
            'height': preview.height,
        },
        'previewBase64': base64.b64encode(preview.content).decode('ascii'),
    }


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in ALLOWED_TYPES:
        return 64
    content = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
    try:
        result = decode(content, sys.argv[1])
    except Exception:
        return 66
    if (
        hashlib.sha256(base64.b64decode(result['previewBase64'])).hexdigest()
        != result['preview']['sha256']
    ):
        return 67
    sys.stdout.write(json.dumps(result, sort_keys=True, separators=(',', ':')))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
