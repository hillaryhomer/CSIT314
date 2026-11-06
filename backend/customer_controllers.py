"""US30-34: public discovery and private customer favourites, using shared projects."""
from datetime import datetime, timezone

from backend.controllers import Controller, effective_access
from backend.favourite_entity import Favourite
from backend.favourite_repository import FavouriteRepository
from backend.models import AppError
from backend.project_repository import ProjectRepository
from backend.validation import check_object, clean


def search_values(query='', category_id='', style=''):
    values = (query, category_id, style)
    if any(not isinstance(value, str) or len(value) > limit for value, limit in zip(values, (254, 100, 100))):
        raise AppError('VALIDATION', 'Search fields exceed the supported length.')
    return tuple(clean(value) for value in values)


class CustomerController(Controller):
    def require_customer(self):
        account, profile = effective_access(self.repository, self.actor_id)
        if profile.role != 'customer' or 'projects:discover' not in profile.permissions:
            raise AppError('FORBIDDEN', 'Customer discovery permission is required for personal favourites.')
        return account.account_id

    def optional_customer(self):
        if not self.actor_id:
            return None
        try:
            return self.require_customer()
        except AppError as error:
            if error.code in ('UNAUTHENTICATED', 'FORBIDDEN'):
                return None
            raise

    def public_records(self, projects, customer_id=None):
        saved = {f.project_id: f.created_at for f in FavouriteRepository(self.repository).list_for_customer(customer_id)} if customer_id else {}
        return [{**ProjectRepository.public_projection(p), 'saved': p['projectId'] in saved,
                 **({'savedAt': saved[p['projectId']]} if p['projectId'] in saved else {})} for p in projects]


class SearchIDPController(CustomerController):
    def execute(self, query='', category_id='', style=''):
        query, category_id, style = search_values(query, category_id, style)
        projects = ProjectRepository(self.repository).search(query=query, category_id=category_id, style=style, public=True)
        return self.public_records(projects, self.optional_customer())


class ViewIDPController(CustomerController):
    def execute(self, project_id):
        project = ProjectRepository(self.repository).find(project_id, public=True)
        if project is None:
            raise AppError('NOT_FOUND', 'Project was not found or is no longer available.')
        # GET stays side-effect free; Member 5 atomically reads/records authorized detail POSTs.
        return self.public_records([project], self.optional_customer())[0]


class AddFavouriteController(CustomerController):
    def execute(self, data):
        check_object(data, {'projectId'})
        project_id = clean(data.get('projectId'))
        if not project_id or len(project_id) > 100:
            raise AppError('VALIDATION', 'Choose a valid project.', {'projectId': 'A project ID is required.'})
        with self.repository.transaction():
            customer_id = self.require_customer()
            project = ProjectRepository(self.repository).find(project_id, public=True)
            if project is None:
                raise AppError('NOT_FOUND', 'Project was not found or is no longer available.')
            store = FavouriteRepository(self.repository)
            created = store.add(Favourite(customer_id, project_id, datetime.now(timezone.utc).isoformat()))
            favourite = store.find(customer_id, project_id)
            result = {**ProjectRepository.public_projection(project), 'saved': True, 'savedAt': favourite.created_at}
        return {'project': result, 'saved': True, 'created': created}


class ViewFavouriteListController(CustomerController):
    def execute(self):
        customer_id = self.require_customer()
        projects = ProjectRepository(self.repository).search(public=True, favourite_customer=customer_id)
        return self.public_records(projects, customer_id)


class SearchFavouriteListController(CustomerController):
    def execute(self, query=''):
        customer_id = self.require_customer()
        query, _, _ = search_values(query)
        projects = ProjectRepository(self.repository).search(query=query, public=True, favourite_customer=customer_id)
        return self.public_records(projects, customer_id)
