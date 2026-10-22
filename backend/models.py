"""Entity: data profil, akun, dan kesalahan yang ditampilkan ke pengguna."""

from dataclasses import dataclass


ROLES = ("admin", "designer", "customer", "manager")
PERMISSIONS = (
    "profiles:read", "profiles:write", "accounts:read", "accounts:write",
    "projects:manage", "projects:discover", "reports:read", "categories:manage",
)


class AppError(Exception):
    def __init__(self, code: str, message: str, fields: dict | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.fields = fields or {}


@dataclass
class UserProfile:
    profile_id: str
    name: str
    role: str
    permissions: list[str]
    status: str = "Active"

    def to_dict(self) -> dict:
        # Nama key tetap sama supaya frontend yang ada tidak perlu ditulis ulang.
        return {
            "profileId": self.profile_id, "name": self.name, "role": self.role,
            "permissions": self.permissions, "status": self.status,
        }


@dataclass
class UserAccount:
    account_id: str
    username: str
    email: str
    password_hash: str
    profile_id: str
    status: str = "Active"

    def to_dict(self, profile: UserProfile) -> dict:
        # Password dan hash sengaja tidak dimasukkan ke respons API.
        return {
            "accountId": self.account_id, "username": self.username,
            "email": self.email, "profileId": self.profile_id,
            "profileName": profile.name, "profileStatus": profile.status,
            "status": self.status,
        }
