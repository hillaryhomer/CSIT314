"""Analytics reads and atomic customer detail access/recording HTTP boundary."""
from flask import g, jsonify, request
from backend.activity_controllers import ViewIDPViewsController, RecordIDPViewController
from backend.models import AppError


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
