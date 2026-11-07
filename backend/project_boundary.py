"""HTTP Boundary for the ten project use cases and shared read adapters."""
from flask import g, jsonify, request, Response

from backend.models import AppError
from backend.project_repository import ProjectRepository
from backend.project_controllers import (
    CreateCurrentIDPController, ViewCurrentIDPController, UpdateCurrentIDPController,
    DeleteCurrentIDPController, SearchCurrentIDPController,
    CreatePastIDPController, ViewPastIDPController, UpdatePastIDPController,
    DeletePastIDPController, SearchPastIDPController, CustomerProjectController,
    SearchIDPC,
)


def register_project_routes(app, repository):
    controls = {
        'current': (CreateCurrentIDPController, ViewCurrentIDPController, UpdateCurrentIDPController, DeleteCurrentIDPController, SearchCurrentIDPController),
        'past': (CreatePastIDPController, ViewPastIDPController, UpdatePastIDPController, DeletePastIDPController, SearchPastIDPController),
    }

    def controller(kind, index):
        if kind not in controls:
            raise AppError('NOT_FOUND', 'Project collection was not found.')
        return controls[kind][index](repository(), g.actor_id)

    @app.get('/api/designer/projects/<kind>')
    def search_projects(kind):
        # US24 & US29 in CSIT314_Consistency_Fixes: boundary supplies status filter to shared SearchIDPC
        if kind not in ('current', 'past'):
            raise AppError('NOT_FOUND', 'Project collection was not found.')
        status = 'Current' if kind == 'current' else 'Past'
        return jsonify(SearchIDPC(repository(), g.actor_id).execute(request.args.get('q', ''), status=status))

    @app.post('/api/designer/projects/<kind>')
    def create_project(kind):
        return jsonify(controller(kind, 0).execute(request.get_json())), 201

    @app.get('/api/designer/projects/<kind>/<project_id>')
    def view_project(kind, project_id):
        return jsonify(controller(kind, 1).execute(project_id))

    @app.put('/api/designer/projects/<kind>/<project_id>')
    def update_project(kind, project_id):
        return jsonify(controller(kind, 2).execute(project_id, request.get_json()))

    @app.delete('/api/designer/projects/<kind>/<project_id>')
    def delete_project(kind, project_id):
        request.get_json()
        return jsonify(controller(kind, 3).execute(project_id))

    @app.get('/api/project-categories')
    def project_categories():
        return jsonify(ProjectRepository(repository()).categories())

    @app.get('/api/project-images/<image_id>')
    def project_image(image_id):
        image = CustomerProjectController(repository(), getattr(g, 'actor_id', None)).image(image_id)
        response = Response(image['content'], mimetype=image['mime_type'])
        response.headers['Content-Disposition'] = 'inline'
        return response
