"""Favourite relationships share the same connection/transaction as projects and sessions."""
from backend.favourite_entity import Favourite


class FavouriteRepository:
    def __init__(self, repository):
        self.connection = repository.connection

    def list_for_customer(self, customer_id):
        return [Favourite(**dict(row)) for row in self.connection.execute(
            'SELECT * FROM favourites WHERE customer_account_id=? ORDER BY created_at DESC,project_id', (customer_id,))]

    def add(self, favourite):
        cursor = self.connection.execute(
            '''INSERT INTO favourites(customer_account_id,project_id,created_at) VALUES (?,?,?)
               ON CONFLICT(customer_account_id,project_id) DO NOTHING''',
            (favourite.customer_account_id, favourite.project_id, favourite.created_at))
        return cursor.rowcount == 1

    def exists(self, customer_id, project_id):
        """US32 in CSIT314_Consistency_Fixes: step 5 exists(customerId, projectId)."""
        row = self.connection.execute(
            'SELECT 1 FROM favourites WHERE customer_account_id=? AND project_id=?',
            (customer_id, project_id)
        ).fetchone()
        return row is not None

    def find(self, customer_id, project_id):
        row = self.connection.execute('SELECT * FROM favourites WHERE customer_account_id=? AND project_id=?', (customer_id, project_id)).fetchone()
        return Favourite(**dict(row)) if row else None

    def count_by_project(self, project_ids):
        """Count favourites per project matching Class Model 2 countByProject(projectIds)."""
        if not project_ids:
            return {}
        placeholders = ','.join('?' for _ in project_ids)
        rows = self.connection.execute(
            f'SELECT project_id, COUNT(*) FROM favourites WHERE project_id IN ({placeholders}) GROUP BY project_id',
            tuple(project_ids)
        ).fetchall()
        return {row[0]: row[1] for row in rows}

    countByProject = count_by_project


class ProjectActivityAdapter:
    """Derive shortlist totals from unique favourites; no redundant counter."""
    view_tracking_available = True

    def __init__(self, repository):
        self.connection = repository.connection

    def shortlist_count(self, project_id):
        return self.connection.execute('SELECT COUNT(*) FROM favourites WHERE project_id=?', (project_id,)).fetchone()[0]
