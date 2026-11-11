"""Boundary: Flask application factory, request lifecycle, and CLI entrypoint.
Mediates between HTTP requests, session management, and BCE boundary handlers.
"""

import argparse
import os
from pathlib import Path
import secrets
import sqlite3
import sys
from getpass import getpass
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from flask import Flask, Request, g, jsonify, request, send_from_directory
from werkzeug.exceptions import BadRequest, NotFound, RequestEntityTooLarge

from backend.boundary import register_all_routes
from backend.controllers import effective_access
from backend.database import Repository, CompanyRepository, connect_database, initialize_database
from backend.models import AppError, UserAccount, UserProfile
from backend.validation import hash_password, validate_account


class AuthenticatedContext:
    """Resolve an opaque, expiring session against server-side storage."""

    def __init__(self, database_path=None):
        self.database_path = database_path

    def resolve(self, incoming_request: Request) -> str | None:
        if not self.database_path:
            return None
        connection = connect_database(self.database_path)
        try:
            stored = CompanyRepository(Repository(connection)).session(incoming_request.cookies.get('csit314_session'))
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
                if not repository.profile_with_id(profile.profile_id) and not repository.profile_with_name(profile.name):
                    repository.create_profile(profile)
            admin_prof = repository.profile_with_name("User Admin")
            prof_id = admin_prof.profile_id if admin_prof else "dev-profile-admin"
            if not repository.account_with_id("dev-admin") and not repository.account_with_username("dev.admin"):
                repository.create_account(UserAccount(
                    "dev-admin", "dev.admin", "dev.admin@example.test",
                    hash_password(secrets.token_urlsafe(24)), prof_id,
                ))
    finally:
        connection.close()


def create_app(database_path: str = "data/atelier_match.sqlite",
               auth_context: AuthenticatedContext | None = None,
               allowed_origin: str = "http://127.0.0.1:5173",
               static_directory: str | None = None) -> Flask:
    app = Flask(__name__, static_folder=None)
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
    initialize_database(database_path)
    context = auth_context or AuthenticatedContext(database_path)
    app.config['SESSION_COOKIE_SECURE'] = os.getenv('COOKIE_SECURE', '0') == '1'
    allowed_origins = {
        allowed_origin,
        "http://127.0.0.1:5173", "http://localhost:5173",
        "http://127.0.0.1:3001", "http://localhost:3001",
    }

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
        if not request.path.startswith("/api/") or request.path in ("/api/health", "/api/auth/login"):
            return None
        # Keep existing small JSON limits, while allowing atomic project/image submissions.
        request.max_content_length = 16 * 1024 * 1024 if request.path.startswith('/api/designer/projects/') else 16 * 1024
        if request.method == 'GET' and (request.path.startswith('/api/catalog/projects') or request.path.startswith('/api/project-images/') or request.path in ('/api/project-categories', '/api/catalog/styles')):
            g.actor_id = context.resolve(request)
            return None
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            if not request.is_json:
                raise AppError("VALIDATION", "Use application/json for writes.")
        g.actor_id = context.resolve(request)
        if not g.actor_id:
            raise AppError("UNAUTHENTICATED", "An authenticated session is required.")
        if request.method in ('POST', 'PUT', 'PATCH', 'DELETE') and not isinstance(context, DevelopmentContext):
            stored = CompanyRepository(repository()).session(request.cookies.get('csit314_session'))
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

    # Register all BCE HTTP endpoints through the Boundary layer
    register_all_routes(app, repository, context=context)

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
    parser = argparse.ArgumentParser(description="Interior Designer Platform API")
    parser.add_argument("--dev", action="store_true", help="Use the development administrator identity")
    parser.add_argument("--init", action="store_true", help="Initialize the database tables")
    parser.add_argument("--seed", action="store_true", help="Add development sample data")
    parser.add_argument('--create-admin', action='store_true', help='Interactively create an administrator; never overwrites existing accounts')
    parser.add_argument("--serve-ui", action="store_true", help="Serve the built React application")
    args = parser.parse_args()
    environment = os.getenv("APP_ENV", os.getenv("NODE_ENV", "development" if args.dev else "production"))
    if args.dev and environment != "development":
        parser.error("--dev is disabled outside development.")
    filename = os.getenv("DATABASE_PATH", "data/atelier_match.sqlite")
    if args.create_admin:
        initialize_database(filename)
        connection = connect_database(filename)
        repository = Repository(connection)
        try:
            username = input('Admin username: ')
            email = input('Admin email: ')
            password = getpass('Password (6+ characters): ')
            if password != getpass('Confirm password: '):
                parser.error('Passwords do not match.')
            profile_id = 'UP-' + str(uuid4())
            values = validate_account(dict(username=username, email=email, password=password, profileId=profile_id), creating=True)
            password_hash = hash_password(password)
            with repository.transaction():
                if repository.account_with_username(values['username']) or repository.account_with_email(values['email']):
                    raise AppError('DUPLICATE', 'Username or email already exists; no account was changed.')
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
        seed_development(filename, "development")
        print("Development sample data initialized.")
    elif args.init:
        initialize_database(filename)
        print("Database schema initialized (existing data preserved).")
    else:
        auth = DevelopmentContext(environment, os.getenv("DEV_ADMIN_ACCOUNT_ID", "dev-admin")) if args.dev else None
        ui_dir = "dist" if (args.serve_ui or Path("dist/index.html").is_file()) else None
        default_origin = 'http://127.0.0.1:' + (os.getenv('PORT', '3002') if ui_dir else '5173')
        app = create_app(filename, auth, os.getenv("APP_ORIGIN", default_origin), ui_dir)
        print("Development identity, not real login." if args.dev else "Session authentication enabled.")
        if ui_dir:
            print("Serving full web application (UI + Backend) on http://127.0.0.1:3002")
        app.run(host="127.0.0.1", port=int(os.getenv("PORT", "3002")), debug=False)


if __name__ == "__main__":
    main()
