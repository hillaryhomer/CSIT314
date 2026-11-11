"""Central HTTP Boundary for CSIT314 Interior Designer Platform (Atelier Match).
Implements the BCE Boundary layer, mediating between incoming HTTP requests
and application controllers.
"""
from flask import g, jsonify, request, Response
import secrets

from backend.controllers import (
    LoginController, CompanyController,
    CreateProfileController, ViewProfileController, UpdateProfileController,
    SuspendProfileController, SearchProfileController,
    CreateUserAccountController, ViewUserAccountController, UpdateUserAccountController,
    SuspendUserAccountController, SearchUserAccountController,
    ProjectController, CustomerProjectController, SearchIDPC,
    SearchIDPController, ViewIDPController, AddFavouriteController,
    ViewFavouriteListController, SearchFavouriteListController,
    ViewIDPViewsController, RecordIDPViewController,
    CreateIDPCategoryController, ViewIDPCategoryController,
    UpdateIDPCategoryController, DeleteIDPCategoryController, SearchIDPCategoryController,
    GenerateDailyReportController, GenerateWeeklyReportController, GenerateMonthlyReportController,
    effective_access,
)
from backend.database import ProjectRepository, CompanyRepository
from backend.models import AppError
from backend.validation import check_object


def register_project_routes(app, repository):
    controls = {
        'current': (ProjectController, ProjectController, ProjectController, ProjectController, SearchIDPC),
        'past': (ProjectController, ProjectController, ProjectController, ProjectController, SearchIDPC),
    }

    @app.get('/api/designer/projects/<kind>')
    def search_projects(kind):
        if kind not in ('current', 'past'):
            raise AppError('NOT_FOUND', 'Project collection was not found.')
        status = 'Current' if kind == 'current' else 'Past'
        return jsonify(SearchIDPC(repository(), g.actor_id).execute(request.args.get('q', ''), status=status))

    @app.post('/api/designer/projects/<kind>')
    def create_project(kind):
        status = 'Current' if kind == 'current' else 'Past'
        return jsonify(ProjectController(repository(), g.actor_id).create(status, request.get_json())), 201

    @app.get('/api/designer/projects/<kind>/<project_id>')
    def view_project(kind, project_id):
        return jsonify(ProjectController(repository(), g.actor_id).view(project_id))

    @app.put('/api/designer/projects/<kind>/<project_id>')
    def update_project(kind, project_id):
        return jsonify(ProjectController(repository(), g.actor_id).update(project_id, request.get_json()))

    @app.delete('/api/designer/projects/<kind>/<project_id>')
    def delete_project(kind, project_id):
        request.get_json()
        return jsonify(ProjectController(repository(), g.actor_id).delete(project_id))

    @app.get('/api/project-categories')
    def project_categories():
        return jsonify(ProjectRepository(repository()).categories())

    @app.get('/api/project-images/<image_id>')
    def project_image(image_id):
        image = CustomerProjectController(repository(), getattr(g, 'actor_id', None)).image(image_id)
        response = Response(image['content'], mimetype=image['mime_type'])
        response.headers['Content-Disposition'] = 'inline'
        return response


def register_customer_routes(app, repository):
    def check_query(allowed):
        if set(request.args) - allowed:
            raise AppError('VALIDATION', 'Unsupported search field.')

    @app.get('/api/catalog/projects')
    def search_customer_projects():
        check_query({'q', 'categoryId', 'style'})
        return jsonify(SearchIDPController(repository(), g.actor_id).execute(
            request.args.get('q', ''), request.args.get('categoryId', ''), request.args.get('style', '')))

    @app.get('/api/catalog/projects/<project_id>')
    def view_customer_project(project_id):
        check_query(set())
        return jsonify(ViewIDPController(repository(), g.actor_id).execute(project_id))

    @app.get('/api/catalog/styles')
    def project_styles():
        check_query(set())
        return jsonify(ProjectRepository(repository()).styles())

    @app.post('/api/favourites')
    def add_favourite():
        check_query(set())
        result = AddFavouriteController(repository(), g.actor_id).execute(request.get_json())
        return jsonify(result), 201 if result['created'] else 200

    @app.get('/api/favourites')
    def view_favourites():
        check_query({'q'})
        if 'q' in request.args:
            return jsonify(SearchFavouriteListController(repository(), g.actor_id).execute(request.args['q']))
        return jsonify(ViewFavouriteListController(repository(), g.actor_id).execute())


def register_activity_routes(app, repository):
    def query():
        if request.args:
            raise AppError('VALIDATION', 'Unsupported analytics field.')

    @app.get('/api/designer/analytics')
    def analytics():
        query()
        return jsonify(ViewIDPViewsController(repository(), g.actor_id).execute())

    @app.get('/api/designer/analytics/<project_id>')
    def project_analytics(project_id):
        query()
        return jsonify(ViewIDPViewsController(repository(), g.actor_id).execute(project_id))

    @app.post('/api/catalog/projects/<project_id>/views')
    def record_view(project_id):
        query()
        return jsonify(RecordIDPViewController(repository(), g.actor_id).execute(project_id, request.get_json()))


