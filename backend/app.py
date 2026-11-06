"""Boundary: accept HTTP requests, call controllers, and return JSON."""

import argparse
import os
from pathlib import Path
import secrets
import sqlite3
from getpass import getpass
from uuid import uuid4

from flask import Flask, Request, g, jsonify, request, send_from_directory
from werkzeug.exceptions import BadRequest, NotFound, RequestEntityTooLarge

from backend.controllers import (
    CreateUserProfileController, ViewUserProfileController,
    UpdateUserProfileController, SuspendUserProfileController,
    SearchUserProfileController, CreateUserAccountController,
    ViewUserAccountController, UpdateUserAccountController,
)
from backend.database import Repository, connect_database, initialize_database
from backend.models import AppError, UserAccount, UserProfile
from backend.validation import hash_password, validate_account
from backend.controllers import effective_access
from backend.member2_repository import Member2Repository
from backend.member2 import LoginController, SearchUserAccountController, SuspendUserAccountController, CompanyController
from backend.project_boundary import register_project_routes
from backend.customer_boundary import register_customer_routes
from backend.activity_boundary import register_activity_routes
from backend.manager_boundary import register_manager_routes


class AuthenticatedContext:
    """Resolve an opaque, expiring session against server-side storage."""

    def __init__(self, database_path=None):
        self.database_path = database_path

    def resolve(self, incoming_request: Request) -> str | None:
        if not self.database_path:
            return None
        connection = connect_database(self.database_path)
        try:
            stored = Member2Repository(Repository(connection)).session(incoming_request.cookies.get('csit314_session'))
            return stored['account_id'] if stored else None
        finally:
            connection.close()


class DevelopmentContext(AuthenticatedContext):
    def __init__(self, environment: str, account_id: str = "dev-admin"):
        if environment != "development":
            raise ValueError("Development identity is disabled outside development.")
        self.account_id = account_id

    def resolve(self, incoming_request: Request) -> str:
        # Do not take identity or role from the body, headers, or UI role selector.
        return self.account_id


def seed_development(filename: str, environment: str) -> None:
    if environment != "development":
        raise ValueError("Development seed is disabled outside development.")
    initialize_database(filename)
    connection = connect_database(filename)
    repository = Repository(connection)
    samples = [
        UserProfile("dev-profile-admin", "User Admin", "admin",
                    ["profiles:read", "profiles:write", "accounts:read", "accounts:write"]),
        UserProfile("dev-profile-designer", "Interior Designer", "designer", ["projects:manage"]),
        UserProfile("dev-profile-customer", "Customer", "customer", ["projects:discover"]),
        UserProfile("dev-profile-manager", "Platform Manager", "manager", ["reports:read", "categories:manage"]),
    ]
    try:
        with repository.transaction():
            for profile in samples:
                if not repository.find_profile(profile.profile_id):
                    repository.create_profile(profile)
            if not repository.find_account("dev-admin"):
                repository.create_account(UserAccount(
                    "dev-admin", "dev.admin", "dev.admin@example.test",
                    hash_password(secrets.token_urlsafe(24)), "dev-profile-admin",
                ))
    finally:
        connection.close()


