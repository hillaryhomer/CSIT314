"""Known calendar counts, restricted to the disposable browser harness database."""
import os
from pathlib import Path
from backend.database import Repository, connect_database
from backend.project_entity import InteriorDesignProject
from backend.project_repository import ProjectRepository
from backend.activity_entity import ProjectView
from backend.activity_repository import ActivityRepository
from backend.customer_controllers import AddFavouriteController

filename = Path(os.environ['DATABASE_PATH']).resolve()
if filename.parent != Path('.test-data').resolve() or not filename.name.startswith('python-browser-'):
    raise RuntimeError('Report fixtures require a dedicated browser test database.')
connection = connect_database(str(filename))
try:
    repository = Repository(connection)
    for suffix, timestamp in [('A', '2024-02-28T16:00:00+00:00'), ('B', '2024-02-29T15:59:59.999999+00:00'), ('C', '2024-02-29T16:00:00+00:00')]:
        with repository.transaction():
            project_id = 'REPORT-' + suffix
            ProjectRepository(repository).create(InteriorDesignProject(project_id, 'browser-designer', None,
                'Report fixture ' + suffix, 'Synthetic known report counts', 'CAT001', 'Modern',
                'Past' if suffix == 'B' else 'Current', timestamp, timestamp))
            ActivityRepository(repository).record(ProjectView(project_id, 'report-fixture-event-' + suffix, timestamp))
    AddFavouriteController(repository, 'browser-customer').execute({'projectId': 'REPORT-A'})
finally:
    connection.close()
