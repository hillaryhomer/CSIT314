"""Activity persistence and aggregate read model shared with future reports."""
class ActivityRepository:
    def __init__(self, repository):
        self.connection = repository.connection

    def record(self, event):
        return self.connection.execute(
            'INSERT INTO project_views VALUES (?,?,?) ON CONFLICT(project_id,event_id) DO NOTHING',
            (event.project_id, event.event_id, event.occurred_at)).rowcount == 1

    def counts(self, owner, project_id=None):
        return [dict(row) for row in self.connection.execute('''
            SELECT p.project_id AS projectId,p.title,p.status,
              (SELECT COUNT(*) FROM project_views v WHERE v.project_id=p.project_id) AS views,
              (SELECT COUNT(*) FROM favourites f WHERE f.project_id=p.project_id) AS shortlists
            FROM interior_design_projects p WHERE p.owner_account_id=?
            AND (? IS NULL OR p.project_id=?) ORDER BY p.created_at DESC,p.project_id
        ''', (owner, project_id, project_id))]
