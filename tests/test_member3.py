"""Member 3 integration tests: real shared sessions and disposable SQLite databases."""
import base64
from io import BytesIO
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

from backend.app import create_app
from backend.database import Repository, connect_database, initialize_database
from backend.models import UserAccount, UserProfile
from backend.project_repository import ProjectRepository
from backend.validation import hash_password

PASSWORD = 'member three test password'
PROJECT = {'title': 'Garden Studio', 'description': 'Calm residential interiors', 'style': 'Japandi', 'categoryId': 'CAT001', 'images': []}


def png_upload(color='red'):
    output = BytesIO()
    Image.new('RGB', (4, 4), color).save(output, format='PNG')
    return {'data': base64.b64encode(output.getvalue()).decode(), 'mimeType': 'image/png'}


class Member3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.password_hash = hash_password(PASSWORD)

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='csit314-member3-')
        self.filename = str(Path(self.directory.name) / 'projects.sqlite')
        initialize_database(self.filename)
        self.connection = connect_database(self.filename)
        self.repository = Repository(self.connection)
        for role in ('admin', 'designer', 'customer', 'manager'):
            permissions = ['accounts:read', 'accounts:write'] if role == 'admin' else ['projects:manage'] if role == 'designer' else ['projects:discover']
            self.repository.create_profile(UserProfile(role, role, role, permissions))
            self.repository.create_account(UserAccount(role, role + '.one', role + '@example.test', self.password_hash, role))
        self.repository.create_account(UserAccount('designer-b', 'designer.two', 'designer-b@example.test', self.password_hash, 'designer'))
        self.app = create_app(self.filename)
        self.app.logger.disabled = True
        self.client, self.csrf = self.login('designer.one')

    def tearDown(self):
        self.connection.close()
        self.directory.cleanup()

    def login(self, username):
        client = self.app.test_client()
        response = client.post('/api/auth/login', json={'identifier': username, 'password': PASSWORD})
        self.assertEqual(response.status_code, 200)
        return client, {'X-CSRF-Token': response.get_json()['csrfToken']}

    def create(self, kind='current', **changes):
        response = self.client.post('/api/designer/projects/' + kind, json={**PROJECT, **changes}, headers=self.csrf)
        self.assertEqual(response.status_code, 201, response.get_json())
        return response.get_json()

    def test_all_ten_stories_crud_search_separation_and_customer_source(self):
        for kind, status in [('current', 'Current'), ('past', 'Past')]:
            with self.subTest(status=status):
                project = self.create(kind, title=status + ' Garden Studio', images=[png_upload()])
                endpoint = f'/api/designer/projects/{kind}/{project["projectId"]}'
                self.assertEqual(project['status'], status)
                self.assertEqual(project['ownerAccountId'], 'designer')
                self.assertEqual(self.client.get(endpoint).get_json(), project)
                self.assertEqual(len(self.client.get('/api/designer/projects/' + kind + '?q=CALM').get_json()), 1)
                self.assertEqual(len(self.client.get('/api/designer/projects/' + kind + '?q=').get_json()), 1)
                self.assertEqual(self.client.get('/api/designer/projects/' + kind + '?q=missing').get_json(), [])
                other_kind = 'past' if kind == 'current' else 'current'
                self.assertEqual(self.client.get('/api/designer/projects/' + other_kind).get_json(), [])
                self.assertEqual(self.client.get(f'/api/designer/projects/{other_kind}/{project["projectId"]}').status_code, 404)
                updated = self.client.put(endpoint, json={**PROJECT, 'title': 'Renamed ' + status, 'images': [{'imageId': project['images'][0]['imageId']}]}, headers=self.csrf)
                self.assertEqual(updated.status_code, 200)
                record = updated.get_json()
                self.assertEqual(record['projectId'], project['projectId'])
                self.assertEqual(record['ownerAccountId'], project['ownerAccountId'])
                self.assertEqual(record['createdAt'], project['createdAt'])
                self.assertEqual(record['status'], status)
                public = self.app.test_client()
                public_record = public.get('/api/catalog/projects/' + project['projectId']).get_json()
                for key in ('projectId', 'title', 'description', 'categoryId', 'style', 'status', 'images', 'createdAt', 'updatedAt'):
                    self.assertEqual(public_record[key], record[key])
                self.assertNotIn('ownerAccountId', public_record)
                self.assertNotIn('companyId', public_record)
                self.assertEqual(public.get('/api/catalog/projects?q=renamed').get_json()[0]['projectId'], record['projectId'])
                image = public.get(record['images'][0]['url'])
                self.assertEqual(image.status_code, 200)
                self.assertEqual(image.mimetype, 'image/png')
                self.assertEqual(image.headers['X-Content-Type-Options'], 'nosniff')
                self.assertEqual(self.client.delete(endpoint, json={}, headers=self.csrf).status_code, 200)
                self.assertEqual(self.client.get(endpoint).status_code, 404)
                self.assertEqual(public.get(record['images'][0]['url']).status_code, 404)
                self.assertEqual(public.get('/api/catalog/projects').get_json(), [])

    def test_owner_role_permission_and_session_enforcement(self):
        project = self.create()
        endpoint = '/api/designer/projects/current/' + project['projectId']
        other, csrf = self.login('designer.two')
        self.assertEqual(other.get('/api/designer/projects/current').get_json(), [])
        for response in [other.get(endpoint), other.put(endpoint, json=PROJECT, headers=csrf), other.delete(endpoint, json={}, headers=csrf)]:
            self.assertEqual(response.status_code, 404)
        for role in ('admin', 'customer', 'manager'):
            client, csrf = self.login(role + '.one')
            for kind in ('current', 'past'):
                base = '/api/designer/projects/' + kind
                for response in [client.get(base), client.get(base + '/' + project['projectId']), client.post(base, json=PROJECT, headers=csrf), client.put(base + '/' + project['projectId'], json=PROJECT, headers=csrf), client.delete(base + '/' + project['projectId'], json={}, headers=csrf)]:
                    self.assertEqual(response.status_code, 403)
        anonymous = self.app.test_client()
        for response in [anonymous.get(endpoint), anonymous.get('/api/designer/projects/current'), anonymous.post('/api/designer/projects/past', json=PROJECT)]:
            self.assertEqual(response.status_code, 401)
        self.assertEqual(self.client.post('/api/designer/projects/current', json=PROJECT).status_code, 403)
        profile = self.repository.find_profile('designer'); profile.permissions = ['projects:discover']; self.repository.update_profile(profile)
        self.assertEqual(self.client.get(endpoint).status_code, 403)

    def test_validation_immutable_fields_empty_search_and_missing_projects(self):
        project = self.create()
        endpoint = '/api/designer/projects/current/' + project['projectId']
        invalid = [{'title': '  '}, {'description': 8}, {'style': 'x' * 101}, {'categoryId': 'unknown'}, {'images': 'fake'}, {'images': [png_upload()] * 6}]
        invalid += [{field: 'forged'} for field in ('projectId','ownerAccountId','companyId','status','createdAt','updatedAt')]
        for change in invalid:
            for method, path in [('post', '/api/designer/projects/current'), ('put', endpoint)]:
                response = getattr(self.client, method)(path, json={**PROJECT, **change}, headers=self.csrf)
                self.assertEqual(response.status_code, 400, change)
        self.assertEqual(self.client.get('/api/designer/projects/current?q=%25').get_json(), [])
        self.assertEqual(self.client.get('/api/designer/projects/other').status_code, 404)
        for response in [self.client.get('/api/designer/projects/past/missing'), self.client.put('/api/designer/projects/past/missing', json=PROJECT, headers=self.csrf), self.client.delete('/api/designer/projects/past/missing', json={}, headers=self.csrf)]:
            self.assertEqual(response.status_code, 404)

    def test_images_verified_replaced_removed_and_cannot_be_borrowed(self):
        first = self.create(images=[png_upload()])
        second = self.create('past', images=[png_upload('blue')])
        endpoint = '/api/designer/projects/current/' + first['projectId']
        invalid = [dict(data=base64.b64encode(b'<svg/>').decode(), mimeType='image/png'), {**png_upload(), 'mimeType': 'image/jpeg'}, {'data': 'not base64', 'mimeType': 'image/png'}, {'data': 'A' * (3 * 1024 * 1024), 'mimeType': 'image/png'}]
        for image in invalid:
            self.assertEqual(self.client.put(endpoint, json={**PROJECT, 'images': [image]}, headers=self.csrf).status_code, 400)
        for images in [[{'imageId': second['images'][0]['imageId']}], [{'imageId': first['images'][0]['imageId']}] * 2]:
            self.assertEqual(self.client.put(endpoint, json={**PROJECT, 'images': images}, headers=self.csrf).status_code, 400)
        response = self.client.put(endpoint, json={**PROJECT, 'images': [png_upload('green')]}, headers=self.csrf)
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(response.get_json()['images'][0]['imageId'], first['images'][0]['imageId'])
        self.assertEqual(self.client.get(first['images'][0]['url']).status_code, 404)
        self.assertEqual(self.client.get(second['images'][0]['url']).status_code, 200)
        self.assertEqual(self.client.put(endpoint, json=PROJECT, headers=self.csrf).get_json()['images'], [])

    def test_restart_persistence_company_deletion_and_unrelated_records_preserved(self):
        company = self.client.post('/api/company', json={'name': 'Studio', 'address': 'Road', 'contact': 'hello@test.example'}, headers=self.csrf).get_json()
        project = self.create(images=[png_upload()]); other = self.create('past')
        self.assertEqual(project['companyId'], company['companyId'])
        restarted = create_app(self.filename).test_client()
        restarted.set_cookie('csit314_session', self.client.get_cookie('csit314_session').value)
        self.assertEqual(restarted.get('/api/designer/projects/current').get_json()[0], project)
        self.assertEqual(self.client.delete('/api/company/' + company['companyId'], json={}, headers=self.csrf).status_code, 200)
        self.assertIsNone(restarted.get('/api/designer/projects/current').get_json()[0]['companyId'])
        self.client.delete('/api/designer/projects/current/' + project['projectId'], json={}, headers=self.csrf)
        self.assertEqual(restarted.get('/api/designer/projects/past').get_json()[0]['projectId'], other['projectId'])
        self.assertIsNotNone(self.repository.find_account('designer'))

    def test_shared_categories_inactive_assignment_and_reference_restriction(self):
        public = self.app.test_client()
        self.assertEqual(public.get('/api/project-categories').get_json()[0]['categoryId'], 'CAT002')
        project = self.create()
        self.connection.execute("UPDATE project_categories SET status='Suspended' WHERE category_id='CAT001'")
        self.assertEqual(self.client.post('/api/designer/projects/current', json=PROJECT, headers=self.csrf).status_code, 400)
        endpoint = '/api/designer/projects/current/' + project['projectId']
        self.assertEqual(self.client.put(endpoint, json=PROJECT, headers=self.csrf).status_code, 200)
        with self.assertRaises(sqlite3.IntegrityError):
            self.connection.execute("DELETE FROM project_categories WHERE category_id='CAT001'")
        self.assertEqual(public.get('/api/catalog/projects?categoryId=CAT001').get_json()[0]['categoryStatus'], 'Suspended')

    def test_storage_failures_roll_back_project_images_and_delete(self):
        original = ProjectRepository.replace_images
        def fail_images(store, *args):
            original(store, *args)
            raise sqlite3.OperationalError('simulated failure')
        with patch.object(ProjectRepository, 'replace_images', fail_images):
            response = self.client.post('/api/designer/projects/current', json={**PROJECT, 'images': [png_upload()]}, headers=self.csrf)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_json()['error']['code'], 'PERSISTENCE')
        self.assertEqual(self.connection.execute('SELECT COUNT(*) FROM project_images').fetchone()[0], 0)
        self.assertEqual(self.client.get('/api/designer/projects/current').get_json(), [])
        project = self.create(images=[png_upload()]); endpoint = '/api/designer/projects/current/' + project['projectId']
        with patch.object(ProjectRepository, 'replace_images', fail_images):
            self.assertEqual(self.client.put(endpoint, json={**PROJECT, 'title': 'Not saved', 'images': []}, headers=self.csrf).status_code, 500)
        self.assertEqual(self.client.get(endpoint).get_json(), project)
        original_delete = ProjectRepository.delete
        def fail_delete(store, *args):
            original_delete(store, *args)
            raise sqlite3.OperationalError('simulated deletion failure')
        with patch.object(ProjectRepository, 'delete', fail_delete):
            self.assertEqual(self.client.delete(endpoint, json={}, headers=self.csrf).status_code, 500)
        self.assertEqual(self.client.get(endpoint).get_json(), project)

    def test_suspension_hides_public_projects_images_and_stops_management(self):
        project = self.create(images=[png_upload()])
        admin, csrf = self.login('admin.one')
        self.assertEqual(admin.post('/api/accounts/designer/suspend', json={}, headers=csrf).status_code, 200)
        public = self.app.test_client()
        self.assertEqual(public.get('/api/catalog/projects').get_json(), [])
        self.assertEqual(public.get('/api/catalog/projects/' + project['projectId']).status_code, 404)
        self.assertEqual(public.get(project['images'][0]['url']).status_code, 404)
        self.assertEqual(self.client.get('/api/designer/projects/current').status_code, 401)

    def test_member2_database_migration_preserves_identity_company_and_session(self):
        legacy = str(Path(self.directory.name) / 'legacy.sqlite')
        con = connect_database(legacy)
        con.executescript(Path('backend/schema.sql').read_text() + Path('backend/member2.sql').read_text())
        repo = Repository(con)
        repo.create_profile(UserProfile('p', 'Designer', 'designer', ['projects:manage']))
        repo.create_account(UserAccount('a', 'legacy.designer', 'legacy@example.test', self.password_hash, 'p'))
        con.execute("INSERT INTO companies VALUES ('co','a','Old Studio','','Old Road','old@example.test','')")
        before = {table: con.execute('SELECT * FROM ' + table).fetchall() for table in ('user_accounts','user_profiles','companies','auth_sessions')}
        con.close(); initialize_database(legacy); con = connect_database(legacy)
        try:
            for table, records in before.items(): self.assertEqual(con.execute('SELECT * FROM ' + table).fetchall(), records)
            self.assertEqual(con.execute('PRAGMA user_version').fetchone()[0], 6)
            self.assertEqual(con.execute('PRAGMA foreign_key_check').fetchall(), [])
        finally: con.close()
