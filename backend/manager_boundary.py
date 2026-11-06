"""Platform Manager HTTP Boundaries; JSON/CSRF/session middleware is shared."""
from flask import g, jsonify, request
from backend.models import AppError
from backend.category_controllers import (CreateIDPCategoryController, ViewIDPCategoryController,
    UpdateIDPCategoryController, DeleteIDPCategoryController, SearchIDPCategoryController)
from backend.report_controllers import (GenerateDailyReportController, GenerateWeeklyReportController,
    GenerateMonthlyReportController)


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
        from backend.validation import check_object
        check_object(request.get_json(), set())
        return jsonify(DeleteIDPCategoryController(repository(), g.actor_id).execute(category_id))

    @app.get('/api/manager/reports/<kind>')
    def report(kind):
        query({'period'})
        controls = {'daily': GenerateDailyReportController, 'weekly': GenerateWeeklyReportController,
                    'monthly': GenerateMonthlyReportController}
        if kind not in controls:
            raise AppError('NOT_FOUND', 'Report type was not found.')
        return jsonify(controls[kind](repository(), g.actor_id).execute(request.args.get('period')))
