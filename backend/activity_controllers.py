"""US37/38 and the single authorized customer detail recorder."""
import re
from datetime import datetime, timezone
from backend.controllers import Controller, effective_access
from backend.models import AppError
from backend.validation import check_object
from backend.activity_entity import ProjectView
from backend.activity_repository import ActivityRepository


class ViewIDPViewsController(Controller):
    def execute(self, project_id=None):
        account, profile = effective_access(self.repository, self.actor_id)
        if profile.role != 'designer' or 'projects:manage' not in profile.permissions:
            raise AppError('FORBIDDEN', 'Designer project access is required.')
        rows = ActivityRepository(self.repository).counts(account.account_id, project_id)
        if project_id is not None:
            if not rows:
                raise AppError('NOT_FOUND', 'Project was not found.')
            return rows[0]
        return rows


class ViewIDPShortlistsController(ViewIDPViewsController):
    """Returns both counts from the same aggregate snapshot, without customer identities."""


class RecordIDPViewController(Controller):
    def execute(self, project_id, data):
        # Import locally to keep shared project/customer controllers acyclic.
        from backend.customer_controllers import ViewIDPController
        check_object(data, {'eventId'})
        event_id = data.get('eventId')
        if not isinstance(event_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{16,100}', event_id):
            raise AppError('VALIDATION', 'A stable eventId of 16-100 URL-safe characters is required.')
        with self.repository.transaction():
            detail = ViewIDPController(self.repository, self.actor_id)
            detail.require_customer()
            project = detail.execute(project_id)
            created = ActivityRepository(self.repository).record(ProjectView(
                project_id, event_id, datetime.now(timezone.utc).isoformat()))
        return {'project': project, 'recorded': created}


# BCE Aliases matching CSIT314 diagram notations
ViewPVCountsC = ViewIDPViewsController
ViewFAVCountsC = ViewIDPShortlistsController
