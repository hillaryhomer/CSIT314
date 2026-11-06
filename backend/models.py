"""Entities: profile and account data, and errors shown to users."""

from dataclasses import dataclass


ROLES = ("admin", "designer", "customer", "manager")
PERMISSIONS = (
    "profiles:read", "profiles:write", "accounts:read", "accounts:write",
    "projects:manage", "projects:discover", "reports:read", "categories:manage",
)


@dataclass
class CompanyInformation:
    company_id: str
    owner_id: str
    name: str
    reg_number: str
    address: str
    contact: str
    description: str

    def to_dict(self) -> dict:
        return {'companyId': self.company_id, 'ownerId': self.owner_id, 'name': self.name,
                'regNumber': self.reg_number, 'address': self.address,
                'contact': self.contact, 'description': self.description}


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
        # Keep the key names unchanged so the existing frontend requires no rewrite.
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
        # Intentionally exclude passwords and password hashes from API responses.
        return {
            "accountId": self.account_id, "username": self.username,
            "email": self.email, "profileId": self.profile_id,
            "profileName": profile.name, "profileStatus": profile.status,
            "status": self.status,
        }
