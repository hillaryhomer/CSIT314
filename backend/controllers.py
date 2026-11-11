"""Unified BCE Controllers for all 48 User Stories (Interior Designer Platform)."""

from datetime import datetime, timezone
import secrets
from uuid import uuid4

from backend.database import (
    ActivityRepository,
    CategoryRepository,
    CompanyRepository,
    FavouriteRepository,
    ProjectActivityAdapter,
    ProjectRepository,
    ReportRepository,
    ReportService,
    Repository,
)
from backend.models import (
    AppError,
    CompanyInformation,
    Favourite,
    IDPCategory,
    InteriorDesignProject,
    ProjectImage,
    ProjectView,
    UserAccount,
    UserProfile,
    utc_timestamp,
)
from backend.validation import (
    check_object,
    clean,
    hash_password,
    normalize,
    validate_account,
    validate_company,
    validate_image,
    validate_profile,
    validate_project,
    verify_password,
)


def effective_access(repository: Repository, account_id: str | None) -> tuple[UserAccount, UserProfile]:
    """Recheck active user access and profile status on every request."""
    if not account_id:
        raise AppError("UNAUTHENTICATED", "An authenticated session is required.")
    account = repository.account_with_id(account_id)
    if not account or account.status != "Active":
        raise AppError("UNAUTHENTICATED", "This account is inactive or not found.")
    profile = repository.profile_with_id(account.profile_id)
    if not profile or profile.status != "Active":
        raise AppError("FORBIDDEN", "The assigned profile is suspended or not found.")
    return account, profile


class Controller:
    """Base Controller providing identity verification and role authorization."""
    def __init__(self, repository: Repository, actor_id: str | None):
        self.repository = repository
        self.actor_id = actor_id

    def require_admin(self, permission: str) -> tuple[UserAccount, UserProfile]:
        account, profile = effective_access(self.repository, self.actor_id)
        if profile.role != "admin" or permission not in profile.permissions:
            raise AppError("FORBIDDEN", "Administrator permissions are required for this action.")
        return account, profile

    def get_profile(self, profile_id: str) -> UserProfile:
        profile = self.repository.profile_with_id(profile_id)
        if not profile:
            raise AppError("NOT_FOUND", "User profile not found.")
        return profile

    def get_account(self, account_id: str) -> UserAccount:
        account = self.repository.account_with_id(account_id)
        if not account:
            raise AppError("NOT_FOUND", "User account not found.")
        return account


# ---------------------------------------------------------------------------
# SPRINT 1 : LOGIN AND SHARED AUTHENTICATION
# ---------------------------------------------------------------------------

class LoginController(Controller):
    """US11, US18, US35, US47: Authenticate credentials and issue session."""
    dummy_hash = None

    def execute(self, data: dict, previous_token: str = ""):
        check_object(data, {"identifier", "password"})
        identifier = clean(data.get("identifier"))
        password = data.get("password")
        if not identifier or len(identifier) > 254 or not isinstance(password, str) or len(password.encode()) > 72:
            raise AppError("VALIDATION", "Enter a username/email and password.")
        account = (self.repository.account_with_username(identifier)
                   or self.repository.account_with_email(identifier))
        if LoginController.dummy_hash is None:
            LoginController.dummy_hash = hash_password(secrets.token_urlsafe(24))
        valid = verify_password(password, account.password_hash if account else LoginController.dummy_hash)
        if not account or not valid:
            raise AppError("UNAUTHENTICATED", "Incorrect username/email or password.")
        store = CompanyRepository(self.repository)
        with self.repository.transaction():
            _, profile = effective_access(self.repository, account.account_id)
            token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
            store.remove_session(previous_token)
            store.create_session(token, account.account_id, csrf)
        return token, {
            "account": account.to_dict(profile),
            "role": profile.role,
            "permissions": profile.permissions,
            "csrfToken": csrf,
        }

LogInUAC = LoginController


class LogOutSessionC(Controller):
    """US12, US19, US36, US48: Invalidate session token upon logout."""
    def execute(self, session_token: str = ""):
        CompanyRepository(self.repository).remove_session(session_token)
        return {"loggedOut": True}


