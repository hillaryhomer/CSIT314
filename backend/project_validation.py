"""Validate project fields and actual image contents before persistence."""
import base64
import binascii
from io import BytesIO
import warnings

from PIL import Image, UnidentifiedImageError

from backend.models import AppError
from backend.validation import check_object, clean

MAX_IMAGE_BYTES = 2 * 1024 * 1024
MAX_IMAGE_PIXELS = 12_000_000
MAX_IMAGES = 5
FORMATS = {'JPEG': 'image/jpeg', 'PNG': 'image/png', 'WEBP': 'image/webp'}


def validate_project(data):
    check_object(data, {'title','description','categoryId','style','images'})
    values, errors = {}, {}
    for field, limit in [('title',160), ('description',6000), ('categoryId',100), ('style',100)]:
        raw = data.get(field)
        value = clean(raw)
        if not isinstance(raw, str) or not value or len(value) > limit:
            errors[field] = f'Enter 1-{limit} characters.'
        values[field] = value
    images = data.get('images', [])
    if not isinstance(images, list) or len(images) > MAX_IMAGES:
        errors['images'] = 'Choose up to five images.'
    if errors:
        raise AppError('VALIDATION', 'Please correct the highlighted fields.', errors)
    return values, images


def validate_image(value):
    check_object(value, {'data','mimeType'})
    encoded = value.get('data')
    if not isinstance(encoded, str) or len(encoded) > ((MAX_IMAGE_BYTES + 2) // 3) * 4:
        raise AppError('VALIDATION', 'Each image must be at most 2 MiB.', {'images': 'Image is too large.'})
    try:
        raw = base64.b64decode(encoded, validate=True)
        if not raw or len(raw) > MAX_IMAGE_BYTES:
            raise ValueError('Invalid image size')
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(BytesIO(raw)) as probe:
                format_name = probe.format
                if format_name not in FORMATS or probe.width * probe.height > MAX_IMAGE_PIXELS or getattr(probe, 'n_frames', 1) != 1:
                    raise ValueError('Unsupported format, dimensions or animation')
                probe.verify()
            with Image.open(BytesIO(raw)) as decoded:
                decoded.load()
                # Re-encode pixels: discard uploaded names, metadata and trailing content.
                output = BytesIO()
                decoded.convert('RGB' if format_name == 'JPEG' else 'RGBA').save(output, format=format_name)
                content = output.getvalue()
        if value.get('mimeType') != FORMATS[format_name] or len(content) > MAX_IMAGE_BYTES:
            raise ValueError('MIME mismatch or encoded image too large')
        return {'content': content, 'mimeType': FORMATS[format_name]}
    except (ValueError, TypeError, binascii.Error, UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning) as error:
        raise AppError('VALIDATION', 'Use a valid, non-animated JPEG, PNG or WebP up to 2 MiB and 12 megapixels.', {'images': 'Invalid image file.'}) from error
