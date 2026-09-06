import hashlib

import pytest

from api.services.content_workspace_media import MediaAdmissionError, admit_upload


@pytest.mark.parametrize(
    ("filename", "media_type", "content"),
    [
        ("episode.mp3", "audio/mpeg", b"ID3\x04\x00\x00\x00\x00\x00\x00safe-audio"),
        ("voice.ogg", "audio/ogg", b"OggS\x00\x02safe-audio"),
        ("clip.mp4", "video/mp4", b"\x00\x00\x00\x18ftypisom\x00\x00\x00\x00safe-video"),
        ("clip.webm", "video/webm", b"\x1aE\xdf\xa3safe-video"),
    ],
)
def test_mixed_media_signatures_enter_quarantine(filename, media_type, content):
    result = admit_upload(filename=filename, claimed_type=media_type, content=content)
    assert result.state == "quarantined"
    assert result.sha256 == hashlib.sha256(content).hexdigest()
    assert result.width is None and result.height is None


@pytest.mark.parametrize(
    ("media_type", "content"),
    [
        ("audio/mpeg", b"not-an-mp3"),
        ("audio/ogg", b"not-an-ogg"),
        ("video/mp4", b"\x00\x00\x00\x18ftypqt  unsafe"),
        ("video/webm", b"not-webm"),
        ("audio/mpeg", b"ID3safe<script>alert(1)</script>"),
    ],
)
def test_mixed_media_spoofing_and_active_payloads_fail_closed(media_type, content):
    with pytest.raises(MediaAdmissionError):
        admit_upload(filename="safe.bin", claimed_type=media_type, content=content)