# ---------------------------------------------------------------------------
# SPRINT 2 : USER PROFILES (US01..US05)
# ---------------------------------------------------------------------------

class CreateProfileController(Controller):
    def execute(self, data: dict) -> dict:
        values = validate_profile(data)
        with self.repository.transaction():
            self.require_admin("profiles:write")
            if self.repository.profile_with_name(values["name"]):
                raise AppError("DUPLICATE", "A profile with this name already exists.", {"name": "Profile name is already used."})
            profile = UserProfile(profile_id="UP-" + str(uuid4()), **values)
            self.repository.create_profile(profile)
        return profile.to_dict()

CreateUPC = CreateProfileController


class ViewProfileController(Controller):
    def execute(self, profile_id: str) -> dict:
        self.require_admin("profiles:read")
        return self.get_profile(profile_id).to_dict()

ViewUPC = ViewProfileController


class UpdateProfileController(Controller):
    def execute(self, profile_id: str, data: dict) -> dict:
        values = validate_profile(data)
        with self.repository.transaction():
            self.require_admin("profiles:write")
            profile = self.get_profile(profile_id)
            existing = self.repository.profile_with_name(values["name"])
            if existing and existing.profile_id != profile_id:
                raise AppError("DUPLICATE", "A profile with this name already exists.", {"name": "Profile name is already used."})
            profile.name = values["name"]
            profile.role = values["role"]
            profile.permissions = values["permissions"]
            self.repository.update_profile(profile)
        return profile.to_dict()

UpdateUPC = UpdateProfileController


class SuspendProfileController(Controller):
    def execute(self, profile_id: str) -> dict:
        with self.repository.transaction():
            self.require_admin("profiles:write")
            profile = self.get_profile(profile_id)
            if profile.status == "Suspended":
                raise AppError("ALREADY_SUSPENDED", "This user profile is already suspended.")
            profile.status = "Suspended"
            self.repository.update_profile(profile)
        return profile.to_dict()

SuspendUPC = SuspendProfileController


class SearchProfileController(Controller):
    def execute(self, query: str = "") -> list[dict]:
        self.require_admin("profiles:read")
        return [p.to_dict() for p in self.repository.list_profiles(query)]

SearchUPC = SearchProfileController


# ---------------------------------------------------------------------------
# SPRINT 2 : USER ACCOUNTS (US06..US10)
# ---------------------------------------------------------------------------

class CreateUserAccountController(Controller):
    def execute(self, data: dict) -> dict:
        values = validate_account(data, creating=True)
        password_hash = hash_password(values.pop("password"))
        with self.repository.transaction():
            self.require_admin("accounts:write")
            profile = self.get_profile(values["profileId"])
            if profile.status != "Active":
                raise AppError("VALIDATION", "New accounts cannot be assigned to suspended profiles.", {"profileId": "Profile is suspended."})
            if self.repository.account_with_username(values["username"]):
                raise AppError("DUPLICATE", "Username already in use.", {"username": "Username is already used."})
            if self.repository.account_with_email(values["email"]):
                raise AppError("DUPLICATE", "Email already in use.", {"email": "Email is already used."})
            account = UserAccount(account_id="UA-" + str(uuid4()), password_hash=password_hash, **values)
            self.repository.create_account(account)
        return account.to_dict(profile)

CreateUAC = CreateUserAccountController


class ViewUserAccountController(Controller):
    def execute(self, account_id: str) -> dict:
        self.require_admin("accounts:read")
        account = self.get_account(account_id)
        return account.to_dict(self.get_profile(account.profile_id))

ViewUAC = ViewUserAccountController


