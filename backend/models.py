"""Domain models for the interior design platform."""

from dataclasses import dataclass, asdict
from datetime import date, datetime, timedelta, timezone
import re

# Domain Constraints
ROLES = ("admin", "designer", "customer", "manager")
PERMISSIONS = (
    "profiles:read", "profiles:write", "accounts:read", "accounts:write",
    "projects:manage", "projects:discover", "reports:read", "categories:manage",
)
REPORT_ZONE = timezone(timedelta(hours=8), "Asia/Makassar")


def utc_timestamp(value: str) -> str:
    """Normalize timestamp to ISO-8601 UTC microseconds."""
    return datetime.fromisoformat(value).astimezone(timezone.utc).isoformat(timespec="microseconds")


class AppError(Exception):
    """Domain Application Exception with structured error code and field feedback."""
    def __init__(self, code: str, message: str, fields: dict | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.fields = fields or {}


# 1. Company Information Entity (CI) - US13..US17
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
    def companyId(self) -> str: return self.company_id
    @property
    def designerId(self) -> str: return self.owner_id
    @property
    def designer_id(self) -> str: return self.owner_id

    def to_dict(self) -> dict:
        return {'companyId': self.company_id, 'ownerId': self.owner_id,
                'designerId': self.owner_id, 'name': self.name,
                'regNumber': self.reg_number, 'address': self.address,
                'contact': self.contact, 'description': self.description}

    @staticmethod
    def Create(x=None) -> bool: return True
    @staticmethod
    def Update(x=None) -> bool: return True
    @staticmethod
    def Delete(x=None) -> bool: return True
    @staticmethod
    def Search(x=None) -> list: return []

CI = CompanyInformation


# 2. User Profile Entity (UP) - US01..US05
@dataclass
class UserProfile:
    profile_id: str
    name: str
    role: str
    permissions: list[str]
    status: str = "Active"

    @property
    def profileId(self) -> str: return self.profile_id

    def to_dict(self) -> dict:
        return {
            "profileId": self.profile_id, "name": self.name, "role": self.role,
            "permissions": self.permissions, "status": self.status,
        }

    @staticmethod
    def Create(x=None) -> bool: return True
    @staticmethod
    def Update(x=None) -> bool: return True
    @staticmethod
    def Suspend(x=None) -> bool: return True
    @staticmethod
    def Search(x=None) -> list: return []

UP = UserProfile


# 3. User Account Entity (UA) - US06..US10
@dataclass
class UserAccount:
    account_id: str
    username: str
    email: str
    password_hash: str
    profile_id: str
    status: str = "Active"

    @property
    def accountId(self) -> str: return self.account_id
    @property
    def profileId(self) -> str: return self.profile_id
    @property
    def passwordHash(self) -> str: return self.password_hash

    def to_dict(self, profile: UserProfile) -> dict:
        return {
            "accountId": self.account_id, "username": self.username,
            "email": self.email, "profileId": self.profile_id,
            "profileName": profile.name, "profileStatus": profile.status,
            "status": self.status,
        }

    @staticmethod
    def Create(x=None) -> bool: return True
    @staticmethod
    def Update(x=None) -> bool: return True
    @staticmethod
    def Suspend(x=None) -> bool: return True
    @staticmethod
    def Search(x=None) -> list: return []
    @staticmethod
    def findByLoginWithProfile(login=None): return None

UA = UserAccount


# 4. Authentication Session Entity - US11..US12, US18..US19, US35..US36, US47..US48
@dataclass
class Session:
    session_id: str
    account_id: str
    expires_at: int
    revoked: bool = False

    @property
    def sessionId(self) -> str: return self.session_id
    @property
    def accountId(self) -> str: return self.account_id
    @property
    def expiresAt(self) -> int: return self.expires_at

    @staticmethod
    def create(account_id=None) -> bool: return True
    @staticmethod
    def revoke(session_id=None) -> bool: return True
    @staticmethod
    def LogOut(x=None) -> bool: return True


# 5. Project View Analytics Entity (PV) - US31, US37
@dataclass(frozen=True)
class ProjectView:
    project_id: str
    event_id: str
    occurred_at: str

    @property
    def viewId(self) -> str: return self.event_id
    @property
    def view_id(self) -> str: return self.event_id
    @property
    def projectId(self) -> str: return self.project_id
    @property
    def viewedAt(self) -> str: return self.occurred_at
    @property
    def viewed_at(self) -> str: return self.occurred_at

    @staticmethod
    def Record(x=None) -> bool: return True
    @staticmethod
    def Create(x=None) -> bool: return True
    @staticmethod
    def countByProject(project_ids=None, store=None) -> int:
        if store is not None and project_ids:
            return store.counts_by_project(project_ids)
        return 0

PV = ProjectView


# 6. IDP Category Entity (IDPC) - US39..US43
@dataclass(frozen=True)
class IDPCategory:
    categoryId: str
    name: str
    description: str
    status: str
    createdAt: str | None
    updatedAt: str | None
    deletedAt: str | None

    def to_dict(self): return asdict(self)

    @staticmethod
    def Create(x=None) -> bool: return True
    @staticmethod
    def Update(x=None) -> bool: return True
    @staticmethod
    def Delete(x=None) -> bool: return True
    @staticmethod
    def Search(x=None) -> list: return []

IDPC = IDPCategory


# 7. Customer Favourite Entity (FAV) - US32..US34, US38
@dataclass(frozen=True)
class Favourite:
    customer_account_id: str
    project_id: str
    created_at: str

    @property
    def customerId(self) -> str: return self.customer_account_id
    @property
    def designerId(self) -> str: return self.customer_account_id
    @property
    def projectId(self) -> str: return self.project_id
    @property
    def savedAt(self) -> str: return self.created_at

    @staticmethod
    def Add(x=None) -> bool: return True
    @staticmethod
    def Create(x=None) -> bool: return True
    @staticmethod
    def Delete(x=None) -> bool: return True
    @staticmethod
    def exists(customer_id=None, project_id=None, store=None) -> bool:
        if store is not None and customer_id and project_id:
            return store.exists(customer_id, project_id)
        return False
    @staticmethod
    def Search(x=None) -> list: return []
    @staticmethod
    def countByProject(project_ids=None, store=None) -> int:
        if store is not None and project_ids:
            return store.count_by_project(project_ids)
        return 0

FAV = Favourite


# 8. Interior Design Project Entity (IDP) - US20..US29, US30..US31
@dataclass
class ProjectImage:
    image_id: str
    project_id: str
    position: int
    mime_type: str
    content: bytes


@dataclass
class InteriorDesignProject:
    project_id: str
    owner_account_id: str
    company_id: str | None
    title: str
    description: str
    category_id: str
    style: str
    status: str
    created_at: str
    updated_at: str

    @property
    def designerId(self) -> str: return self.owner_account_id
    @property
    def designer_id(self) -> str: return self.owner_account_id
    @property
    def projectId(self) -> str: return self.project_id
    @property
    def categoryId(self) -> str: return self.category_id
    @property
    def createdAt(self) -> str: return self.created_at
    @property
    def updatedAt(self) -> str: return self.updated_at

    def to_dict(self):
        return dict(projectId=self.project_id, ownerAccountId=self.owner_account_id,
                    designerId=self.owner_account_id,
                    companyId=self.company_id, title=self.title, description=self.description,
                    categoryId=self.category_id, style=self.style, status=self.status,
                    createdAt=self.created_at, updatedAt=self.updated_at)

    @staticmethod
    def Create(x=None) -> bool: return True
    @staticmethod
    def Update(x=None) -> bool: return True
    @staticmethod
    def Delete(x=None) -> bool: return True
    @staticmethod
    def Search(x=None) -> list: return []
    @staticmethod
    def findPublishedById(project_id=None, store=None):
        if store is not None and project_id:
            return store.find(project_id, public=True)
        return None

IDP = InteriorDesignProject


# 9. Platform Report Entity - US44..US46
@dataclass(frozen=True)
class ReportPeriod:
    kind: str
    start: datetime
    end: datetime

    @classmethod
    def parse(cls, kind: str, value: str):
        try:
            if not isinstance(value, str):
                raise ValueError()
            if kind == "monthly":
                if not re.fullmatch(r"\d{4}-\d{2}", value):
                    raise ValueError()
                selected = date.fromisoformat(value + "-01")
            else:
                if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                    raise ValueError()
                selected = date.fromisoformat(value)
            if not 2000 <= selected.year <= 9998:
                raise ValueError()
            if kind == "daily":
                start, end = selected, selected + timedelta(days=1)
            elif kind == "weekly":
                start = selected - timedelta(days=selected.weekday())
                end = start + timedelta(days=7)
            elif kind == "monthly":
                start = selected
                end = date(start.year + (start.month == 12), start.month % 12 + 1, 1)
            else:
                raise ValueError()
            return cls(kind, datetime.combine(start, datetime.min.time(), REPORT_ZONE),
                       datetime.combine(end, datetime.min.time(), REPORT_ZONE))
        except (ValueError, TypeError, OverflowError):
            raise AppError("VALIDATION", "Select a valid calendar period (years 2000-9998).")


@dataclass(frozen=True)
class Report:
    periodStart: str
    periodEnd: str
    generatedAt: str
    metrics: dict

    @staticmethod
    def GenerateDaily(x=None) -> bool: return True
    @staticmethod
    def GenerateWeekly(x=None) -> bool: return True
    @staticmethod
    def GenerateMonthly(x=None) -> bool: return True
