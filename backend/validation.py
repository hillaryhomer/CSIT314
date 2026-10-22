"""Validasi input bersama. Aturan bisnis tetap berada di controller."""

import re
import unicodedata

import bcrypt

from backend.models import AppError, PERMISSIONS, ROLES


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
        errors["profileId"] = "Choose an existing active profile."
    if creating:
        password = data.get("password")
        if (not isinstance(password, str) or len(password) < 12
                or len(password.encode("utf-8")) > 72 or not password.strip()):
            errors["password"] = "Use at least 12 characters and at most 72 UTF-8 bytes; whitespace-only passwords are not allowed."
    check_errors(errors)
    return {"username": username, "email": email, "profile_id": profile_id}


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    encoded = password.encode("utf-8")
    if len(encoded) > 72:
        return False
    return bcrypt.checkpw(encoded, password_hash.encode("ascii"))
