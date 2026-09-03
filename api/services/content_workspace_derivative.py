from __future__ import annotations

import hashlib
import io
import re
import warnings
from dataclasses import dataclass

from PIL import Image, UnidentifiedImageError
from pypdf import PdfReader, PdfWriter
from pypdf.errors import PdfReadError


MAX_DERIVATIVE_BYTES = 10 * 1024 * 1024
MAX_IMAGE_PIXELS = 40_000_000
MAX_IMAGE_EDGE = 1600
MAX_PDF_PAGES = 200
IMAGE_FORMATS = {
    'image/jpeg': 'JPEG',
    'image/png': 'PNG',
    'image/webp': 'WEBP',
}
ACTIVE_PDF_TOKEN = re.compile(
    rb'/(?:JavaScript|JS|OpenAction|AA|Launch|EmbeddedFiles?|RichMedia|AcroForm|XFA|'
    rb'SubmitForm|ImportData|GoToR)\b',
    re.IGNORECASE,
)


class DerivativeError(ValueError):
    pass


@dataclass(frozen=True)
class SafeDerivative:
    content: bytes
    media_type: str
    width: int | None
    height: int | None

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.content).hexdigest()


def _image_derivative(content: bytes, media_type: str) -> SafeDerivative:
    previous_limit = Image.MAX_IMAGE_PIXELS
    Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(content)) as source:
                if (
                    source.format != IMAGE_FORMATS[media_type]
                    or getattr(source, 'n_frames', 1) != 1
                ):
                    raise DerivativeError('content_media_derivative_invalid')
                source.load()
                source.thumbnail((MAX_IMAGE_EDGE, MAX_IMAGE_EDGE), Image.Resampling.LANCZOS)
                has_alpha = source.mode in {'RGBA', 'LA'} or (
                    source.mode == 'P' and 'transparency' in source.info
                )
                rendered = source.convert('RGBA' if has_alpha else 'RGB')
                output = io.BytesIO()
                rendered.save(output, format='PNG', compress_level=9, optimize=False)
                result = output.getvalue()
                width, height = rendered.size
    except (OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombError) as exc:
        if isinstance(exc, DerivativeError):
            raise
        raise DerivativeError('content_media_derivative_invalid') from exc
    finally:
        Image.MAX_IMAGE_PIXELS = previous_limit
    if not result or len(result) > MAX_DERIVATIVE_BYTES:
        raise DerivativeError('content_media_derivative_too_large')
    return SafeDerivative(result, 'image/png', width, height)


def _pdf_derivative(content: bytes) -> SafeDerivative:
    if ACTIVE_PDF_TOKEN.search(content):
        raise DerivativeError('content_media_active_document')
    try:
        reader = PdfReader(io.BytesIO(content), strict=True)
        if reader.is_encrypted or not 1 <= len(reader.pages) <= MAX_PDF_PAGES:
            raise DerivativeError('content_media_derivative_invalid')
        writer = PdfWriter()
        for source_page in reader.pages:
            source_page.pop('/Annots', None)
            source_page.pop('/AA', None)
            writer.add_page(source_page)
        writer.metadata = None
        output = io.BytesIO()
        writer.write(output)
        result = output.getvalue()
    except (OSError, ValueError, PdfReadError) as exc:
        if isinstance(exc, DerivativeError):
            raise
        raise DerivativeError('content_media_derivative_invalid') from exc
    if not result or len(result) > MAX_DERIVATIVE_BYTES or ACTIVE_PDF_TOKEN.search(result):
        raise DerivativeError('content_media_derivative_invalid')
    return SafeDerivative(result, 'application/pdf', None, None)


def generate_safe_derivative(*, content: bytes, media_type: str) -> SafeDerivative:
    """Decode and rewrite an admitted payload into a closed, metadata-free form."""
    if not isinstance(content, bytes) or not content or len(content) > MAX_DERIVATIVE_BYTES:
        raise DerivativeError('content_limit_exceeded')
    if media_type in IMAGE_FORMATS:
        return _image_derivative(content, media_type)
    if media_type == 'application/pdf':
        return _pdf_derivative(content)
    raise DerivativeError('content_media_type_invalid')