class UpdateUserAccountController(Controller):
    def execute(self, account_id: str, data: dict) -> dict:
        values = validate_account(data, creating=False)
        with self.repository.transaction():
            self.require_admin("accounts:write")
            account = self.get_account(account_id)
            profile = self.get_profile(values["profileId"])
            if profile.status != "Active" and values["profileId"] != account.profile_id:
                raise AppError("VALIDATION", "Cannot reassign account to a suspended profile.", {"profileId": "Profile is suspended."})
            existing_user = self.repository.account_with_username(values["username"])
            if existing_user and existing_user.account_id != account_id:
                raise AppError("DUPLICATE", "Username already in use.", {"username": "Username is already used."})
            existing_email = self.repository.account_with_email(values["email"])
            if existing_email and existing_email.account_id != account_id:
                raise AppError("DUPLICATE", "Email already in use.", {"email": "Email is already used."})
            account.username = values["username"]
            account.email = values["email"]
            account.profile_id = values["profileId"]
            self.repository.update_account(account)
        return account.to_dict(profile)

UpdateUAC = UpdateUserAccountController


class SuspendUserAccountController(Controller):
    def execute(self, account_id: str) -> dict:
        with self.repository.transaction():
            actor, _ = self.require_admin("accounts:write")
            account = self.get_account(account_id)
            if account.account_id == actor.account_id:
                raise AppError("FORBIDDEN", "You cannot suspend your own account.")
            if account.status == "Suspended":
                raise AppError("ALREADY_SUSPENDED", "This account is already suspended.")
            CompanyRepository(self.repository).suspend_account(account_id)
            account.status = "Suspended"
        return account.to_dict(self.get_profile(account.profile_id))

SuspendUAC = SuspendUserAccountController


class SearchUserAccountController(Controller):
    def execute(self, query: str = "") -> list[dict]:
        self.require_admin("accounts:read")
        if not isinstance(query, str) or len(query) > 254:
            raise AppError("VALIDATION", "Search must contain at most 254 characters.")
        keyword = normalize(query)
        return [a.to_dict(self.get_profile(a.profile_id)) for a in self.repository.list_accounts()
                if keyword in normalize(a.username) or keyword in normalize(a.email)]

SearchUAC = SearchUserAccountController


# ---------------------------------------------------------------------------
# SPRINT 2 : COMPANY INFORMATION (US13..US17)
# ---------------------------------------------------------------------------

class CompanyController(Controller):
    def owner(self) -> str:
        account, profile = effective_access(self.repository, self.actor_id)
        if profile.role != "designer":
            raise AppError("FORBIDDEN", "Interior Designer access is required.")
        return account.account_id

    def view(self, query: str = "") -> dict:
        owner = self.owner()
        if len(query) > 254:
            raise AppError("VALIDATION", "Search must contain at most 254 characters.")
        company = CompanyRepository(self.repository).company(owner)
        return {
            "company": company,
            "matches": bool(company and normalize(query) in normalize(" ".join(
                company[k] for k in ("name", "regNumber", "address", "contact", "description")
            ))),
        }

    def create(self, data: dict) -> dict:
        values = validate_company(data)
        with self.repository.transaction():
            owner = self.owner()
            if CompanyRepository(self.repository).company(owner):
                raise AppError("DUPLICATE", "You already have company information. Edit the existing company.")
            CompanyRepository(self.repository).create_company("CO-" + str(uuid4()), owner, values)
        return CompanyRepository(self.repository).company(owner)

    def update(self, company_id: str, data: dict) -> dict:
        values = validate_company(data)
        with self.repository.transaction():
            owner = self.owner()
            current = CompanyRepository(self.repository).company(owner)
            if not current or current["companyId"] != company_id:
                raise AppError("NOT_FOUND", "Company was not found.")
            CompanyRepository(self.repository).update_company(company_id, owner, values)
        return CompanyRepository(self.repository).company(owner)

    def delete(self, company_id: str) -> dict:
        with self.repository.transaction():
            owner = self.owner()
            current = CompanyRepository(self.repository).company(owner)
            if not current or current["companyId"] != company_id:
                raise AppError("NOT_FOUND", "Company was not found.")
            CompanyRepository(self.repository).delete_company(company_id, owner)
        return {"deleted": True}

class CreateCIC(CompanyController):
    def execute(self, data): return self.create(data)

class ViewCIC(CompanyController):
    def execute(self, query=""): return self.view(query)

