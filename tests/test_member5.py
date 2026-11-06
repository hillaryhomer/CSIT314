"""Member 5 integration with real sessions, concurrent requests and isolated SQLite."""
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
import sqlite3
import unittest
import tempfile
from pathlib import Path
import test_member4 as fixtures
from backend.app import create_app
from backend.activity_repository import ActivityRepository


class Member5Tests(unittest.TestCase):
    # Reuse the actual account/session fixture, without rerunning inherited tests.
    setUpClass = classmethod(fixtures.Member4Tests.setUpClass.__func__)
    setUp = fixtures.Member4Tests.setUp
    tearDown = fixtures.Member4Tests.tearDown
    login = fixtures.Member4Tests.login
    project = fixtures.Member4Tests.project
    save = fixtures.Member4Tests.save
    def counts(self, project):
        response = self.designer.get('/api/designer/analytics/' + project['projectId'])
        self.assertEqual(response.status_code, 200)
        return response.get_json()

    def test_activity_lifecycle(self):
        project = self.project()
        past = self.project('past')
        url = '/api/catalog/projects/' + project['projectId']
        customer, csrf = self.login('customer.one')
        self.assertEqual(self.counts(project)['views'], 0)
        self.assertEqual(self.counts(project)['shortlists'], 0)
        customer.get('/api/catalog/projects')
        customer.get(url)
        self.assertEqual(self.counts(project)['views'], 0)
        event = {'eventId': 'stable-event-00000001'}
        self.assertTrue(customer.post(url + '/views', json=event, headers=csrf).get_json()['recorded'])
        self.assertFalse(customer.post(url + '/views', json=event, headers=csrf).get_json()['recorded'])
        self.assertEqual(customer.post(url + '/views', json={'eventId': 'stable-event-00000002'}, headers=csrf).status_code, 200)
        self.assertEqual(self.counts(project)['views'], 2)
        for _ in range(2): self.assertIn(self.save(customer, csrf, project).status_code, (200, 201))
        other, token = self.login('customer.two')
        self.save(other, token, project)
        self.assertEqual(self.counts(project)['shortlists'], 2)
        self.assertEqual(self.counts(past)['views'], 0)
        self.assertEqual(len(self.designer.get('/api/designer/analytics').get_json()), 2)
        self.app = create_app(self.filename)
        self.designer, self.designer_csrf = self.login('designer.one')
        self.assertEqual(self.counts(project)['views'], 2)
        self.assertEqual(self.counts(project)['shortlists'], 2)
        self.assertEqual(self.designer.delete('/api/designer/projects/current/' + project['projectId'], json={}, headers=self.designer_csrf).status_code, 200)
        self.assertEqual(self.connection.execute('SELECT COUNT(*) FROM project_views').fetchone()[0], 0)
        self.assertEqual(self.designer.get('/api/designer/analytics/' + project['projectId']).status_code, 404)

    def test_denials_and_rollback(self):
        project = self.project()
        url = '/api/catalog/projects/' + project['projectId'] + '/views'
        event = {'eventId': 'stable-event-00000001'}
        customer, csrf = self.login('customer.one')
        self.assertEqual(self.app.test_client().post(url, json=event).status_code, 401)
        self.assertEqual(self.designer.post(url, json=event, headers=self.designer_csrf).status_code, 403)
        self.assertEqual(customer.get('/api/designer/analytics').status_code, 403)
        self.assertEqual(customer.post('/api/catalog/projects/missing/views', json=event, headers=csrf).status_code, 404)
        self.assertEqual(customer.post(url, json={**event, 'views': 99}, headers=csrf).status_code, 400)
        self.assertEqual(customer.post(url, json=event).status_code, 403)
        with patch.object(ActivityRepository, 'record', side_effect=sqlite3.OperationalError('failed')):
            self.assertEqual(customer.post(url, json=event, headers=csrf).status_code, 500)
        self.assertEqual(self.counts(project)['views'], 0)
        self.connection.execute("UPDATE user_accounts SET status='Suspended' WHERE account_id='designer'")
        self.assertEqual(customer.post(url, json=event, headers=csrf).status_code, 404)
        self.assertEqual(self.connection.execute('SELECT COUNT(*) FROM project_views').fetchone()[0], 0)

    def test_ownership_and_concurrent_events(self):
        from backend.models import UserAccount
        self.repository.create_account(UserAccount('designer-b', 'designer.two', 'designer2@example.test', self.password_hash, 'designer'))
        other, _ = self.login('designer.two')
        project = self.project()
        self.assertEqual(other.get('/api/designer/analytics').get_json(), [])
        self.assertEqual(other.get('/api/designer/analytics/' + project['projectId']).status_code, 404)
        customer, csrf = self.login('customer.one')
        cookie = customer.get_cookie('csit314_session').value
        def record(index):
            client = self.app.test_client()
            client.set_cookie('csit314_session', cookie)
            return client.post('/api/catalog/projects/' + project['projectId'] + '/views', json={'eventId': f'concurrent-event-{index % 5:08d}'}, headers=csrf).status_code
        with ThreadPoolExecutor(max_workers=5) as pool:
            self.assertEqual(list(pool.map(record, range(15))), [200] * 15)
        self.assertEqual(self.counts(project)['views'], 5)


class GeneratorTests(unittest.TestCase):
    def test_seed_counts_foreign_keys_and_guards(self):
        from backend.seed_member5 import generate
        from backend.database import connect_database
        with tempfile.TemporaryDirectory() as directory:
            filename = str(Path(directory) / 'demo.sqlite')
            with self.assertRaises(ValueError): generate(filename, 'production')
            project = generate(filename, 'test', 7)
            connection = connect_database(filename)
            try:
                self.assertEqual(connection.execute('PRAGMA foreign_key_check').fetchall(), [])
                self.assertEqual(connection.execute('SELECT COUNT(*) FROM project_views WHERE project_id=?', (project,)).fetchone()[0], 3)
                self.assertEqual(connection.execute('SELECT COUNT(*) FROM favourites WHERE project_id=?', (project,)).fetchone()[0], 2)
                self.assertEqual(connection.execute('SELECT COUNT(*) FROM interior_design_projects').fetchone()[0], 4)
                with self.assertRaises(ValueError): generate(filename, 'test', 7)
                self.assertEqual(connection.execute('SELECT COUNT(*) FROM project_views').fetchone()[0], 3)
            finally: connection.close()
