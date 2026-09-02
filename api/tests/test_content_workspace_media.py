from __future__ import annotations

import pytest

from api.services.content_workspace_media import (
    MAX_UPLOAD_BYTES,
    MediaAdmissionError,
    admit_upload,
)


def test_safe_media_is_content_addressed_and_starts_quarantined():
    admitted = admit_upload(
        filename='synthetic.png', claimed_type='image/png', content=b'\x89PNG\r\n\x1a\nfixture'
    )
    assert admitted.state == 'quarantined'
    assert admitted.safe_name == 'synthetic.png'
    assert len(admitted.sha256) == 64


@pytest.mark.parametrize(
    ('filename', 'media_type', 'content'),
    [
        ('../escape.png', 'image/png', b'\x89PNG\r\n\x1a\nfixture'),
        ('escape\\file.png', 'image/png', b'\x89PNG\r\n\x1a\nfixture'),
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