class UpdateCIC(CompanyController):
    def execute(self, company_id, data): return self.update(company_id, data)

class DeleteCIC(CompanyController):
    def execute(self, company_id): return self.delete(company_id)

class SearchCIC(CompanyController):
    def execute(self, query=""): return self.view(query)


# ---------------------------------------------------------------------------
# SPRINT 2 : CURRENT & PAST PROJECTS (US20..US29)
# ---------------------------------------------------------------------------

class ProjectController(Controller):
    def designer_owner(self) -> str:
        account, profile = effective_access(self.repository, self.actor_id)
        if profile.role != "designer" or "projects:manage" not in profile.permissions:
            raise AppError("FORBIDDEN", "Designer project permissions required.")
        return account.account_id

    def list(self, status: str, query: str = ""):
        owner = self.designer_owner()
        return ProjectRepository(self.repository).search(status=status, owner=owner, query=query)

    def view(self, project_id: str):
        owner = self.designer_owner()
        project = ProjectRepository(self.repository).find(project_id, owner=owner)
        if not project:
            raise AppError("NOT_FOUND", "Project was not found.")
        return project

    def create(self, status: str, data: dict):
        values, image_inputs = validate_project(data)
        owner = self.designer_owner()
        store = ProjectRepository(self.repository)
        with self.repository.transaction():
            category = store.category(values["categoryId"])
            if not category or category["status"] != "Active":
                raise AppError("VALIDATION", "Choose an active category.", {"categoryId": "Category is inactive or missing."})
            project_id = "PRJ-" + str(uuid4())
            now = datetime.now(timezone.utc).isoformat()
            images = [ProjectImage("IMG-" + str(uuid4()), project_id, pos, img["mimeType"], img["content"])
                      for pos, img in enumerate(validate_image(item) for item in image_inputs)]
            project = InteriorDesignProject(
                project_id=project_id, owner_account_id=owner,
                company_id=store.company_id(owner), title=values["title"],
                description=values["description"], category_id=values["categoryId"],
                style=values["style"], status=status, created_at=now, updated_at=now,
            )
            store.save(project, images, new=True)
        return store.find(project_id, owner=owner)

    def update(self, project_id: str, data: dict):
        values, image_inputs = validate_project(data)
        owner = self.designer_owner()
        store = ProjectRepository(self.repository)
        with self.repository.transaction():
            current = store.find(project_id, owner=owner)
            if not current:
                raise AppError("NOT_FOUND", "Project was not found.")
            category = store.category(values["categoryId"])
            if not category or (category["status"] != "Active" and values["categoryId"] != current["categoryId"]):
                raise AppError("VALIDATION", "Choose an active category.", {"categoryId": "Category is inactive or missing."})
            images = [ProjectImage("IMG-" + str(uuid4()), project_id, pos, img["mimeType"], img["content"])
                      for pos, img in enumerate(validate_image(item) for item in image_inputs)]
            project = InteriorDesignProject(
                project_id=project_id, owner_account_id=owner,
                company_id=store.company_id(owner), title=values["title"],
                description=values["description"], category_id=values["categoryId"],
                style=values["style"], status=current["status"],
                created_at=current["createdAt"], updated_at=datetime.now(timezone.utc).isoformat(),
            )
            store.save(project, images, new=False)
        return store.find(project_id, owner=owner)

    def delete(self, project_id: str):
        owner = self.designer_owner()
        store = ProjectRepository(self.repository)
        with self.repository.transaction():
            if not store.find(project_id, owner=owner):
                raise AppError("NOT_FOUND", "Project was not found.")
            store.delete(project_id)
        return {"deleted": True}

class SearchIDPC(ProjectController):
    def execute(self, query: str = "", status: str = "Current"):
        return self.list(status=status, query=query)

class CreateCurrentIDPController(ProjectController):
    def execute(self, data: dict): return self.create("Current", data)

class ViewCurrentIDPController(ProjectController):
    def execute(self, project_id: str): return self.view(project_id)

