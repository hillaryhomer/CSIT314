"""Customer HTTP Boundary. Customer ownership is resolved strictly from session."""
from flask import g, jsonify, request

from backend.customer_controllers import (SearchIDPController, ViewIDPController, AddFavouriteController,
                                          ViewFavouriteListController, SearchFavouriteListController)
from backend.models import AppError
from backend.project_repository import ProjectRepository


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
