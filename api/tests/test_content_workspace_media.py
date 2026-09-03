from __future__ import annotations

import pytest

from api.services.content_workspace_media import (
    MAX_UPLOAD_BYTES,
    MediaAdmissionError,
    admit_upload,
    apply_scan_result,
)


def png(*, width: int = 1, height: int = 1, tail: bytes = b'fixture') -> bytes:
    return (
        b'\x89PNG\r\n\x1a\n'
        + (13).to_bytes(4, 'big')
        + b'IHDR'
        + width.to_bytes(4, 'big')
        + height.to_bytes(4, 'big')
        + b'\x08\x06\x00\x00\x00'
        + b'\x00\x00\x00\x00'
        + tail
    )


def webp(*, width: int = 20, height: int = 10) -> bytes:
    content = bytearray(b'RIFF' + (22).to_bytes(4, 'little') + b'WEBPVP8X' + b'\x00' * 14)
    content[24:27] = (width - 1).to_bytes(3, 'little')
    content[27:30] = (height - 1).to_bytes(3, 'little')
    return bytes(content)


def jpeg(*, width: int = 20, height: int = 10) -> bytes:
    return (
        b'\xff\xd8'
        b'\xff\xd8'
        b'\xff\xe0\x00\x04\x00\x00'
        b'\xff\xc0\x00\x07\x08'
        + height.to_bytes(2, 'big')
        + width.to_bytes(2, 'big')
    )


def test_safe_media_is_content_addressed_and_starts_quarantined():
    admitted = admit_upload(
        filename='synthetic.png', claimed_type='image/png', content=png(width=20, height=10)
    )
    assert admitted.state == 'quarantined'
    assert admitted.safe_name == 'synthetic.png'
    assert (admitted.width, admitted.height) == (20, 10)
    assert len(admitted.sha256) == 64


@pytest.mark.parametrize(
    ('filename', 'media_type', 'content', 'dimensions'),
    [
        ('synthetic.webp', 'image/webp', webp(), (20, 10)),
        ('synthetic.jpg', 'image/jpeg', jpeg(), (20, 10)),
        ('synthetic.pdf', 'application/pdf', b'%PDF-1.7\nsafe', (None, None)),
    ],
)
def test_all_allowed_media_types_are_structurally_admitted(
    filename, media_type, content, dimensions
):
    admitted = admit_upload(filename=filename, claimed_type=media_type, content=content)
    assert (admitted.width, admitted.height) == dimensions
    assert admitted.media_type == media_type and admitted.byte_size == len(content)


@pytest.mark.parametrize(
    ('filename', 'media_type', 'content', 'code'),
    [
        (None, 'image/png', png(), 'content_media_filename_invalid'),
        ('empty.png', 'image/png', b'', 'content_limit_exceeded'),
        ('type.png', 'image/png', 'not-bytes', 'content_limit_exceeded'),
        ('header.png', 'image/png', b'\x89PNG\r\n\x1a\n' + b'x' * 25, 'content_media_signature_invalid'),
        ('short.webp', 'image/webp', b'RIFF\x00\x00\x00\x00WEBP', 'content_media_signature_invalid'),
        (
            'kind.webp',
            'image/webp',
            b'RIFF\x16\x00\x00\x00WEBPBAD!' + b'\x00' * 14,
            'content_media_signature_invalid',
        ),
        ('body.jpg', 'image/jpeg', b'\xff\xd8not-a-marker', 'content_media_signature_invalid'),
        ('length.jpg', 'image/jpeg', b'\xff\xd8\xff\xe0\x00\x20short', 'content_media_signature_invalid'),
        ('sof.jpg', 'image/jpeg', b'\xff\xd8\xff\xc0\x00\x06xxxx', 'content_media_signature_invalid'),
        ('width.webp', 'image/webp', webp(width=12_001), 'content_media_dimensions_invalid'),
        ('pixels.webp', 'image/webp', webp(width=10_000, height=10_000), 'content_media_dimensions_invalid'),
    ],
)
def test_media_parser_closes_every_malformed_structural_branch(filename, media_type, content, code):
    with pytest.raises(MediaAdmissionError, match=code):
        admit_upload(filename=filename, claimed_type=media_type, content=content)


@pytest.mark.parametrize(
    ('filename', 'media_type', 'content'),
    [
        ('../escape.png', 'image/png', png()),
        ('escape\\file.png', 'image/png', png()),
        ('active.svg', 'image/svg+xml', b'<svg><script>alert(1)</script></svg>'),
        ('spoof.png', 'image/png', b'MZ executable'),
        ('polyglot.pdf', 'application/pdf', b'%PDF-1.7\n<script>bad</script>'),
        ('bomb.png', 'image/png', b'\x89PNG\r\n\x1a\n' + b'x' * MAX_UPLOAD_BYTES),
    ],
)
def test_hostile_names_types_spoofs_active_content_and_oversize_fail_closed(
    filename, media_type, content
):
    with pytest.raises(MediaAdmissionError):
        admit_upload(filename=filename, claimed_type=media_type, content=content)


def test_remote_url_is_not_an_admission_input():
    with pytest.raises(TypeError):
        admit_upload(
            filename='x.png', claimed_type='image/png', remote_url='https://example.test/x'
        )


def test_pixel_bombs_truncated_images_and_late_active_payloads_fail_closed():
    for content in (
        png(width=20_000, height=20_000),
        b'\x89PNG\r\n\x1a\ntruncated',
        png(tail=b'x' * 5000 + b'<script>late</script>'),
    ):
        with pytest.raises(MediaAdmissionError):
            admit_upload(filename='unsafe.png', claimed_type='image/png', content=content)


def test_scan_results_are_closed_content_bound_and_never_promote_without_derivative():
    admitted = admit_upload(filename='synthetic.png', claimed_type='image/png', content=png())
    clean = apply_scan_result(admitted, outcome='clean', scanned_sha256=admitted.sha256)
    assert clean.state == 'quarantined'
    assert apply_scan_result(
        admitted, outcome='infected', scanned_sha256=admitted.sha256
    ).state == ('rejected')
    assert apply_scan_result(admitted, outcome='error', scanned_sha256=admitted.sha256).state == (
        'quarantined'
    )
    with pytest.raises(MediaAdmissionError, match='content_integrity_failed'):
        apply_scan_result(admitted, outcome='clean', scanned_sha256='0' * 64)
    with pytest.raises(MediaAdmissionError, match='content_media_scan_invalid'):
        apply_scan_result(admitted, outcome='unknown', scanned_sha256=admitted.sha256)
