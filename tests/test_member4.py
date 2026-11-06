"""Customer workflows, authorization and integration using real sessions and disposable databases."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from backend.app import create_app
from backend.database import Repository, connect_database, initialize_database
from backend.favourite_repository import FavouriteRepository, ProjectActivityAdapter
from backend.models import UserAccount, UserProfile
from backend.validation import hash_password

PASSWORD = 'member four integration password'
PROJECT = {'title': 'Quiet Loft', 'description': 'Calm coastal interiors', 'categoryId': 'CAT001', 'style': 'Japandi', 'images': []}


class Member4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.password_hash = hash_password(PASSWORD)

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='csit314-member4-')
        self.filename = str(Path(self.directory.name) / 'customer.sqlite')
        initialize_database(self.filename)
        self.connection = connect_database(self.filename)
        self.repository = Repository(self.connection)
        permissions = {'admin': ['accounts:read', 'accounts:write'], 'designer': ['projects:manage'], 'customer': ['projects:discover'], 'manager': ['reports:read']}
        for role in permissions:
            self.repository.create_profile(UserProfile(role, role, role, permissions[role]))
            self.repository.create_account(UserAccount(role, role + '.one', role + '@example.test', self.password_hash, role))
        self.repository.create_account(UserAccount('customer-b', 'customer.two', 'other@example.test', self.password_hash, 'customer'))
        self.app = create_app(self.filename)
        self.app.logger.disabled = True
        self.designer, self.designer_csrf = self.login('designer.one')

    def tearDown(self):
        self.connection.close()
        self.directory.cleanup()

    def login(self, username):
        client = self.app.test_client()
        response = client.post('/api/auth/login', json={'identifier': username, 'password': PASSWORD})
        self.assertEqual(response.status_code, 200, response.get_json())
        return client, {'X-CSRF-Token': response.get_json()['csrfToken']}

    def project(self, kind='current', **fields):
        response = self.designer.post('/api/designer/projects/' + kind, json={**PROJECT, **fields}, headers=self.designer_csrf)
        self.assertEqual(response.status_code, 201, response.get_json())
        return response.get_json()

    def save(self, client, csrf, project):
        return client.post('/api/favourites', json={'projectId': project['projectId']}, headers=csrf)

    def test_keyword_category_style_combination_empty_filters_and_options(self):
        a = self.project()
        b = self.project('past', title='Quiet Cafe', categoryId='CAT003', style='Modern')
        c = self.project(title='Office', description='Workspaces', categoryId='CAT002', style='japandi')
        d = self.project('past', title='Home', description='Family interiors', style='Modern')
        public = self.app.test_client()
        def ids(**query): return {p['projectId'] for p in public.get('/api/catalog/projects', query_string=query).get_json()}
        self.assertEqual(ids(q='  COASTAL  '), {a['projectId'], b['projectId']})
        self.assertEqual(ids(categoryId='CAT001'), {a['projectId'], d['projectId']})
        self.assertEqual(ids(style='  JAPANDI '), {a['projectId'], c['projectId']})
        self.assertEqual(ids(q='coastal', categoryId='CAT001', style='japandi'), {a['projectId']})
        self.assertEqual(ids(q='coastal', categoryId='CAT002', style='Modern'), set())
        self.assertEqual(ids(q='', categoryId='', style=''), {p['projectId'] for p in (a, b, c, d)})
        self.assertEqual(ids(q="%' OR 1=1 --"), set())
        self.assertEqual({s.lower() for s in public.get('/api/catalog/styles').get_json()}, {'japandi', 'modern'})
        self.assertEqual(len(public.get('/api/project-categories').get_json()), 3)
        for query in ({'q': 'x' * 255}, {'style': 'x' * 101}, {'categoryId': 'x' * 101}, {'customerId': 'customer-b'}):
            self.assertEqual(public.get('/api/catalog/projects', query_string=query).status_code, 400)

    def test_public_details_exclude_account_private_fields_and_report_unavailable(self):
        company = self.designer.post('/api/company', json={'name': 'Public Studio', 'address': 'PRIVATE ADDRESS', 'contact': 'private@example.test'}, headers=self.designer_csrf)
        self.assertEqual(company.status_code, 201)
        project = self.project()
        public = self.app.test_client()
        record = public.get('/api/catalog/projects/' + project['projectId']).get_json()
        self.assertEqual(record['companyName'], 'Public Studio')
        self.assertFalse(record['saved'])
        for forbidden in ('ownerAccountId', 'companyId', 'customerId', 'email', 'permissions', 'password', 'passwordHash'):
            self.assertNotIn(forbidden, record)
        for value in ('PRIVATE ADDRESS', 'private@example.test', 'designer.one'):
            self.assertNotIn(value, str(record))
        self.assertEqual(public.get('/api/catalog/projects/missing').status_code, 404)
        self.connection.execute("UPDATE user_accounts SET status='Suspended' WHERE account_id='designer'")
        self.assertEqual(public.get('/api/catalog/projects/' + project['projectId']).status_code, 404)
        self.assertEqual(public.get('/api/catalog/styles').get_json(), [])

    def test_add_is_idempotent_unique_and_saved_state_is_personal(self):
        project = self.project()
        customer, csrf = self.login('customer.one')
        first = self.save(customer, csrf, project)
        self.assertEqual(first.status_code, 201)
        self.assertTrue(first.get_json()['created'])
        repeated = self.save(customer, csrf, project)
        self.assertEqual(repeated.status_code, 200)
        self.assertFalse(repeated.get_json()['created'])
        self.assertEqual(first.get_json()['project']['savedAt'], repeated.get_json()['project']['savedAt'])
        with self.assertRaises(sqlite3.IntegrityError):
            self.connection.execute("INSERT INTO favourites VALUES ('customer',?,'duplicate')", (project['projectId'],))
        self.assertEqual(ProjectActivityAdapter(self.repository).shortlist_count(project['projectId']), 1)
        self.assertTrue(customer.get('/api/catalog/projects/' + project['projectId']).get_json()['saved'])
        self.assertTrue(customer.get('/api/catalog/projects').get_json()[0]['saved'])
        other, _ = self.login('customer.two')
        self.assertFalse(other.get('/api/catalog/projects/' + project['projectId']).get_json()['saved'])
        self.assertEqual(other.get('/api/favourites').get_json(), [])

    def test_personal_favourite_list_and_search_never_search_other_customers_or_catalog(self):
        a = self.project(title='Garden Loft')
        b = self.project('past', title='Garden Cafe', categoryId='CAT003')
        self.project(title='Unsaved Garden House')
        customer, csrf = self.login('customer.one')
        other, other_csrf = self.login('customer.two')
        self.save(customer, csrf, a); self.save(other, other_csrf, b)
        for path in ('/api/favourites', '/api/favourites?q=', '/api/favourites?q=GARDEN', '/api/favourites?q=%20coastal%20'):
            self.assertEqual([p['projectId'] for p in customer.get(path).get_json()], [a['projectId']])
        self.assertEqual(customer.get('/api/favourites?q=Cafe').get_json(), [])
        self.assertEqual(customer.get('/api/favourites?q=Unsaved').get_json(), [])
        self.assertEqual(customer.get('/api/favourites?customerId=customer-b').status_code, 400)
        self.assertEqual(customer.get('/api/customers/customer-b/favourites').status_code, 404)
        self.assertEqual(customer.post('/api/favourites', json={'projectId': b['projectId'], 'customerId': 'customer-b'}, headers=csrf).status_code, 400)
        self.assertEqual(customer.post('/api/favourites?customerId=customer-b', json={'projectId': b['projectId']}, headers=csrf).status_code, 400)
        self.assertEqual(len(other.get('/api/favourites').get_json()), 1)
        self.assertEqual(customer.get('/api/favourites?q=' + 'x' * 255).status_code, 400)

    def test_login_restart_logout_persistence_and_latest_project_fields(self):
        project = self.project()
        customer, csrf = self.login('customer.one'); self.save(customer, csrf, project)
        restarted = create_app(self.filename).test_client()
        restarted.set_cookie('csit314_session', customer.get_cookie('csit314_session').value)
        self.assertEqual(restarted.get('/api/favourites').get_json()[0]['projectId'], project['projectId'])
        self.assertEqual(customer.post('/api/auth/logout', json={}, headers=csrf).status_code, 200)
        self.assertEqual(customer.get('/api/favourites').status_code, 401)
        customer, _ = self.login('customer.one')
        updated = self.designer.put('/api/designer/projects/current/' + project['projectId'], json={**PROJECT, 'title': 'Updated Loft', 'style': 'Modern'}, headers=self.designer_csrf)
        self.assertEqual(updated.status_code, 200)
        favourite = customer.get('/api/favourites').get_json()[0]
        self.assertEqual(favourite['title'], 'Updated Loft')
        self.assertEqual(favourite['style'], 'Modern')
        self.assertTrue(favourite['saved'])

    def test_roles_permissions_csrf_suspension_and_missing_projects(self):
        project = self.project()
        anonymous = self.app.test_client()
        self.assertEqual(anonymous.get('/api/favourites').status_code, 401)
        self.assertEqual(anonymous.post('/api/favourites', json={'projectId': project['projectId']}).status_code, 401)
        for role in ('admin', 'designer', 'manager'):
            client, csrf = self.login(role + '.one')
            self.assertEqual(client.get('/api/favourites').status_code, 403)
            self.assertEqual(self.save(client, csrf, project).status_code, 403)
        customer, csrf = self.login('customer.one')
        self.assertEqual(customer.post('/api/favourites', json={'projectId': project['projectId']}).status_code, 403)
        self.assertEqual(customer.post('/api/favourites', json={'projectId': project['projectId']}, headers={**csrf, 'Origin': 'https://evil.example'}).status_code, 403)
        self.assertEqual(self.save(customer, csrf, {'projectId': 'missing'}).status_code, 404)
        for payload in ({}, {'projectId': 3}, {'projectId': ''}, {'projectId': 'x' * 101}):
            self.assertEqual(customer.post('/api/favourites', json=payload, headers=csrf).status_code, 400)
        profile = self.repository.find_profile('customer'); profile.permissions = ['reports:read']; self.repository.update_profile(profile)
        self.assertEqual(customer.get('/api/favourites').status_code, 403)
        self.assertEqual(self.save(customer, csrf, project).status_code, 403)
        profile.permissions = ['projects:discover']; self.repository.update_profile(profile)
        admin, admin_csrf = self.login('admin.one')
        admin.post('/api/accounts/customer/suspend', json={}, headers=admin_csrf)
        self.assertEqual(customer.get('/api/favourites').status_code, 401)
        self.assertEqual(self.save(customer, csrf, project).status_code, 401)

    def test_unavailable_projects_hidden_without_broken_rows_deleted_projects_cascade(self):
        a = self.project(); b = self.project('past', title='Another project')
        customer, csrf = self.login('customer.one'); self.save(customer, csrf, a); self.save(customer, csrf, b)
        profile = self.repository.find_profile('designer'); profile.status = 'Suspended'; self.repository.update_profile(profile)
        self.assertEqual(customer.get('/api/favourites').get_json(), [])
        self.assertEqual(self.save(customer, csrf, a).status_code, 404)
        self.assertEqual(ProjectActivityAdapter(self.repository).shortlist_count(a['projectId']), 1)
        profile.status = 'Active'; self.repository.update_profile(profile)
        self.assertEqual(len(customer.get('/api/favourites').get_json()), 2)
        self.designer.delete('/api/designer/projects/current/' + a['projectId'], json={}, headers=self.designer_csrf)
        self.assertEqual([p['projectId'] for p in customer.get('/api/favourites').get_json()], [b['projectId']])
        self.assertEqual(ProjectActivityAdapter(self.repository).shortlist_count(a['projectId']), 0)
        self.assertEqual(self.connection.execute('PRAGMA foreign_key_check').fetchall(), [])

    def test_storage_error_rolls_back_and_does_not_claim_saved(self):
        project = self.project(); customer, csrf = self.login('customer.one')
        original = FavouriteRepository.add
        def fail_after_insert(store, favourite):
            original(store, favourite)
            raise sqlite3.OperationalError('simulated private storage failure')
        with patch.object(FavouriteRepository, 'add', fail_after_insert):
            response = self.save(customer, csrf, project)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_json()['error']['code'], 'PERSISTENCE')
        self.assertNotIn('private storage', response.get_data(as_text=True))
        self.assertEqual(customer.get('/api/favourites').get_json(), [])
        self.assertFalse(customer.get('/api/catalog/projects/' + project['projectId']).get_json()['saved'])
        with patch.object(FavouriteRepository, 'list_for_customer', side_effect=sqlite3.OperationalError('disk read failed')):
            self.assertEqual(customer.get('/api/favourites').status_code, 500)

    def test_concurrent_saves_and_repeated_detail_reads_do_not_double_count_shortlists(self):
        project = self.project()
        customer, csrf = self.login('customer.one')
        cookie = customer.get_cookie('csit314_session').value
        def save_in_thread(_):
            client = self.app.test_client(); client.set_cookie('csit314_session', cookie)
            return self.save(client, csrf, project).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sorted(pool.map(save_in_thread, range(2))), [200, 201])
        for _ in range(3):
            self.assertEqual(customer.get('/api/catalog/projects/' + project['projectId']).status_code, 200)
        adapter = ProjectActivityAdapter(self.repository)
        self.assertEqual(adapter.shortlist_count(project['projectId']), 1)
        self.assertTrue(adapter.view_tracking_available)
        other, other_csrf = self.login('customer.two'); self.save(other, other_csrf, project)
        self.assertEqual(adapter.shortlist_count(project['projectId']), 2)
        self.assertEqual(customer.delete('/api/favourites', json={'projectId': project['projectId']}, headers=csrf).status_code, 404)
        self.assertEqual(adapter.shortlist_count(project['projectId']), 2)

    def test_version3_migration_preserves_existing_records(self):
        legacy = str(Path(self.directory.name) / 'legacy.sqlite')
        con = connect_database(legacy)
        con.executescript(''.join(Path('backend/' + file).read_text() for file in ('schema.sql','member2.sql','member3.sql')))
        repo = Repository(con)
        repo.create_profile(UserProfile('p', 'Old Designer', 'designer', ['projects:manage']))
        repo.create_account(UserAccount('a', 'legacy.designer', 'legacy@example.test', self.password_hash, 'p'))
        before = con.execute('SELECT * FROM user_accounts').fetchall()
        con.close(); initialize_database(legacy); con = connect_database(legacy)
        try:
            self.assertEqual(con.execute('PRAGMA user_version').fetchone()[0], 6)
            self.assertEqual(con.execute('SELECT * FROM user_accounts').fetchall(), before)
            self.assertEqual(con.execute('SELECT COUNT(*) FROM favourites').fetchone()[0], 0)
            self.assertEqual(con.execute('PRAGMA foreign_key_check').fetchall(), [])
        finally: con.close()
