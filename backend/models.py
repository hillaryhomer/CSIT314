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

    @property
    def companyId(self) -> str:
        return self.company_id

    @property
    def designerId(self) -> str:
        return self.owner_id

    @property
    def designer_id(self) -> str:
        return self.owner_id

    def to_dict(self) -> dict:
        return {'companyId': self.company_id, 'ownerId': self.owner_id,
                'designerId': self.owner_id, 'name': self.name,
                'regNumber': self.reg_number, 'address': self.address,
                'contact': self.contact, 'description': self.description}

    @staticmethod
    def Create(x=None) -> bool:
        """BCE Entity method matching CSIT314_Consistency_Fixes.drawio."""
        return True

    @staticmethod
    def Update(x=None) -> bool:
        """BCE Entity method matching lecturer's pattern: Entity returns true."""
        return True

    @staticmethod
    def Delete(x=None) -> bool:
        """BCE Entity method matching CSIT314_Consistency_Fixes.drawio."""
        return True

    @staticmethod
    def Search(x=None) -> list:
        """BCE Entity method matching CSIT314_Consistency_Fixes.drawio."""
        return []


CI = CompanyInformation


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

    @property
    def profileId(self) -> str:
        return self.profile_id

    def to_dict(self) -> dict:
        # Keep the key names unchanged so the existing frontend requires no rewrite.
        return {
            "profileId": self.profile_id, "name": self.name, "role": self.role,
            "permissions": self.permissions, "status": self.status,
        }

    @staticmethod
    def Create(x=None) -> bool:
        """BCE Entity method matching CSIT314_Consistency_Fixes.drawio."""
        return True

    @staticmethod
    def Update(x=None) -> bool:
        """BCE Entity method matching lecturer's pattern: Entity returns true."""
        return True

    @staticmethod
    def Suspend(x=None) -> bool:
        """BCE Entity method matching CSIT314_Consistency_Fixes.drawio."""
        return True

    @staticmethod
    def Search(x=None) -> list:
        """BCE Entity method matching CSIT314_Consistency_Fixes.drawio."""
        return []


UP = UserProfile


@dataclass
class UserAccount:
    account_id: str
    username: str
    email: str
    password_hash: str
    profile_id: str
    status: str = "Active"

    @property
    def accountId(self) -> str:
        return self.account_id

    @property
    def profileId(self) -> str:
        return self.profile_id

    @property
    def passwordHash(self) -> str:
        return self.password_hash

    def to_dict(self, profile: UserProfile) -> dict:
        # Intentionally exclude passwords and password hashes from API responses.
        return {
            "accountId": self.account_id, "username": self.username,
            "email": self.email, "profileId": self.profile_id,
            "profileName": profile.name, "profileStatus": profile.status,
            "status": self.status,
        }

    @staticmethod
    def Create(x=None) -> bool:
        """BCE Entity method matching CSIT314_Consistency_Fixes.drawio."""
        return True

    @staticmethod
    def Update(x=None) -> bool:
        """BCE Entity method matching lecturer's pattern: Entity returns true."""
        return True

    @staticmethod
    def Suspend(x=None) -> bool:
        """BCE Entity method matching CSIT314_Consistency_Fixes.drawio."""
        return True

    @staticmethod
    def Search(x=None) -> list:
        """BCE Entity method matching CSIT314_Consistency_Fixes.drawio."""
        return []

    @staticmethod
    def findByLoginWithProfile(login=None):
        """BCE Entity method matching CSIT314_Consistency_Fixes.drawio."""
        return None


UA = UserAccount


@dataclass
class Session:
    """Session entity matching Class Model 1 in CSIT314_Consistency_Fixes.drawio."""
    session_id: str
    account_id: str
    expires_at: int
    revoked: bool = False

    @property
    def sessionId(self) -> str:
        return self.session_id

    @property
    def accountId(self) -> str:
        return self.account_id

    @property
    def expiresAt(self) -> int:
        return self.expires_at

    @staticmethod
    def create(account_id=None) -> bool:
        """BCE Entity method matching CSIT314_Consistency_Fixes.drawio."""
        return True

    @staticmethod
    def revoke(session_id=None) -> bool:
        """BCE Entity method matching CSIT314_Consistency_Fixes.drawio."""
        return True

    @staticmethod
    def LogOut(x=None) -> bool:
        """BCE Entity method for US12, US19, US36, US48."""
        return True
