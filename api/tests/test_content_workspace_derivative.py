from __future__ import annotations

import io

import pytest
from PIL import Image
from pypdf import PdfReader, PdfWriter

from api.services.content_workspace_derivative import (
    MAX_IMAGE_EDGE,
    DerivativeError,
    generate_safe_derivative,
)


def image_fixture(format_name: str, *, size=(20, 10), metadata=True) -> bytes:
    output = io.BytesIO()
    image = Image.new('RGB', size, color=(32, 64, 96))
    kwargs = {'exif': b'unsafe-private-metadata'} if metadata and format_name == 'JPEG' else {}
    image.save(output, format=format_name, **kwargs)
    return output.getvalue()


@pytest.mark.parametrize(
    ('media_type', 'format_name'),
    [('image/jpeg', 'JPEG'), ('image/png', 'PNG'), ('image/webp', 'WEBP')],
)
def test_images_are_decoded_bounded_and_reencoded_as_metadata_free_png(media_type, format_name):
    derivative = generate_safe_derivative(
        content=image_fixture(format_name, size=(2400, 1200)), media_type=media_type
    )
    assert derivative.media_type == 'image/png'
    assert derivative.width == MAX_IMAGE_EDGE
    assert derivative.height == MAX_IMAGE_EDGE // 2
    assert b'unsafe-private-metadata' not in derivative.content
    with Image.open(io.BytesIO(derivative.content)) as decoded:
        assert decoded.format == 'PNG'
        assert decoded.n_frames == 1
        assert 'exif' not in decoded.info


def test_pdf_is_rewritten_without_metadata_or_document_actions():
    source = io.BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.add_metadata({'/Author': 'private author'})
    writer.write(source)

    derivative = generate_safe_derivative(content=source.getvalue(), media_type='application/pdf')
    assert derivative.media_type == 'application/pdf'
    assert b'private author' not in derivative.content
    parsed = PdfReader(io.BytesIO(derivative.content), strict=True)
    assert len(parsed.pages) == 1
    assert not parsed.metadata


@pytest.mark.parametrize(
    ('content', 'media_type', 'code'),
    [
        (b'not an image', 'image/png', 'content_media_derivative_invalid'),
        (b'%PDF-1.7\n/JavaScript', 'application/pdf', 'content_media_active_document'),
        (b'%PDF-1.7', 'text/plain', 'content_media_type_invalid'),
    ],
)
def test_malformed_active_and_unapproved_derivatives_fail_closed(content, media_type, code):
    with pytest.raises(DerivativeError, match=code):
        generate_safe_derivative(content=content, media_type=media_type)