class UpdateCurrentIDPController(ProjectController):
    def execute(self, project_id: str, data: dict): return self.update(project_id, data)

class DeleteCurrentIDPController(ProjectController):
    def execute(self, project_id: str): return self.delete(project_id)

class SearchCurrentIDPController(SearchIDPC):
    def execute(self, query: str = "", status: str = "Current"):
        return super().execute(query=query, status=status or "Current")

class CreatePastIDPController(ProjectController):
    def execute(self, data: dict): return self.create("Past", data)

class ViewPastIDPController(ProjectController):
    def execute(self, project_id: str): return self.view(project_id)

class UpdatePastIDPController(ProjectController):
    def execute(self, project_id: str, data: dict): return self.update(project_id, data)

class DeletePastIDPController(ProjectController):
    def execute(self, project_id: str): return self.delete(project_id)

class SearchPastIDPController(SearchIDPC):
    def execute(self, query: str = "", status: str = "Past"):
        return super().execute(query=query, status=status or "Past")

class CustomerProjectController(Controller):
    def image(self, image_id: str):
        store = ProjectRepository(self.repository)
        img = store.image_content(image_id)
        if not img:
            raise AppError("NOT_FOUND", "Image not found.")
        return img

# BCE Aliases
CreateCurrentIDPC = CreateCurrentIDPController
ViewCurrentIDPC = ViewCurrentIDPController
UpdateCurrentIDPC = UpdateCurrentIDPController
DeleteCurrentIDPC = DeleteCurrentIDPController
SearchCurrentIDPC = SearchCurrentIDPController

CreatePastIDPC = CreatePastIDPController
ViewPastIDPC = ViewPastIDPController
UpdatePastIDPC = UpdatePastIDPController
DeletePastIDPC = DeletePastIDPController
SearchPastIDPC = SearchPastIDPController

CreateIDPController = ProjectController
ViewIDPController = ProjectController
UpdateIDPController = ProjectController
DeleteIDPController = ProjectController
SearchIDPController = SearchIDPC

CreateIDPC = CreateCurrentIDPController
ViewIDPC = ViewCurrentIDPController
UpdateIDPC = UpdateCurrentIDPController
DeleteIDPC = DeleteCurrentIDPController


# ---------------------------------------------------------------------------
# SPRINT 3 : CUSTOMER DISCOVERY & FAVOURITES (US30..US36)
# ---------------------------------------------------------------------------

class CustomerCatalogController(Controller):
    def customer_actor(self) -> str:
        account, profile = effective_access(self.repository, self.actor_id)
        if profile.role != "customer" or "projects:discover" not in profile.permissions:
            raise AppError("FORBIDDEN", "Customer discovery access required.")
        return account.account_id

    def search_catalog(self, query: str = "", category_id: str = "", style: str = ""):
        customer_id = None
        if self.actor_id:
            try: customer_id = self.customer_actor()
            except AppError: pass
        projects = ProjectRepository(self.repository).search(public=True, query=query, category_id=category_id, style=style)
        favourite_ids = set()
        if customer_id:
            favourite_ids = {f.project_id for f in FavouriteRepository(self.repository).list_for_customer(customer_id)}
        for p in projects:
            p["saved"] = p["projectId"] in favourite_ids
        return projects

    def view_project(self, project_id: str):
        project = ProjectRepository(self.repository).find(project_id, public=True)
        if not project:
            raise AppError("NOT_FOUND", "Project not found.")
        customer_id = None
        if self.actor_id:
            try: customer_id = self.customer_actor()
            except AppError: pass
        project["saved"] = FavouriteRepository(self.repository).exists(customer_id, project_id) if customer_id else False
        return project

    def add_favourite(self, project_id: str):
        customer_id = self.customer_actor()
        store = FavouriteRepository(self.repository)
        with self.repository.transaction():
            project = ProjectRepository(self.repository).find(project_id, public=True)
            if not project:
                raise AppError("NOT_FOUND", "Project not found.")
            now = datetime.now(timezone.utc).isoformat()
            created = store.add(Favourite(customer_id, project_id, now))
        record = store.find(customer_id, project_id)
        project["saved"] = True
        project["savedAt"] = record.created_at if record else now
        return {"project": project, "saved": True, "created": created}

    def list_favourites(self, query: str = ""):
        customer_id = self.customer_actor()
        projects = ProjectRepository(self.repository).search(public=True, favourite_customer=customer_id, query=query)
        saved_dates = {f.project_id: f.created_at for f in FavouriteRepository(self.repository).list_for_customer(customer_id)}
        for p in projects:
            p["saved"] = True
            p["savedAt"] = saved_dates.get(p["projectId"])
        return projects