def register_manager_routes(app, repository):
    def query(allowed=()):
        if set(request.args) - set(allowed):
            raise AppError('VALIDATION', 'Unsupported query field.')

    @app.get('/api/manager/categories')
    def search():
        query({'q'})
        return jsonify(SearchIDPCategoryController(repository(), g.actor_id).execute(request.args.get('q', '')))

    @app.post('/api/manager/categories')
    def create():
        query()
        return jsonify(CreateIDPCategoryController(repository(), g.actor_id).execute(request.get_json())), 201

    @app.get('/api/manager/categories/<category_id>')
    def view(category_id):
        query()
        return jsonify(ViewIDPCategoryController(repository(), g.actor_id).execute(category_id))

    @app.put('/api/manager/categories/<category_id>')
    def update(category_id):
        query()
        return jsonify(UpdateIDPCategoryController(repository(), g.actor_id).execute(category_id, request.get_json()))

    @app.delete('/api/manager/categories/<category_id>')
    def delete(category_id):
        query()
        check_object(request.get_json(), set())
        return jsonify(DeleteIDPCategoryController(repository(), g.actor_id).execute(category_id))

    @app.get('/api/manager/reports/<kind>')
    def report(kind):
        query({'period'})
        controls = {
            'daily': GenerateDailyReportController,
            'weekly': GenerateWeeklyReportController,
            'monthly': GenerateMonthlyReportController,
        }
        if kind not in controls:
            raise AppError('NOT_FOUND', 'Report type was not found.')
        return jsonify(controls[kind](repository(), g.actor_id).execute(request.args.get('period')))


def register_all_routes(app, repository, context=None):
    """Registers all BCE boundary routes onto the Flask application."""
    @app.get('/api/health')
    def health():
        return jsonify(status="ok")

    @app.post('/api/auth/login')
    def login():
        token, payload = LoginController(repository(), None).execute(
            request.get_json(), request.cookies.get('csit314_session', '')
        )
        response = jsonify(payload)
        response.set_cookie(
            'csit314_session', token, max_age=28800, httponly=True,
            secure=app.config.get('SESSION_COOKIE_SECURE', False), samesite='Strict', path='/'
        )
        return response

    @app.get('/api/auth/session')
    def current_session():
        account, profile = effective_access(repository(), g.actor_id)
        stored = CompanyRepository(repository()).session(request.cookies.get('csit314_session'))
        from backend.app import DevelopmentContext
        is_dev = isinstance(context, DevelopmentContext) if context else False
        return jsonify(
            account=account.to_dict(profile), role=profile.role, permissions=profile.permissions,
            csrfToken=stored['csrf_token'] if stored else '', development=is_dev
        )

    @app.post('/api/auth/logout')
    def logout():
        request.get_json()
        CompanyRepository(repository()).remove_session(request.cookies.get('csit314_session', ''))
        response = jsonify(loggedOut=True)
        response.delete_cookie('csit314_session', path='/', samesite='Strict')
        return response

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

    @app.get('/api/profiles')
    def search_profiles():
        return jsonify(SearchProfileController(repository(), g.actor_id).execute(request.args.get('name', '')))

    @app.post('/api/profiles')
    def create_profile():
        return jsonify(CreateProfileController(repository(), g.actor_id).execute(request.get_json())), 201

    @app.get('/api/profiles/<profile_id>')
    def view_profile(profile_id):
        return jsonify(ViewProfileController(repository(), g.actor_id).execute(profile_id))

    @app.put('/api/profiles/<profile_id>')
    def update_profile(profile_id):
        return jsonify(UpdateProfileController(repository(), g.actor_id).execute(profile_id, request.get_json()))

    @app.post('/api/profiles/<profile_id>/suspend')
    def suspend_profile(profile_id):
        request.get_json()
        return jsonify(SuspendProfileController(repository(), g.actor_id).execute(profile_id))

    @app.get('/api/accounts')
    def list_accounts():
        if set(request.args) - {'q', 'username', 'email'}:
            raise AppError('VALIDATION', 'Unsupported account search field.')
        return jsonify(SearchUserAccountController(repository(), g.actor_id).execute(
            request.args.get('q', request.args.get('username', request.args.get('email', '')))
        ))

    @app.post('/api/accounts')
    def create_account():
        return jsonify(CreateUserAccountController(repository(), g.actor_id).execute(request.get_json())), 201

    @app.get('/api/accounts/<account_id>')
    def view_account(account_id):
        return jsonify(ViewUserAccountController(repository(), g.actor_id).execute(account_id))

    @app.put('/api/accounts/<account_id>')
    def update_account(account_id):
        return jsonify(UpdateUserAccountController(repository(), g.actor_id).execute(account_id, request.get_json()))

    @app.post('/api/accounts/<account_id>/suspend')
    def suspend_account(account_id):
        request.get_json()
        return jsonify(SuspendUserAccountController(repository(), g.actor_id).execute(account_id))

    # Register Project, Customer, Activity, and Manager route groups
    register_project_routes(app, repository)
    register_customer_routes(app, repository)
    register_activity_routes(app, repository)
    register_manager_routes(app, repository)

