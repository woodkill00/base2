"""Deterministic safe previews and closed external-probe normalization."""

from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass
from typing import Any

from PIL import Image, ImageDraw

from api.services.content_workspace_derivative import SafeDerivative, generate_safe_derivative


MAX_DURATION_SECONDS = 8 * 60 * 60
MAX_VIDEO_PIXELS = 3840 * 2160


class MediaProcessorError(ValueError):
    pass


@dataclass(frozen=True)
class ProbeResult:
    media_type: str
    duration_seconds: float | None
    width: int | None
    height: int | None
    stream_count: int
    tool_ref: str


def normalize_probe(payload: Any, *, expected_type: str, tool_ref: str) -> ProbeResult:
    """Admit only the small typed subset produced by a sandboxed probe process."""
    if (
        not isinstance(payload, dict)
        or set(payload) != {"mediaType", "durationSeconds", "width", "height", "streamCount"}
        or payload.get("mediaType") != expected_type
        or not isinstance(tool_ref, str)
        or not tool_ref.startswith("ffprobe:")
        or len(tool_ref) > 64
    ):
        raise MediaProcessorError("media_probe_invalid")
    duration = payload["durationSeconds"]
    width, height, streams = payload["width"], payload["height"], payload["streamCount"]
    if (
        duration is not None
        and (isinstance(duration, bool) or not isinstance(duration, (int, float)) or not 0 < duration <= MAX_DURATION_SECONDS)
    ):
        raise MediaProcessorError("media_duration_limit_exceeded")
    if (
        not isinstance(streams, int)
        or isinstance(streams, bool)
        or not 1 <= streams <= 16
        or (width is None) != (height is None)
    ):
        raise MediaProcessorError("media_probe_invalid")
    if width is not None and (
        not isinstance(width, int)
        or isinstance(width, bool)
        or not isinstance(height, int)
        or isinstance(height, bool)
        or width < 1
        or height < 1
        or width * height > MAX_VIDEO_PIXELS
    ):
        raise MediaProcessorError("media_dimensions_limit_exceeded")
    return ProbeResult(expected_type, float(duration) if duration is not None else None, width, height, streams, tool_ref)


def _placeholder(content: bytes, label: str) -> SafeDerivative:
    digest = hashlib.sha256(content).digest()
    background = tuple(24 + value % 72 for value in digest[:3])
    accent = tuple(150 + value % 90 for value in digest[3:6])
    image = Image.new("RGB", (640, 360), background)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((48, 48, 592, 312), radius=28, outline=accent, width=8)
    draw.text((64, 162), label, fill=accent, stroke_width=0)
    output = io.BytesIO()
    image.save(output, format="PNG", compress_level=9, optimize=False)
    return SafeDerivative(output.getvalue(), "image/png", 640, 360)


def generate_media_preview(*, content: bytes, media_type: str) -> SafeDerivative:
    if media_type in {"image/jpeg", "image/png", "image/webp", "application/pdf"}:
        return generate_safe_derivative(content=content, media_type=media_type)
    if media_type in {"audio/mpeg", "audio/ogg"}:
        return _placeholder(content, "AUDIO PREVIEW")
    if media_type in {"video/mp4", "video/webm"}:
        return _placeholder(content, "VIDEO PREVIEW")
    raise MediaProcessorError("media_type_invalid")