class SearchIDPController(CustomerCatalogController):
    def execute(self, query: str = "", category_id: str = "", style: str = ""):
        return self.search_catalog(query, category_id, style)

class ViewIDPController(CustomerCatalogController):
    def execute(self, project_id: str):
        return self.view_project(project_id)

class AddFavouriteController(CustomerCatalogController):
    def execute(self, data: dict):
        check_object(data, {"projectId"})
        project_id = clean(data.get("projectId"))
        if not project_id:
            raise AppError("VALIDATION", "Project ID required.")
        return self.add_favourite(project_id)

class ViewFavouriteListController(CustomerCatalogController):
    def execute(self):
        return self.list_favourites()

class SearchFavouriteListController(CustomerCatalogController):
    def execute(self, query: str = ""):
        return self.list_favourites(query)

SearchCustomerCatalogController = SearchIDPController
ViewCustomerProjectController = ViewIDPController
ViewFavouriteController = ViewFavouriteListController
SearchFavouriteController = SearchFavouriteListController

SearchIDPCustomerC = SearchIDPController
ViewIDPCustomerC = ViewIDPController
AddFAVC = AddFavouriteController
ViewFAVC = ViewFavouriteListController
SearchFAVC = SearchFavouriteListController


# ---------------------------------------------------------------------------
# SPRINT 3 : DESIGNER ANALYTICS (US37..US38)
# ---------------------------------------------------------------------------

class RecordIDPViewController(Controller):
    def execute(self, project_id: str, data: dict):
        check_object(data, {"eventId"})
        event_id = clean(data.get("eventId"))
        if not 16 <= len(event_id) <= 100:
            raise AppError("VALIDATION", "Valid analytics event ID required.")
        with self.repository.transaction():
            if not ProjectRepository(self.repository).find(project_id, public=True):
                raise AppError("NOT_FOUND", "Project not found.")
            now = datetime.now(timezone.utc).isoformat()
            recorded = ActivityRepository(self.repository).record(ProjectView(project_id, event_id, now))
        return {"recorded": recorded}


class ViewAnalyticsController(Controller):
    def execute(self, project_id: str = None):
        account, profile = effective_access(self.repository, self.actor_id)
        if profile.role != "designer":
            raise AppError("FORBIDDEN", "Interior Designer access required.")
        return ActivityRepository(self.repository).counts(account.account_id, project_id)

ViewIDPViewsController = ViewAnalyticsController
ViewIDPShortlistsController = ViewAnalyticsController
ViewIDPViewsC = ViewAnalyticsController
ViewIDPShortlistsC = ViewAnalyticsController


# ---------------------------------------------------------------------------
# SPRINT 3 : IDP CATEGORIES (US39..US43)
# ---------------------------------------------------------------------------

