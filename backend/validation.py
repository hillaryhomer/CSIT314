"""Shared input validation rules and password security for Interior Designer Platform."""

import base64
import binascii
from io import BytesIO
import re
import unicodedata
import warnings

import bcrypt
from PIL import Image, UnidentifiedImageError

from backend.models import AppError, PERMISSIONS, ROLES

MAX_IMAGE_BYTES = 2 * 1024 * 1024
MAX_IMAGE_PIXELS = 12_000_000
MAX_IMAGES = 5
IMAGE_FORMATS = {'JPEG': 'image/jpeg', 'PNG': 'image/png', 'WEBP': 'image/webp'}


def clean(value: object) -> str:
    return unicodedata.normalize("NFKC", value).strip() if isinstance(value, str) else ""


def normalize(value: str) -> str:
    return clean(value).lower()


def check_object(data: object, allowed_fields: set[str]) -> None:
    if not isinstance(data, dict) or set(data) - allowed_fields:
        raise AppError("VALIDATION", "The request contains invalid or unsupported fields.")


def check_errors(errors: dict) -> None:
    if errors:
        raise AppError("VALIDATION", "Please correct the highlighted fields.", errors)


def validate_profile(data: dict) -> dict:
    check_object(data, {"name", "role", "permissions"})
    name = clean(data.get("name"))
    role = data.get("role")
    permissions = data.get("permissions")
    errors = {}
    if not name or len(name) > 80:
        errors["name"] = "Enter a profile name of 1-80 characters."
    if role not in ROLES:
        errors["role"] = "Select a supported role."
    if (not isinstance(permissions, list) or not permissions
            or any(value not in PERMISSIONS for value in permissions)
            or len(set(permissions)) != len(permissions)):
        errors["permissions"] = "Select at least one supported permission, without duplicates."
    check_errors(errors)
    return {"name": name, "role": role, "permissions": permissions}


def validate_account(data: dict, creating: bool = False) -> dict:
    allowed = {"username", "email", "profileId"}
    if creating:
        allowed.add("password")
    check_object(data, allowed)
    username = clean(data.get("username"))
    email = normalize(clean(data.get("email")))
    profile_id = clean(data.get("profileId"))
    errors = {}
    if not re.fullmatch(r"[a-zA-Z0-9_.-]{3,40}", username):
        errors["username"] = "Use 3-40 letters, digits, dots, underscores or hyphens."
    if len(email) > 254 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        errors["email"] = "Enter a valid email address."
    if not profile_id:
        errors["profileId"] = "Select an existing user profile."
    if creating:
        password = data.get("password")
        if not isinstance(password, str) or len(password) < 6:
            errors["password"] = "Password must be at least 6 characters."
        elif len(password.encode("utf-8")) > 72:
            errors["password"] = "Password must be at most 72 bytes."
    check_errors(errors)
    return {"username": username, "email": email, "profileId": profile_id}


def hash_password(password: str) -> str:
    raw = password.encode("utf-8")
    if len(raw) > 72:
        raise AppError("VALIDATION", "Password must be at most 72 bytes.",
                       {"password": "Password must be at most 72 bytes."})
    return bcrypt.hashpw(raw, bcrypt.gensalt(12)).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def validate_company(data: dict) -> dict:
    check_object(data, {'name', 'regNumber', 'address', 'contact', 'description'})
    limits = {'name': 120, 'regNumber': 80, 'address': 500, 'contact': 254, 'description': 4000}
    values, errors = {}, {}
    for field, limit in limits.items():
        raw = data.get(field, '')
        value = clean(raw)
        values[field] = value
        if not isinstance(raw, str) or len(value) > limit or (field in ('name', 'address', 'contact') and not value):
            errors[field] = f'Enter text of {1 if field in ("name", "address", "contact") else 0}-{limit} characters.'
    check_errors(errors)
    return values


def validate_project(data: dict):
    check_object(data, {'title', 'description', 'categoryId', 'style', 'images'})
    values, errors = {}, {}
    for field, limit in [('title', 160), ('description', 6000), ('categoryId', 100), ('style', 100)]:
        raw = data.get(field)
        value = clean(raw)
        if not isinstance(raw, str) or not value or len(value) > limit:
            errors[field] = f'Enter 1-{limit} characters.'
        values[field] = value
    images = data.get('images', [])
    if not isinstance(images, list) or len(images) > MAX_IMAGES:
        errors['images'] = 'Choose up to five images.'
    check_errors(errors)
    return values, images


def validate_image(value: dict):
    check_object(value, {'data', 'mimeType'})
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
                if format_name not in IMAGE_FORMATS or probe.width * probe.height > MAX_IMAGE_PIXELS or getattr(probe, 'n_frames', 1) != 1:
                    raise ValueError('Unsupported format, dimensions or animation')
                probe.verify()
            with Image.open(BytesIO(raw)) as decoded:
                decoded.load()
                output = BytesIO()
                decoded.convert('RGB' if format_name == 'JPEG' else 'RGBA').save(output, format=format_name)
                content = output.getvalue()
        if value.get('mimeType') != IMAGE_FORMATS[format_name] or len(content) > MAX_IMAGE_BYTES:
            raise ValueError('MIME mismatch or encoded image too large')
        return {'content': content, 'mimeType': IMAGE_FORMATS[format_name]}
    except (ValueError, TypeError, binascii.Error, UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning) as error:
        raise AppError('VALIDATION', 'Upload a valid, static JPEG, PNG or WebP image under 2 MiB.', {'images': str(error)})