def create_app(database_path: str = "data/member1.sqlite",
               auth_context: AuthenticatedContext | None = None,
               allowed_origin: str = "http://127.0.0.1:5173",
               static_directory: str | None = None) -> Flask:
    app = Flask(__name__, static_folder=None)
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
    initialize_database(database_path)
    context = auth_context or AuthenticatedContext(database_path)
    app.config['SESSION_COOKIE_SECURE'] = os.getenv('COOKIE_SECURE', '0') == '1'

    def repository() -> Repository:
        if "database" not in g:
            g.database = connect_database(database_path)
        return Repository(g.database)

    @app.teardown_appcontext
    def close_database(error):
        connection = g.pop("database", None)
        if connection is not None:
            connection.close()

    @app.before_request
    def check_request():
        if not request.path.startswith("/api/") or request.path == "/api/health":
            return None
        # Keep existing small JSON limits, while allowing atomic project/image submissions.
        request.max_content_length = 16 * 1024 * 1024 if request.path.startswith('/api/designer/projects/') else 16 * 1024
        if request.method == 'GET' and (request.path.startswith('/api/catalog/projects') or request.path.startswith('/api/project-images/') or request.path in ('/api/project-categories', '/api/catalog/styles')):
            g.actor_id = context.resolve(request)
            return None
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            if request.headers.get("Origin") not in (None, allowed_origin):
                raise AppError("FORBIDDEN", "The request origin is not permitted.")
            if not request.is_json:
                raise AppError("VALIDATION", "Use application/json for writes.")
        if request.path == '/api/auth/login':
            return None
        g.actor_id = context.resolve(request)
        if not g.actor_id:
            raise AppError("UNAUTHENTICATED", "An authenticated session is required.")
        if request.method in ('POST', 'PUT', 'PATCH', 'DELETE') and not isinstance(context, DevelopmentContext):
            stored = Member2Repository(repository()).session(request.cookies.get('csit314_session'))
            if not stored or not secrets.compare_digest(stored['csrf_token'], request.headers.get('X-CSRF-Token', '')):
                raise AppError('FORBIDDEN', 'Invalid session security token. Refresh and retry.')
        if request.path != '/api/auth/logout':
            effective_access(repository(), g.actor_id)

    @app.after_request
    def response_headers(response):
        if request.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
            response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.errorhandler(AppError)
    def application_error(error):
        status = {
            "VALIDATION": 400, "UNAUTHENTICATED": 401, "FORBIDDEN": 403,
            "NOT_FOUND": 404, "DUPLICATE": 409, "ALREADY_SUSPENDED": 409,
            "PERSISTENCE": 500,
        }[error.code]
        return jsonify(error={"code": error.code, "message": error.message,
                              "fields": error.fields}), status

    @app.errorhandler(sqlite3.Error)
    def storage_error(error):
        app.logger.error("SQLite operation failed", exc_info=error)
        return application_error(AppError("PERSISTENCE", "The data could not be stored or retrieved. Please retry."))

    @app.errorhandler(BadRequest)
    @app.errorhandler(RequestEntityTooLarge)
    def invalid_json(error):
        return application_error(AppError("VALIDATION", "The request body is invalid or too large."))

    @app.errorhandler(404)
    @app.errorhandler(405)
    def missing_endpoint(error):
        return application_error(AppError("NOT_FOUND", "This endpoint does not exist."))

    @app.get("/api/health")
    def health():
        return jsonify(status="ok")

    @app.post('/api/auth/login')
    def login():
        token, payload = LoginController(repository(), None).execute(request.get_json(), request.cookies.get('csit314_session', ''))
        response = jsonify(payload)
        response.set_cookie('csit314_session', token, max_age=28800, httponly=True,
                            secure=app.config['SESSION_COOKIE_SECURE'], samesite='Strict', path='/')
        return response

    @app.get('/api/auth/session')
    def current_session():
        account, profile = effective_access(repository(), g.actor_id)
        stored = Member2Repository(repository()).session(request.cookies.get('csit314_session'))
        return jsonify(account=account.to_dict(profile), role=profile.role, permissions=profile.permissions,
                       csrfToken=stored['csrf_token'] if stored else '', development=isinstance(context, DevelopmentContext))

    @app.post('/api/auth/logout')
    def logout():
        request.get_json()
        Member2Repository(repository()).remove_session(request.cookies.get('csit314_session', ''))
        response = jsonify(loggedOut=True)
        response.delete_cookie('csit314_session', path='/', samesite='Strict')
        return response

    @app.post('/api/accounts/<account_id>/suspend')
    def suspend_account(account_id):
        request.get_json()
        return jsonify(SuspendUserAccountController(repository(), g.actor_id).execute(account_id))

    @app.get('/api/company')
    def view_company():
        return jsonify(CompanyController(repository(), g.actor_id).view(request.args.get('q', '')))

    @app.post('/api/company')
    def create_company():
        return jsonify(CompanyController(repository(), g.actor_id).create(request.get_json())), 201

    @app.put('/api/company/<company_id>')
    def update_company(company_id):
        return jsonify(CompanyController(repository(), g.actor_id).update(company_id, request.get_json()))

    @app.delete('/api/company/<company_id>')
    def delete_company(company_id):
        request.get_json()
        return jsonify(CompanyController(repository(), g.actor_id).delete(company_id))

    @app.get("/api/profiles")
    def search_profiles():
        controller = SearchUserProfileController(repository(), g.actor_id)
        return jsonify(controller.execute(request.args.get("name", "")))

    @app.post("/api/profiles")
    def create_profile():
        controller = CreateUserProfileController(repository(), g.actor_id)
        return jsonify(controller.execute(request.get_json())), 201

    @app.get("/api/profiles/<profile_id>")
    def view_profile(profile_id):
        return jsonify(ViewUserProfileController(repository(), g.actor_id).execute(profile_id))

    @app.put("/api/profiles/<profile_id>")
    def update_profile(profile_id):
        controller = UpdateUserProfileController(repository(), g.actor_id)
        return jsonify(controller.execute(profile_id, request.get_json()))

    @app.post("/api/profiles/<profile_id>/suspend")
    def suspend_profile(profile_id):
        request.get_json()  # Still reject malformed JSON; identity is not read from the body.
        return jsonify(SuspendUserProfileController(repository(), g.actor_id).execute(profile_id))

    @app.get("/api/accounts")
    def list_accounts():
        if set(request.args) - {'q', 'username', 'email'}:
            raise AppError('VALIDATION', 'Unsupported account search field.')
        return jsonify(SearchUserAccountController(repository(), g.actor_id).execute(
            request.args.get('q', request.args.get('username', request.args.get('email', '')))))

    @app.post("/api/accounts")
    def create_account():
        controller = CreateUserAccountController(repository(), g.actor_id)
        return jsonify(controller.execute(request.get_json())), 201

    @app.get("/api/accounts/<account_id>")
    def view_account(account_id):
        return jsonify(ViewUserAccountController(repository(), g.actor_id).execute(account_id))

    @app.put("/api/accounts/<account_id>")
    def update_account(account_id):
        controller = UpdateUserAccountController(repository(), g.actor_id)
        return jsonify(controller.execute(account_id, request.get_json()))

    register_project_routes(app, repository)
    register_customer_routes(app, repository)
    register_activity_routes(app, repository)
    register_manager_routes(app, repository)

    if static_directory:
        directory = Path(static_directory).resolve()

        @app.get("/")
        @app.get("/<path:path>")
        def frontend(path=""):
            if path.startswith("api/"):
                raise AppError("NOT_FOUND", "This API endpoint does not exist.")
            if (directory / path).is_file():
                return send_from_directory(directory, path)
            if "." in Path(path).name:
                raise NotFound()
            return send_from_directory(directory, "index.html")

    return app


