import pytest

from api.services.media_library_processor import (
    MediaProcessorError,
    generate_media_preview,
    normalize_document_probe,
    normalize_probe,
)


def test_audio_and_video_previews_are_deterministic_safe_pngs():
    first = generate_media_preview(content=b"ID3synthetic", media_type="audio/mpeg")
    second = generate_media_preview(content=b"ID3synthetic", media_type="audio/mpeg")
    video = generate_media_preview(content=b"synthetic-video", media_type="video/mp4")
    assert first.content == second.content and first.sha256 == second.sha256
    assert first.media_type == video.media_type == "image/png"
    assert first.content.startswith(b"\x89PNG\r\n\x1a\n")
    assert first.width == video.width == 640
    assert first.height == 160 and video.height == 360


def test_document_probe_rejects_active_content_and_page_exhaustion():
    result = normalize_document_probe(
        {'mediaType': 'application/pdf', 'pageCount': 12, 'activeContent': False},
        tool_ref='pypdf:5.9',
    )
    assert result.page_count == 12 and result.active_content is False
    for payload in (
        {'mediaType': 'application/pdf', 'pageCount': 501, 'activeContent': False},
        {'mediaType': 'application/pdf', 'pageCount': 1, 'activeContent': True},
    ):
        with pytest.raises(MediaProcessorError, match='document_probe_invalid'):
            normalize_document_probe(payload, tool_ref='pypdf:5.9')


def test_empty_audio_cannot_generate_a_waveform():
    with pytest.raises(MediaProcessorError, match='media_content_empty'):
        generate_media_preview(content=b'', media_type='audio/mpeg')


def test_probe_normalization_is_closed_and_bounded():
    result = normalize_probe(
        {
            "mediaType": "video/mp4", "durationSeconds": 90.5,
            "width": 1920, "height": 1080, "streamCount": 2,
        },
        expected_type="video/mp4", tool_ref="ffprobe:7.1",
    )
    assert result.duration_seconds == 90.5 and result.tool_ref == "ffprobe:7.1"


@pytest.mark.parametrize(
    "payload",
    [
        {"mediaType": "video/mp4", "durationSeconds": 999999, "width": 1, "height": 1, "streamCount": 1},
        {"mediaType": "video/mp4", "durationSeconds": 1, "width": 100000, "height": 100000, "streamCount": 1},
        {"mediaType": "video/mp4", "durationSeconds": 1, "width": None, "height": 1, "streamCount": 1},
        {"mediaType": "video/mp4", "durationSeconds": 1, "width": 1, "height": 1, "streamCount": 99},
    ],
)
def test_probe_limits_fail_closed(payload):
    with pytest.raises(MediaProcessorError):
        normalize_probe(payload, expected_type="video/mp4", tool_ref="ffprobe:7.1")
