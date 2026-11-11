"""Company and Authentication controllers for Interior Designer Platform."""

import secrets
from uuid import uuid4

from backend.controllers import Controller, effective_access
from backend.models import AppError
from backend.validation import check_object, clean, normalize, verify_password, hash_password
from backend.company_repository import CompanyRepository


class LoginController(Controller):
    # Used for unknown users too, keeping a bcrypt check in both credential paths.
    dummy_hash = None

    def execute(self, data, previous_token=''):
        check_object(data, {'identifier', 'password'})
        identifier, password = clean(data.get('identifier')), data.get('password')
        if not identifier or len(identifier) > 254 or not isinstance(password, str) or len(password.encode()) > 72:
            raise AppError('VALIDATION', 'Enter a username/email and password.')
        account = (self.repository.account_with_username(identifier)
                   or self.repository.account_with_email(identifier))
        if LoginController.dummy_hash is None:
            LoginController.dummy_hash = hash_password(secrets.token_urlsafe(24))
        valid = verify_password(password, account.password_hash if account else LoginController.dummy_hash)
        if not account or not valid:
            raise AppError('UNAUTHENTICATED', 'Incorrect username/email or password.')
        store = CompanyRepository(self.repository)
        with self.repository.transaction():
            _, profile = effective_access(self.repository, account.account_id)
            token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
            store.remove_session(previous_token)
            store.create_session(token, account.account_id, csrf)
        return token, {'account': account.to_dict(profile), 'role': profile.role,
                       'permissions': profile.permissions, 'csrfToken': csrf}


class SearchUserAccountController(Controller):
    def execute(self, query=''):
        self.require_admin('accounts:read')
        if not isinstance(query, str) or len(query) > 254:
            raise AppError('VALIDATION', 'Search must contain at most 254 characters.')
        keyword = normalize(query)
        return [a.to_dict(self.get_profile(a.profile_id)) for a in self.repository.list_accounts()
                if keyword in normalize(a.username) or keyword in normalize(a.email)]


class SuspendUserAccountController(Controller):
    def execute(self, account_id):
        with self.repository.transaction():
            actor, _ = self.require_admin('accounts:write')
            account = self.get_account(account_id)
            if account.account_id == actor.account_id:
                raise AppError('FORBIDDEN', 'You cannot suspend your own account.')
            if account.status == 'Suspended':
                raise AppError('ALREADY_SUSPENDED', 'This account is already suspended.')
            CompanyRepository(self.repository).suspend_account(account_id)
            account.status = 'Suspended'
        return account.to_dict(self.get_profile(account.profile_id))


def validate_company(data):
    check_object(data, {'name', 'regNumber', 'address', 'contact', 'description'})
    limits = {'name': 120, 'regNumber': 80, 'address': 500, 'contact': 254, 'description': 4000}
    values, errors = {}, {}
    for field, limit in limits.items():
        raw = data.get(field, '')
        value = clean(raw)
        values[field] = value
        if not isinstance(raw, str) or len(value) > limit or (field in ('name', 'address', 'contact') and not value):
            errors[field] = f'Enter text of {1 if field in ("name", "address", "contact") else 0}-{limit} characters.'
    if errors:
        raise AppError('VALIDATION', 'Please correct the highlighted fields.', errors)
    return values


class CompanyController(Controller):
    def owner(self):
        account, profile = effective_access(self.repository, self.actor_id)
        if profile.role != 'designer':
            raise AppError('FORBIDDEN', 'Interior Designer access is required.')
        return account.account_id

    def view(self, query=''):
        owner = self.owner()
        if len(query) > 254:
            raise AppError('VALIDATION', 'Search must contain at most 254 characters.')
        company = CompanyRepository(self.repository).company(owner)
        return {'company': company, 'matches': bool(company and normalize(query) in normalize(' '.join(
            company[k] for k in ('name', 'regNumber', 'address', 'contact', 'description'))))}

    def create(self, data):
        values = validate_company(data)
        with self.repository.transaction():
            owner = self.owner()
            if CompanyRepository(self.repository).company(owner):
                raise AppError('DUPLICATE', 'You already have company information. Edit the existing company.')
            CompanyRepository(self.repository).create_company('CO-' + str(uuid4()), owner, values)
        return CompanyRepository(self.repository).company(owner)

    def update(self, company_id, data):
        values = validate_company(data)
        with self.repository.transaction():
            owner = self.owner()
            current = CompanyRepository(self.repository).company(owner)
            if not current or current['companyId'] != company_id:
                raise AppError('NOT_FOUND', 'Company was not found.')
            CompanyRepository(self.repository).update_company(company_id, owner, values)
        return CompanyRepository(self.repository).company(owner)

    def delete(self, company_id):
        with self.repository.transaction():
            owner = self.owner()
            current = CompanyRepository(self.repository).company(owner)
            if not current or current['companyId'] != company_id:
                raise AppError('NOT_FOUND', 'Company was not found.')
            CompanyRepository(self.repository).delete_company(company_id, owner)
        return {'deleted': True}


# BCE Aliases and Controllers matching CSIT314 diagram notations
SuspendUAC = SuspendUserAccountController
SearchUAC = SearchUserAccountController
LogInUAC = LoginController


class LogOutSessionC(Controller):
    """US12, US19, US36, US48: Log Out Platform Session BCE Control."""
    def execute(self, session_token=''):
        CompanyRepository(self.repository).remove_session(session_token)
        return {'loggedOut': True}


class CreateCIC(CompanyController):
    """US13: Create Company Information BCE Control."""
    def execute(self, data): return self.create(data)


class ViewCIC(CompanyController):
    """US14: View Company Information BCE Control."""
    def execute(self, query=''): return self.view(query)


class UpdateCIC(CompanyController):
    """US15: Update Company Information BCE Control."""
    def execute(self, company_id, data): return self.update(company_id, data)


class DeleteCIC(CompanyController):
    """US16: Delete Company Information BCE Control."""
    def execute(self, company_id): return self.delete(company_id)


class SearchCIC(CompanyController):
    """US17: Search Company Information BCE Control."""
    def execute(self, query=''): return self.view(query)

