"""US39-43: session-authorized use cases with transactional category changes."""
from datetime import datetime, timezone
from dataclasses import replace
from uuid import uuid4
from backend.controllers import Controller, effective_access
from backend.category_entity import IDPCategory
from backend.category_repository import CategoryRepository
from backend.models import AppError


class ManagerController(Controller):
    def require(self, permission):
        _, profile = effective_access(self.repository, self.actor_id)
        if profile.role != 'manager' or permission not in profile.permissions:
            raise AppError('FORBIDDEN', 'Platform Manager permission is required.')


class ViewIDPCategoryController(ManagerController):
    def execute(self, category_id):
        self.require('categories:manage')
        category = CategoryRepository(self.repository).find(category_id)
        if category is None:
            raise AppError('NOT_FOUND', 'Category was not found or has been deleted.')
        return category.to_dict()


class SearchIDPCategoryController(ManagerController):
    def execute(self, query=''):
        self.require('categories:manage')
        if not isinstance(query, str) or len(query) > 254:
            raise AppError('VALIDATION', 'Search supports at most 254 characters.')
        return CategoryRepository(self.repository).search(query)


class CreateIDPCategoryController(ManagerController):
    def execute(self, data):
        name, description = IDPCategory.validate(data)
        with self.repository.transaction():
            self.require('categories:manage')
            store = CategoryRepository(self.repository)
            if store.duplicate(name):
                raise AppError('DUPLICATE', 'A category with this name already exists (including deleted categories).', {'name': 'Choose another name.'})
            now = datetime.now(timezone.utc).isoformat()
            category = IDPCategory('CAT-' + str(uuid4()), name, description, 'Active', now, now, None)
            store.save(category, new=True)
        return category.to_dict()


class UpdateIDPCategoryController(ManagerController):
    def execute(self, category_id, data):
        name, description = IDPCategory.validate(data)
        with self.repository.transaction():
            current = IDPCategory(**ViewIDPCategoryController(self.repository, self.actor_id).execute(category_id))
            store = CategoryRepository(self.repository)
            if store.duplicate(name, category_id):
                raise AppError('DUPLICATE', 'A category with this name already exists.', {'name': 'Choose another name.'})
            category = replace(current, name=name, description=description, updatedAt=datetime.now(timezone.utc).isoformat())
            store.save(category)
        return category.to_dict()


class DeleteIDPCategoryController(ManagerController):
    def execute(self, category_id):
        with self.repository.transaction():
            current = IDPCategory(**ViewIDPCategoryController(self.repository, self.actor_id).execute(category_id))
            now = datetime.now(timezone.utc).isoformat()
            CategoryRepository(self.repository).save(replace(current, status='Suspended', deletedAt=now, updatedAt=now))
        return {'deleted': True, 'categoryId': category_id}


# BCE Aliases matching CSIT314 diagram notations
CreateIDPCC = CreateIDPCategoryController
ViewIDPCC = ViewIDPCategoryController
UpdateIDPCC = UpdateIDPCategoryController
DeleteIDPCC = DeleteIDPCategoryController
SearchIDPCC = SearchIDPCategoryController
