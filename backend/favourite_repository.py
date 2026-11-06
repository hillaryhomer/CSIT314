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

    def find(self, customer_id, project_id):
        row = self.connection.execute('SELECT * FROM favourites WHERE customer_account_id=? AND project_id=?', (customer_id, project_id)).fetchone()
        return Favourite(**dict(row)) if row else None


class ProjectActivityAdapter:
    """Member 5 contract: derive shortlist totals from unique favourites; no second counter."""
    view_tracking_available = True

    def __init__(self, repository):
        self.connection = repository.connection

    def shortlist_count(self, project_id):
        return self.connection.execute('SELECT COUNT(*) FROM favourites WHERE project_id=?', (project_id,)).fetchone()[0]
