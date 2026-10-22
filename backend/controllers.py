"""Control: satu class untuk setiap user story, dengan aturan bisnis yang jelas."""

from uuid import uuid4

from backend.database import Repository
from backend.models import AppError, UserAccount, UserProfile
from backend.validation import hash_password, validate_account, validate_profile


def effective_access(repository: Repository, actor_id: str | None) -> tuple[UserAccount, UserProfile]:
    """Dipakai bersama Member 2 untuk memeriksa akses pada setiap request."""
    if not actor_id:
        raise AppError("UNAUTHENTICATED", "An authenticated session is required.")
    account = repository.find_account(actor_id)
    profile = repository.find_profile(account.profile_id) if account else None
    if not account or not profile or account.status != "Active" or profile.status != "Active":
        raise AppError("FORBIDDEN", "The account or its assigned profile cannot access protected functions.")
    return account, profile


class Controller:
    def __init__(self, repository: Repository, actor_id: str | None):
        self.repository = repository
        self.actor_id = actor_id

    def require_admin(self, permission: str) -> tuple[UserAccount, UserProfile]:
        account, profile = effective_access(self.repository, self.actor_id)
        if profile.role != "admin" or permission not in profile.permissions:
            raise AppError("FORBIDDEN", "User Admin permission is required for this operation.")
        return account, profile

    def get_profile(self, profile_id: str) -> UserProfile:
        profile = self.repository.find_profile(profile_id)
        if not profile:
            raise AppError("NOT_FOUND", "Profile was not found. Refresh the list and try again.")
        return profile

    def get_account(self, account_id: str) -> UserAccount:
        account = self.repository.find_account(account_id)
        if not account:
            raise AppError("NOT_FOUND", "Account was not found. Refresh the list and try again.")
        return account

    def check_profile_name(self, name: str, current_id: str | None = None) -> None:
        existing = self.repository.profile_with_name(name)
        if existing and existing.profile_id != current_id:
            raise AppError("DUPLICATE", "A profile with this name already exists.",
                           {"name": "Choose a different profile name."})

    def check_account_details(self, username: str, email: str, current_id: str | None = None) -> None:
        errors = {}
        existing = self.repository.account_with_username(username)
        if existing and existing.account_id != current_id:
            errors["username"] = "This username is already in use."
        existing = self.repository.account_with_email(email)
        if existing and existing.account_id != current_id:
            errors["email"] = "This email is already in use."
        if errors:
            raise AppError("DUPLICATE", "An account with these details already exists.", errors)

    def check_assignment(self, profile_id: str, current_id: str | None = None) -> UserProfile:
        profile = self.repository.find_profile(profile_id)
        if not profile or (profile.status != "Active" and profile_id != current_id):
            raise AppError("VALIDATION", "The assigned profile is missing or suspended.",
                           {"profileId": "Choose an existing active profile."})
        return profile

    def protect_admin(self, proposed_profile: UserProfile, current_profile: UserProfile) -> None:
        if (proposed_profile.status != "Active" or proposed_profile.role != "admin"
                or not set(current_profile.permissions).issubset(proposed_profile.permissions)):
            raise AppError("FORBIDDEN", "You cannot remove your own administrative access through this workflow.")


class CreateUserProfileController(Controller):
    def execute(self, data: dict) -> dict:
        with self.repository.transaction():
            self.require_admin("profiles:write")
            values = validate_profile(data)
            self.check_profile_name(values["name"])
            profile = UserProfile("UP-" + str(uuid4()), **values)
            self.repository.create_profile(profile)
        return profile.to_dict()


class ViewUserProfileController(Controller):
    def execute(self, profile_id: str) -> dict:
        self.require_admin("profiles:read")
        return self.get_profile(profile_id).to_dict()


class UpdateUserProfileController(Controller):
    def execute(self, profile_id: str, data: dict) -> dict:
        with self.repository.transaction():
            actor, actor_profile = self.require_admin("profiles:write")
            current = self.get_profile(profile_id)
            values = validate_profile(data)
            self.check_profile_name(values["name"], profile_id)
            profile = UserProfile(profile_id, **values, status=current.status)
            if actor.profile_id == profile_id:
                self.protect_admin(profile, actor_profile)
            self.repository.update_profile(profile)
        return profile.to_dict()


class SuspendUserProfileController(Controller):
    def execute(self, profile_id: str) -> dict:
        with self.repository.transaction():
            actor, _ = self.require_admin("profiles:write")
            profile = self.get_profile(profile_id)
            if profile.status == "Suspended":
                raise AppError("ALREADY_SUSPENDED", "This profile is already suspended.")
            if actor.profile_id == profile_id:
                raise AppError("FORBIDDEN", "You cannot remove your own administrative access through this workflow.")
            profile.status = "Suspended"
            self.repository.update_profile(profile)
        return profile.to_dict()


class SearchUserProfileController(Controller):
    def execute(self, name: str = "") -> list[dict]:
        self.require_admin("profiles:read")
        if not isinstance(name, str) or len(name) > 100:
            raise AppError("VALIDATION", "Search must be text of at most 100 characters.")
        return [profile.to_dict() for profile in self.repository.search_profiles(name)]


class CreateUserAccountController(Controller):
    def execute(self, data: dict) -> dict:
        self.require_admin("accounts:write")
        values = validate_account(data, creating=True)
        self.check_assignment(values["profile_id"])
        self.check_account_details(values["username"], values["email"])
        password_hash = hash_password(data["password"])
        with self.repository.transaction():
            # Profil/akses mungkin berubah saat proses hashing: periksa lagi.
            self.require_admin("accounts:write")
            profile = self.check_assignment(values["profile_id"])
            self.check_account_details(values["username"], values["email"])
            account = UserAccount("UA-" + str(uuid4()), password_hash=password_hash, **values)
            self.repository.create_account(account)
        return account.to_dict(profile)


class ViewUserAccountController(Controller):
    def execute(self, account_id: str) -> dict:
        self.require_admin("accounts:read")
        account = self.get_account(account_id)
        return account.to_dict(self.get_profile(account.profile_id))

    def list_accounts(self) -> list[dict]:
        self.require_admin("accounts:read")
        return [account.to_dict(self.get_profile(account.profile_id))
                for account in self.repository.list_accounts()]


class UpdateUserAccountController(Controller):
    def execute(self, account_id: str, data: dict) -> dict:
        with self.repository.transaction():
            actor, actor_profile = self.require_admin("accounts:write")
            current = self.get_account(account_id)
            values = validate_account(data)
            self.check_account_details(values["username"], values["email"], account_id)
            profile = self.check_assignment(values["profile_id"], current.profile_id)
            if actor.account_id == account_id:
                self.protect_admin(profile, actor_profile)
            account = UserAccount(account_id, password_hash=current.password_hash,
                                  status=current.status, **values)
            self.repository.update_account(account)
        return account.to_dict(profile)
