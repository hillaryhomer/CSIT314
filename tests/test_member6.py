"""Manager stories on isolated databases with shared account/session/project fixtures."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
from contextlib import closing
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4
import test_member4 as fixtures
from backend.app import create_app
from backend.database import initialize_database, connect_database
from backend.category_repository import CategoryRepository
from backend.report_repository import ReportRepository
from backend.report_service import ReportPeriod, ReportService
from backend.project_entity import InteriorDesignProject
from backend.project_repository import ProjectRepository
from backend.activity_entity import ProjectView
from backend.activity_repository import ActivityRepository
from backend.validation import hash_password


class Member6Tests(unittest.TestCase):
    setUpClass = classmethod(fixtures.Member4Tests.setUpClass.__func__)
    tearDown = fixtures.Member4Tests.tearDown
    login = fixtures.Member4Tests.login
    project = fixtures.Member4Tests.project

    def setUp(self):
        fixtures.Member4Tests.setUp(self)
        self.connection.execute("UPDATE user_profiles SET permissions_json='[\"reports:read\",\"categories:manage\"]' WHERE profile_id='manager'")
        self.manager, self.csrf = self.login('manager.one')

    def create(self, name='  Garden Spaces  ', description='Green interiors'):
        return self.manager.post('/api/manager/categories', json={'name': name, 'description': description}, headers=self.csrf)

    def test_category_crud_search_persistence_and_shared_projects(self):
        response = self.create()
        self.assertEqual(response.status_code, 201)
        category = response.get_json()
        category_id = category['categoryId']
        self.assertEqual(category['name'], 'Garden Spaces')
        self.assertIsNotNone(category['createdAt'])
        url = '/api/manager/categories/' + category_id
        self.assertEqual(self.manager.get(url).get_json(), category)
        self.assertEqual(len(self.manager.get('/api/manager/categories?q=  GREEN ').get_json()), 1)
        self.assertEqual(self.manager.get('/api/manager/categories?q=unmatched').get_json(), [])
        self.assertEqual(len(self.manager.get('/api/manager/categories?q= ').get_json()), 4)
        self.assertIn(category_id, [c['categoryId'] for c in self.app.test_client().get('/api/project-categories').get_json()])
        project = self.project(categoryId=category_id)
        other_project = self.project(categoryId='CAT002')
        updated = self.manager.put(url, json={'name': 'Courtyard', 'description': 'New description'}, headers=self.csrf)
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.get_json()['categoryId'], category_id)
        self.assertEqual(self.app.test_client().get('/api/catalog/projects/' + project['projectId']).get_json()['categoryName'], 'Courtyard')
        restarted = create_app(self.filename)
        cookie = self.manager.get_cookie('csit314_session').value
        client = restarted.test_client(); client.set_cookie('csit314_session', cookie)
        self.assertEqual(client.get(url).get_json()['name'], 'Courtyard')
        self.assertEqual(self.manager.delete(url, json={}, headers=self.csrf).status_code, 200)
        self.assertEqual(self.manager.get(url).status_code, 404)
        self.assertNotIn(category_id, [c['categoryId'] for c in self.manager.get('/api/manager/categories').get_json()])
        historical = self.app.test_client().get('/api/catalog/projects/' + project['projectId'])
        self.assertEqual(historical.status_code, 200)
        self.assertEqual(historical.get_json()['categoryStatus'], 'Suspended')
        self.assertEqual(self.designer.post('/api/designer/projects/current', json={**fixtures.PROJECT, 'categoryId': category_id}, headers=self.designer_csrf).status_code, 400)
        self.assertEqual(self.designer.put('/api/designer/projects/current/' + other_project['projectId'], json={**fixtures.PROJECT, 'categoryId': category_id}, headers=self.designer_csrf).status_code, 400)
        self.assertEqual(self.designer.put('/api/designer/projects/current/' + project['projectId'], json={**fixtures.PROJECT, 'categoryId': category_id, 'title': 'Historical edit'}, headers=self.designer_csrf).status_code, 200)
        self.assertEqual(self.create('courtyard').status_code, 409)
        self.assertEqual(self.connection.execute('PRAGMA foreign_key_check').fetchall(), [])

    def test_validation_duplicates_constraint_and_failures(self):
        for name in ('', '  ', 'x' * 101): self.assertEqual(self.create(name).status_code, 400)
        self.assertEqual(self.create('Good', 'x' * 2001).status_code, 400)
        category = self.create('Case Name').get_json()
        self.assertEqual(self.create('  CASE NAME ').status_code, 409)
        self.assertEqual(self.create('ＣＡＳＥ ＮＡＭＥ').status_code, 409)
        self.assertEqual(self.manager.put('/api/manager/categories/' + category['categoryId'], json={'name': 'residential'}, headers=self.csrf).status_code, 409)
        self.assertEqual(self.manager.put('/api/manager/categories/missing', json={'name': 'Other'}, headers=self.csrf).status_code, 404)
        with self.assertRaises(sqlite3.IntegrityError):
            self.connection.execute("INSERT INTO project_categories(category_id,name,name_key) VALUES ('bad','CASE NAME','case name')")
        with self.assertRaises(sqlite3.IntegrityError):
            self.connection.execute("INSERT INTO project_categories(category_id,name,name_key) VALUES ('bad','Valid','forged')")
        with patch.object(CategoryRepository, 'save', side_effect=sqlite3.OperationalError('disk failure')):
            self.assertEqual(self.create('Failed').status_code, 500)
        self.assertEqual(self.manager.get('/api/manager/categories?q=Failed').get_json(), [])
        with patch.object(CategoryRepository, 'search', side_effect=sqlite3.OperationalError('read failure')):
            self.assertEqual(self.manager.get('/api/manager/categories').status_code, 500)

    def test_access_permissions_and_concurrent_duplicate(self):
        customer, _ = self.login('customer.one')
        admin, _ = self.login('admin.one')
        for client in (self.app.test_client(), self.designer, customer, admin):
            self.assertIn(client.get('/api/manager/categories').status_code, (401, 403))
            self.assertIn(client.get('/api/manager/reports/daily?period=2024-02-29').status_code, (401, 403))
        self.assertEqual(self.manager.post('/api/manager/categories', json={'name': 'No csrf'}).status_code, 403)
        self.connection.execute("UPDATE user_profiles SET permissions_json='[\"reports:read\"]' WHERE profile_id='manager'")
        self.assertEqual(self.create().status_code, 403)
        self.connection.execute("UPDATE user_profiles SET permissions_json='[\"categories:manage\"]' WHERE profile_id='manager'")
        self.assertEqual(self.manager.get('/api/manager/reports/daily?period=2024-02-29').status_code, 403)
        cookie = self.manager.get_cookie('csit314_session').value
        def create(_):
            client = self.app.test_client(); client.set_cookie('csit314_session', cookie)
            return client.post('/api/manager/categories', json={'name': 'Concurrent'}, headers=self.csrf).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sorted(pool.map(create, range(2))), [201, 409])

    def at(self, timestamp):
        project_id = str(uuid4())
        with self.repository.transaction():
            ProjectRepository(self.repository).create(InteriorDesignProject(project_id, 'designer', None,
                'Fixture', 'Known count', 'CAT001', 'Modern', 'Current', timestamp, timestamp))
        return project_id

    def view_at(self, project_id, timestamp, event_id='known-event-00000001'):
        with self.repository.transaction():
            ActivityRepository(self.repository).record(ProjectView(project_id, event_id, timestamp))

    def test_reports_known_counts_boundaries_offsets_and_retention(self):
        a = self.at('2024-02-28T16:00:00+00:00')  # Feb 29 midnight locally, included
        self.at('2024-02-29T15:59:59.999999+00:00')  # last microsecond, included
        self.at('2024-02-29T16:00:00+00:00')  # next local day, excluded
        self.at('2024-02-28T15:59:59.999999+00:00')  # previous day, excluded
        self.view_at(a, '2024-02-29T00:00:00+08:00')
        self.view_at(a, '2024-02-29T00:00:00+08:00')  # duplicate contributes nothing
        self.view_at(a, '2024-02-29T23:59:59.999999+08:00', 'known-event-00000002')
        self.view_at(a, '2024-03-01T00:00:00+08:00', 'known-event-00000003')
        response = self.manager.get('/api/manager/reports/daily?period=2024-02-29')
        self.assertEqual(response.status_code, 200)
        report = response.get_json()
        self.assertEqual(report['metrics'], {'projectsCreated': 2, 'viewEvents': 2})
        self.assertFalse(report['coverage']['complete'])
        self.assertIn('unavailable', report['coverage']['note'])
        self.assertEqual(report['startUtc'], '2024-02-28T16:00:00.000000+00:00')
        self.assertEqual(self.manager.get('/api/manager/reports/daily?period=2020-01-01').get_json()['metrics'], {'projectsCreated': 0, 'viewEvents': 0})
        self.assertEqual(self.manager.get('/api/manager/reports/monthly?period=2024-02').get_json()['metrics'], {'projectsCreated': 3, 'viewEvents': 2})
        self.designer.delete('/api/designer/projects/current/' + a, json={}, headers=self.designer_csrf)
        self.assertEqual(self.manager.get('/api/manager/reports/daily?period=2024-02-29').get_json()['metrics'], report['metrics'])
        self.assertEqual(self.connection.execute('SELECT COUNT(*) FROM project_views WHERE project_id=?', (a,)).fetchone()[0], 0)
        self.assertEqual(self.connection.execute('PRAGMA foreign_key_check').fetchall(), [])
        with patch.object(ReportRepository, 'aggregate', side_effect=sqlite3.OperationalError('failed query')):
            failure = self.manager.get('/api/manager/reports/daily?period=2024-02-29')
            self.assertEqual(failure.status_code, 500)
            self.assertNotIn('metrics', failure.get_json())

    def test_calendar_ranges_current_partial_and_invalid_input(self):
        week = ReportPeriod.parse('weekly', '2025-01-01')
        self.assertEqual(week.start.date().isoformat(), '2024-12-30')
        self.assertEqual(week.end.date().isoformat(), '2025-01-06')
        for selected, days in [('2024-02', 29), ('2023-02', 28), ('2024-04', 30), ('2024-12', 31)]:
            period = ReportPeriod.parse('monthly', selected)
            self.assertEqual((period.end - period.start).days, days)
        now = datetime(2024, 2, 29, 1, tzinfo=timezone.utc)
        report = ReportService(ReportRepository(self.repository)).generate('daily', '2024-02-29', now)
        self.assertTrue(report['partial'])
        future = ReportService(ReportRepository(self.repository)).generate('daily', '2024-03-01', now)
        self.assertTrue(future['future'])
        for path in ('daily?period=2023-02-29', 'monthly?period=2024-13', 'daily?period=2024-2-01', 'weekly?period=invalid', 'daily', 'daily?period=1999-01-01'):
            self.assertEqual(self.manager.get('/api/manager/reports/' + path).status_code, 400)
        self.assertEqual(self.manager.get('/api/manager/reports/unknown?period=2024-01-01').status_code, 404)

    def test_live_events_report_changes_and_ledger_failure_rolls_back(self):
        from backend.report_service import REPORT_ZONE
        project = self.project()
        customer, csrf = self.login('customer.one')
        today = datetime.now(REPORT_ZONE).date().isoformat()
        report_url = '/api/manager/reports/daily?period=' + today
        before = self.manager.get(report_url).get_json()
        url = '/api/catalog/projects/' + project['projectId'] + '/views'
        body = {'eventId': 'live-report-event-00001'}
        self.assertEqual(customer.post(url, json=body, headers=csrf).status_code, 200)
        self.assertEqual(customer.post(url, json=body, headers=csrf).status_code, 200)
        after = self.manager.get(report_url).get_json()
        self.assertEqual(after['metrics']['viewEvents'], before['metrics']['viewEvents'] + 1)
        self.assertTrue(after['partial'])
        self.connection.execute("CREATE TRIGGER fail_report BEFORE INSERT ON report_events BEGIN SELECT RAISE(ABORT,'ledger unavailable'); END")
        self.assertEqual(customer.post(url, json={'eventId': 'live-report-event-00002'}, headers=csrf).status_code, 500)
        self.assertEqual(self.connection.execute('SELECT COUNT(*) FROM project_views').fetchone()[0], 1)
        self.assertEqual(self.manager.get(report_url).get_json()['metrics'], after['metrics'])


class Migration6Tests(unittest.TestCase):
    def test_backfill_preserves_real_timestamps_and_is_idempotent(self):
        from backend.database import Repository
        from backend.models import UserAccount, UserProfile
        with tempfile.TemporaryDirectory() as directory:
            filename = str(Path(directory) / 'legacy.sqlite')
            with closing(connect_database(filename)) as connection:
                for script in ('schema.sql', 'member2.sql', 'member3.sql', 'member4.sql', 'member5.sql'):
                    connection.executescript(Path('backend', script).read_text(encoding='utf-8'))
                repository = Repository(connection)
                repository.create_profile(UserProfile('legacy-profile', 'Legacy Designer', 'designer', ['projects:manage']))
                repository.create_account(UserAccount('legacy-owner', 'legacy', 'legacy@example.test', hash_password('synthetic migration password'), 'legacy-profile'))
                timestamp = '2024-02-29T00:00:00+08:00'
                ProjectRepository(repository).create(InteriorDesignProject('legacy-project', 'legacy-owner', None,
                    'Legacy project', 'Real retained record', 'CAT001', 'Modern', 'Current', timestamp, timestamp))
                ActivityRepository(repository).record(ProjectView('legacy-project', 'legacy-event-00000001', timestamp))
            initialize_database(filename)
            initialize_database(filename)
            connection = connect_database(filename)
            try:
                self.assertEqual(connection.execute('PRAGMA user_version').fetchone()[0], 6)
                self.assertEqual(connection.execute('SELECT COUNT(*) FROM report_events').fetchone()[0], 2)
                self.assertEqual(connection.execute('SELECT DISTINCT occurred_at FROM report_events').fetchone()[0], '2024-02-28T16:00:00.000000+00:00')
                self.assertIsNone(connection.execute("SELECT created_at FROM project_categories WHERE category_id='CAT001'").fetchone()[0])
                self.assertEqual(connection.execute('PRAGMA foreign_key_check').fetchall(), [])
            finally: connection.close()

    def test_case_collision_rolls_back_instead_of_merging_categories(self):
        with tempfile.TemporaryDirectory() as directory:
            filename = str(Path(directory) / 'legacy.sqlite')
            connection = connect_database(filename)
            for script in ('schema.sql', 'member2.sql', 'member3.sql', 'member4.sql', 'member5.sql'):
                connection.executescript(Path('backend', script).read_text(encoding='utf-8'))
            connection.execute("INSERT INTO project_categories(category_id,name) VALUES ('old','residential')")
            connection.close()
            with self.assertRaises(sqlite3.IntegrityError): initialize_database(filename)
            connection = connect_database(filename)
            try:
                self.assertEqual(connection.execute('PRAGMA user_version').fetchone()[0], 5)
                self.assertNotIn('name_key', [r['name'] for r in connection.execute('PRAGMA table_info(project_categories)')])
                self.assertEqual(connection.execute('SELECT COUNT(*) FROM project_categories').fetchone()[0], 4)
            finally: connection.close()
