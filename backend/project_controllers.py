"""Ten use cases, with shared access and transaction logic for Current and Past."""
from datetime import datetime, timezone
from uuid import uuid4

from backend.controllers import Controller, effective_access
from backend.models import AppError
from backend.project_entity import InteriorDesignProject
from backend.project_repository import ProjectRepository
from backend.project_validation import validate_project, validate_image
from backend.customer_controllers import SearchIDPController, ViewIDPController


class ProjectController(Controller):
    status = None

    def owner(self):
        account, profile = effective_access(self.repository, self.actor_id)
        if profile.role != 'designer' or 'projects:manage' not in profile.permissions:
            raise AppError('FORBIDDEN', 'Interior Designer project management permission is required.')
        return account.account_id

    def get(self, project_id):
        project = ProjectRepository(self.repository).find(project_id, self.owner(), self.status)
        if project is None:
            raise AppError('NOT_FOUND', 'Project was not found.')
        return project

    def list(self, query=''):
        owner = self.owner()
        if not isinstance(query, str) or len(query) > 254:
            raise AppError('VALIDATION', 'Search must contain at most 254 characters.')
        return ProjectRepository(self.repository).search(status=self.status, owner=owner, query=query)

    def save(self, data, project_id=None):
        self.owner()
        values, image_inputs = validate_project(data)
        # Expensive decoding happens before the write transaction; ownership/access are rechecked inside it.
        uploads = [validate_image(image) if isinstance(image, dict) and 'data' in image else None for image in image_inputs]
        store = ProjectRepository(self.repository)
        with self.repository.transaction():
            owner = self.owner()
            previous = self.get(project_id) if project_id else None
            category = store.category(values['categoryId'])
            if not category or (category['status'] != 'Active' and (not previous or previous['categoryId'] != values['categoryId'])):
                raise AppError('VALIDATION', 'Select an available category.', {'categoryId': 'Category is missing or inactive.'})
            images, seen = [], set()
            for value, upload in zip(image_inputs, uploads):
                if upload is not None:
                    images.append(dict(imageId='IMG-' + str(uuid4()), **upload))
                else:
                    if not isinstance(value, dict) or set(value) != {'imageId'} or not isinstance(value['imageId'], str):
                        raise AppError('VALIDATION', 'Invalid image reference.', {'images': 'Choose an image or retain one from this project.'})
                    image = store.image_content(value['imageId'])
                    if not previous or not image or image['project_id'] != project_id or value['imageId'] in seen:
                        raise AppError('VALIDATION', 'Invalid image reference.', {'images': 'Image does not belong to this project.'})
                    seen.add(value['imageId'])
                    images.append(dict(imageId=image['image_id'], content=image['content'], mimeType=image['mime_type']))
            now = datetime.now(timezone.utc).isoformat()
            if previous:
                store.update({**previous, **values, 'updatedAt': now}, owner)
            else:
                project_id = 'IDP-' + str(uuid4())
                store.create(InteriorDesignProject(project_id, owner, store.company_id(owner), values['title'],
                    values['description'], values['categoryId'], values['style'], self.status, now, now))
            store.replace_images(project_id, images)
        return store.find(project_id, owner, self.status)

    def remove(self, project_id):
        with self.repository.transaction():
            self.get(project_id)
            ProjectRepository(self.repository).delete(project_id, self.owner())
        return {'deleted': True}


class CreateCurrentIDPController(ProjectController):
    status = 'Current'
    def execute(self, data): return self.save(data)

class ViewCurrentIDPController(ProjectController):
    status = 'Current'
    def execute(self, project_id): return self.get(project_id)

class UpdateCurrentIDPController(ProjectController):
    status = 'Current'
    def execute(self, project_id, data): return self.save(data, project_id)

class DeleteCurrentIDPController(ProjectController):
    status = 'Current'
    def execute(self, project_id): return self.remove(project_id)

class SearchCurrentIDPController(ProjectController):
    status = 'Current'
    def execute(self, query=''): return self.list(query)

class CreatePastIDPController(ProjectController):
    status = 'Past'
    def execute(self, data): return self.save(data)

class ViewPastIDPController(ProjectController):
    status = 'Past'
    def execute(self, project_id): return self.get(project_id)

class UpdatePastIDPController(ProjectController):
    status = 'Past'
    def execute(self, project_id, data): return self.save(data, project_id)

class DeletePastIDPController(ProjectController):
    status = 'Past'
    def execute(self, project_id): return self.remove(project_id)

class SearchPastIDPController(ProjectController):
    status = 'Past'
    def execute(self, query=''): return self.list(query)


class CustomerProjectController(Controller):
    """Read adapter for Member 4; no publication or analytics workflow is introduced."""
    def search(self, query='', category_id='', style=''):
        return SearchIDPController(self.repository, self.actor_id).execute(query, category_id, style)

    def view(self, project_id):
        return ViewIDPController(self.repository, self.actor_id).execute(project_id)

    def image(self, image_id):
        store = ProjectRepository(self.repository)
        image = store.image_content(image_id)
        if image is None:
            raise AppError('NOT_FOUND', 'Image was not found.')
        # A designer can preview owned images even if public visibility changes.
        owned = None
        if self.actor_id:
            account, profile = effective_access(self.repository, self.actor_id)
            if profile.role == 'designer' and 'projects:manage' in profile.permissions:
                owned = store.find(image['project_id'], owner=account.account_id)
        if owned is None:
            self.view(image['project_id'])
        return image