class CategoryController(Controller):
    def require_manager(self):
        account, profile = effective_access(self.repository, self.actor_id)
        if profile.role != "manager" or "categories:manage" not in profile.permissions:
            raise AppError("FORBIDDEN", "Manager category permissions required.")
        return account.account_id

    def list(self, query: str = ""):
        self.require_manager()
        return CategoryRepository(self.repository).search(query)

    def view(self, category_id: str):
        self.require_manager()
        cat = CategoryRepository(self.repository).find(category_id)
        if not cat: raise AppError("NOT_FOUND", "Category not found.")
        return cat.to_dict()

    def create(self, data: dict):
        self.require_manager()
        check_object(data, {"name", "description"})
        name, description = clean(data.get("name")), clean(data.get("description", ""))
        if not name or len(name) > 100:
            raise AppError("VALIDATION", "Category name must be 1-100 characters.", {"name": "Enter 1-100 characters."})
        store = CategoryRepository(self.repository)
        with self.repository.transaction():
            if store.duplicate(name):
                raise AppError("DUPLICATE", "Category name already exists.", {"name": "Category name already exists."})
            now = datetime.now(timezone.utc).isoformat()
            cat = IDPCategory("CAT-" + str(uuid4()), name, description, "Active", now, now, None)
            store.save(cat, new=True)
        return cat.to_dict()

    def update(self, category_id: str, data: dict):
        self.require_manager()
        check_object(data, {"name", "description", "status"})
        name, description = clean(data.get("name")), clean(data.get("description", ""))
        status = data.get("status")
        if status not in ("Active", "Suspended"):
            raise AppError("VALIDATION", "Status must be Active or Suspended.")
        if not name or len(name) > 100:
            raise AppError("VALIDATION", "Category name must be 1-100 characters.", {"name": "Enter 1-100 characters."})
        store = CategoryRepository(self.repository)
        with self.repository.transaction():
            current = store.find(category_id)
            if not current: raise AppError("NOT_FOUND", "Category not found.")
            if store.duplicate(name, excluding=category_id):
                raise AppError("DUPLICATE", "Category name already exists.", {"name": "Category name already exists."})
            now = datetime.now(timezone.utc).isoformat()
            cat = IDPCategory(category_id, name, description, status, current.createdAt, now, None)
            store.save(cat, new=False)
        return cat.to_dict()

    def delete(self, category_id: str):
        self.require_manager()
        store = CategoryRepository(self.repository)
        with self.repository.transaction():
            current = store.find(category_id)
            if not current: raise AppError("NOT_FOUND", "Category not found.")
            now = datetime.now(timezone.utc).isoformat()
            cat = IDPCategory(category_id, current.name, current.description, "Suspended", current.createdAt, current.updatedAt, now)
            store.save(cat, new=False)
        return {"deleted": True}

class CreateIDPCategoryController(CategoryController):
    def execute(self, data: dict): return self.create(data)

class ViewIDPCategoryController(CategoryController):
    def execute(self, category_id: str): return self.view(category_id)

class UpdateIDPCategoryController(CategoryController):
    def execute(self, category_id: str, data: dict): return self.update(category_id, data)

class DeleteIDPCategoryController(CategoryController):
    def execute(self, category_id: str): return self.delete(category_id)

class SearchIDPCategoryController(CategoryController):
    def execute(self, query: str = ""): return self.list(query)

CreateIDPCC = CreateIDPCategoryController
ViewIDPCC = ViewIDPCategoryController
UpdateIDPCC = UpdateIDPCategoryController
DeleteIDPCC = DeleteIDPCategoryController
SearchIDPCC = SearchIDPCategoryController


# ---------------------------------------------------------------------------
# SPRINT 3 : PLATFORM REPORTS (US44..US46)
# ---------------------------------------------------------------------------

class PlatformReportController(Controller):
    def require_manager(self):
        account, profile = effective_access(self.repository, self.actor_id)
        if profile.role != "manager" or "reports:read" not in profile.permissions:
            raise AppError("FORBIDDEN", "Manager report permissions required.")
        return account.account_id

    def generate(self, kind: str, value: str):
        self.require_manager()
        return ReportService(ReportRepository(self.repository)).generate(kind, value)

class GenerateDailyReportController(PlatformReportController):
    def execute(self, period: str = None): return self.generate("daily", period)

class GenerateWeeklyReportController(PlatformReportController):
    def execute(self, period: str = None): return self.generate("weekly", period)

class GenerateMonthlyReportController(PlatformReportController):
    def execute(self, period: str = None): return self.generate("monthly", period)

GenerateDailyReportC = GenerateDailyReportController
GenerateWeeklyReportC = GenerateWeeklyReportController
GenerateMonthlyReportC = GenerateMonthlyReportController
