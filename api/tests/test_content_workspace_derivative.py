from __future__ import annotations

import io

import pytest
from PIL import Image
from pypdf import PdfReader, PdfWriter

from api.services import content_workspace_derivative as derivative_service
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
    assert len(derivative.sha256) == 64
    assert b'unsafe-private-metadata' not in derivative.content
    with Image.open(io.BytesIO(derivative.content)) as decoded:
        assert decoded.format == 'PNG'
        assert decoded.n_frames == 1
        assert 'exif' not in decoded.info


def test_alpha_images_preserve_alpha_in_the_safe_png():
    output = io.BytesIO()
    Image.new('RGBA', (2, 2), color=(32, 64, 96, 128)).save(output, format='PNG')
    derivative = generate_safe_derivative(content=output.getvalue(), media_type='image/png')
    with Image.open(io.BytesIO(derivative.content)) as decoded:
        assert decoded.mode == 'RGBA'


def test_declared_image_format_mismatch_and_output_bound_fail_closed(monkeypatch):
    with pytest.raises(DerivativeError, match='content_media_derivative_invalid'):
        generate_safe_derivative(content=image_fixture('PNG'), media_type='image/jpeg')

    monkeypatch.setattr(derivative_service, 'MAX_DERIVATIVE_BYTES', 1)
    with pytest.raises(DerivativeError, match='content_media_derivative_too_large'):
        derivative_service._image_derivative(image_fixture('PNG'), 'image/png')


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


def test_encrypted_and_oversized_pdf_derivatives_fail_closed(monkeypatch):
    source = io.BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.encrypt('synthetic-password')
    writer.write(source)
    with pytest.raises(DerivativeError, match='content_media_derivative_invalid'):
        generate_safe_derivative(content=source.getvalue(), media_type='application/pdf')

    source = io.BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.write(source)
    monkeypatch.setattr(derivative_service, 'MAX_DERIVATIVE_BYTES', 1)
    with pytest.raises(DerivativeError, match='content_media_derivative_invalid'):
        derivative_service._pdf_derivative(source.getvalue())


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


@pytest.mark.parametrize('content', [b'', 'not-bytes'])
def test_empty_and_nonbyte_derivative_inputs_fail_the_size_boundary(content):
    with pytest.raises(DerivativeError, match='content_limit_exceeded'):
        generate_safe_derivative(content=content, media_type='image/png')