def main():
    parser = argparse.ArgumentParser(description="Backend Python Member 1")
    parser.add_argument("--dev", action="store_true", help="Use the development administrator identity")
    parser.add_argument("--init", action="store_true", help="Initialize the database tables")
    parser.add_argument("--seed", action="store_true", help="Add development sample data")
    parser.add_argument('--create-admin', action='store_true', help='Interactively create an administrator; never overwrites existing accounts')
    parser.add_argument("--serve-ui", action="store_true", help="Serve the built React application")
    args = parser.parse_args()
    environment = os.getenv("APP_ENV", os.getenv("NODE_ENV", "development" if args.dev else "production"))
    if args.dev and environment != "development":
        parser.error("--dev is disabled outside development.")
    filename = os.getenv("DATABASE_PATH", "data/member1.sqlite")
    if args.create_admin:
        initialize_database(filename)
        connection = connect_database(filename)
        repository = Repository(connection)
        try:
            username = input('Admin username: ')
            email = input('Admin email: ')
            password = getpass('Password (12+ characters): ')
            if password != getpass('Confirm password: '):
                parser.error('Passwords do not match.')
            profile_id = 'UP-' + str(uuid4())
            values = validate_account(dict(username=username, email=email, password=password, profileId=profile_id), creating=True)
            password_hash = hash_password(password)
            with repository.transaction():
                if repository.account_with_username(values['username']) or repository.account_with_email(values['email']):
                    raise AppError('DUPLICATE', 'Username or email already exists; no account was changed.')
                # Each CLI-created admin receives an independent profile to preserve existing roles.
                profile = UserProfile(profile_id, 'Administrator ' + values['username'], 'admin',
                    ['profiles:read', 'profiles:write', 'accounts:read', 'accounts:write'])
                repository.create_profile(profile)
                repository.create_account(UserAccount('UA-' + str(uuid4()), password_hash=password_hash, **values))
            print('Administrator created. Start the backend without --dev to sign in.')
        except AppError as error:
            parser.error(error.message + (' ' + str(error.fields) if error.fields else ''))
        finally:
            connection.close()
    elif args.seed:
        seed_development(filename, environment)
        print("Development sample data initialized.")
    elif args.init:
        initialize_database(filename)
        print("Database schema initialized (existing data preserved).")
    else:
        auth = DevelopmentContext(environment, os.getenv("DEV_ADMIN_ACCOUNT_ID", "dev-admin")) if args.dev else None
        default_origin = 'http://127.0.0.1:' + (os.getenv('PORT', '3001') if args.serve_ui else '5173')
        app = create_app(filename, auth, os.getenv("APP_ORIGIN", default_origin),
                         "dist" if args.serve_ui else None)
        print("Development identity, not real login." if args.dev else "Session authentication enabled.")
        app.run(host="127.0.0.1", port=int(os.getenv("PORT", "3001")), debug=False)


if __name__ == "__main__":
    main()
