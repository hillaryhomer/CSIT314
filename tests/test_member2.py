"""Real sessions and shared Member 1/2 integration against disposable SQLite files."""
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from backend.app import create_app, main
from backend.database import Repository, connect_database, initialize_database
from backend.member2_repository import Member2Repository
from backend.models import UserAccount, UserProfile
from backend.validation import hash_password

PASSWORD = 'member two integration password'
COMPANY = {'name': 'Studio A', 'address': '12 Studio Road', 'contact': 'hello@example.test', 'description': 'Residential design'}


class Member2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.password_hash = hash_password(PASSWORD)

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='csit314-member2-')
        self.filename = str(Path(self.directory.name) / 'test.sqlite')
        initialize_database(self.filename)
        self.connection = connect_database(self.filename)
        self.repository = Repository(self.connection)
        for role in ('admin', 'designer', 'customer', 'manager'):
            permissions = ['profiles:read', 'profiles:write', 'accounts:read', 'accounts:write'] if role == 'admin' else ['projects:manage']
            self.repository.create_profile(UserProfile('p-' + role, role, role, permissions))
            self.repository.create_account(UserAccount(role, role + '.one', role + '@example.test', self.password_hash, 'p-' + role))
        self.repository.create_account(UserAccount('designer-b', 'designer.two', 'other@example.test', self.password_hash, 'p-designer'))
        self.app = create_app(self.filename)
        self.app.logger.disabled = True

    def tearDown(self):
        self.connection.close()
        self.directory.cleanup()

    def login(self, role='designer', identifier=None):
        client = self.app.test_client()
        response = client.post('/api/auth/login', json={'identifier': identifier or role + '.one', 'password': PASSWORD})
        self.assertEqual(response.status_code, 200, response.get_json())
        return client, {'X-CSRF-Token': response.get_json()['csrfToken']}

    def test_all_roles_login_with_username_email_refresh_and_restart(self):
        for role in ('admin', 'designer', 'customer', 'manager'):
            client, _ = self.login(role, role.upper() + '@EXAMPLE.TEST')
            cookie = client.get_cookie('csit314_session')
            self.assertTrue(cookie.http_only)
            self.assertEqual(cookie.same_site, 'Strict')
            payload = client.get('/api/auth/session').get_json()
            self.assertEqual(payload['role'], role)
            self.assertNotIn('password', str(payload).lower())
            restarted = create_app(self.filename).test_client()
            restarted.set_cookie('csit314_session', cookie.value)
            self.assertEqual(restarted.get('/api/auth/session').status_code, 200)

    def test_member1_created_account_can_login_and_hash_is_hidden(self):
        admin, csrf = self.login('admin')
        response = admin.post('/api/accounts', headers=csrf, json={'username': 'new.designer', 'email': 'new@example.test', 'password': PASSWORD, 'profileId': 'p-designer'})
        self.assertEqual(response.status_code, 201)
        client, _ = self.login(identifier='new.designer')
        self.assertEqual(client.get('/api/auth/session').get_json()['role'], 'designer')
        account = self.repository.account_with_username('new.designer')
        self.assertTrue(account.password_hash.startswith('$2b$'))
        self.assertNotIn('hash', str(response.get_json()).lower())

    def test_invalid_credentials_forged_identity_and_expiry(self):
        client = self.app.test_client()
        for identifier in ('designer.one', 'unknown.user'):
            self.assertEqual(client.post('/api/auth/login', json={'identifier': identifier, 'password': 'wrong'}).status_code, 401)
        self.assertEqual(client.get('/api/company', headers={'X-Admin-Id': 'admin'}).status_code, 401)
        client.set_cookie('csit314_session', 'forged-token')
        self.assertEqual(client.get('/api/auth/session').status_code, 401)
        client, _ = self.login()
        self.connection.execute('UPDATE auth_sessions SET expires_at=0')
        self.assertEqual(client.get('/api/company').status_code, 401)

    def test_csrf_origin_and_payload_rejection(self):
        client, csrf = self.login()
        self.assertEqual(client.post('/api/company', json=COMPANY).status_code, 403)
        self.assertEqual(client.post('/api/company', json=COMPANY, headers={**csrf, 'Origin': 'https://evil.example'}).status_code, 403)
        for data in ({**COMPANY, 'ownerId': 'designer-b'}, {**COMPANY, 'name': '  '}, {**COMPANY, 'description': 'x' * 4001}, {**COMPANY, 'contact': 123}):
            self.assertEqual(client.post('/api/company', json=data, headers=csrf).status_code, 400)
        self.assertIsNone(client.get('/api/company').get_json()['company'])

    def test_company_crud_search_restart_and_preserved_account(self):
        client, csrf = self.login()
        self.assertIsNone(client.get('/api/company').get_json()['company'])
        response = client.post('/api/company', json=COMPANY, headers=csrf)
        self.assertEqual(response.status_code, 201)
        company = response.get_json()
        self.assertEqual(company['ownerId'], 'designer')
        self.assertEqual(client.post('/api/company', json=COMPANY, headers=csrf).status_code, 409)
        self.assertTrue(client.get('/api/company?q=RESIDENTIAL').get_json()['matches'])
        self.assertFalse(client.get('/api/company?q=nonexistent').get_json()['matches'])
        endpoint = '/api/company/' + company['companyId']
        self.assertEqual(client.put(endpoint, json={**COMPANY, 'name': 'Renamed'}, headers=csrf).status_code, 200)
        restarted = create_app(self.filename).test_client()
        restarted.set_cookie('csit314_session', client.get_cookie('csit314_session').value)
        self.assertEqual(restarted.get('/api/company').get_json()['company']['name'], 'Renamed')
        self.assertEqual(client.delete(endpoint, json={}, headers=csrf).status_code, 200)
        self.assertIsNone(restarted.get('/api/company').get_json()['company'])
        self.assertIsNotNone(self.repository.find_account('designer'))

    def test_company_ownership_and_role_checks(self):
        owner, csrf = self.login()
        company = owner.post('/api/company', json=COMPANY, headers=csrf).get_json()
        other, other_csrf = self.login(identifier='designer.two')
        self.assertIsNone(other.get('/api/company?q=Studio').get_json()['company'])
        endpoint = '/api/company/' + company['companyId']
        self.assertEqual(other.put(endpoint, json=COMPANY, headers=other_csrf).status_code, 404)
        self.assertEqual(other.delete(endpoint, json={}, headers=other_csrf).status_code, 404)
        self.assertEqual(owner.put(endpoint, json={**COMPANY, 'companyId': 'changed'}, headers=csrf).status_code, 400)
        for role in ('admin', 'customer', 'manager'):
            client, role_csrf = self.login(role)
            self.assertEqual(client.get('/api/company').status_code, 403)
            self.assertEqual(client.post('/api/company', json=COMPANY, headers=role_csrf).status_code, 403)
        self.assertEqual(owner.get('/api/accounts').status_code, 403)

    def test_admin_search_suspension_revokes_all_sessions_and_blocks_login(self):
        admin, csrf = self.login('admin')
        first, designer_csrf = self.login()
        second, _ = self.login()
        company = first.post('/api/company', json=COMPANY, headers=designer_csrf).get_json()
        for query in ('DESIGNER.ONE', 'designer@EXAMPLE.TEST'):
            rows = admin.get('/api/accounts', query_string={'q': query}).get_json()
            self.assertEqual(len(rows), 1)
            self.assertIn('profileName', rows[0])
            self.assertNotIn('password', str(rows).lower())
        self.assertEqual(admin.get('/api/accounts?q=not-found').get_json(), [])
        self.assertEqual(first.post('/api/accounts/admin/suspend', json={}, headers=designer_csrf).status_code, 403)
        self.assertEqual(admin.post('/api/accounts/admin/suspend', json={}, headers=csrf).status_code, 403)
        self.assertEqual(admin.post('/api/accounts/designer/suspend', json={}, headers=csrf).get_json()['status'], 'Suspended')
        for client in (first, second):
            self.assertEqual(client.get('/api/company').status_code, 401)
        self.assertEqual(admin.post('/api/accounts/designer/suspend', json={}, headers=csrf).status_code, 409)
        self.assertEqual(first.post('/api/auth/login', json={'identifier': 'designer.one', 'password': PASSWORD}).status_code, 403)
        self.assertIsNotNone(self.repository.find_account('designer'))
        self.assertEqual(Member2Repository(self.repository).company('designer')['companyId'], company['companyId'])

    def test_logout_invalidates_cookie_replay_and_other_sessions_remain(self):
        client, csrf = self.login()
        second, _ = self.login()
        cookie = client.get_cookie('csit314_session').value
        self.assertEqual(client.post('/api/auth/logout', json={}, headers=csrf).status_code, 200)
        self.assertIsNone(client.get_cookie('csit314_session'))
        client.set_cookie('csit314_session', cookie)
        self.assertEqual(client.get('/api/auth/session').status_code, 401)
        self.assertEqual(client.get('/api/company').status_code, 401)
        self.assertEqual(second.get('/api/company').status_code, 200)

    def test_login_rotates_session_and_cli_admin_can_sign_in(self):
        client, _ = self.login()
        previous = client.get_cookie('csit314_session').value
        self.assertEqual(client.post('/api/auth/login', json={'identifier': 'designer.one', 'password': PASSWORD}).status_code, 200)
        self.assertNotEqual(client.get_cookie('csit314_session').value, previous)
        replay = self.app.test_client()
        replay.set_cookie('csit314_session', previous)
        self.assertEqual(replay.get('/api/auth/session').status_code, 401)
        with patch('sys.argv', ['backend.app', '--create-admin']), patch.dict('os.environ', {'DATABASE_PATH': self.filename}), patch('builtins.input', side_effect=['bootstrap.admin', 'bootstrap@example.test']), patch('backend.app.getpass', return_value=PASSWORD), patch('builtins.print'):
            main()
        admin, _ = self.login(identifier='bootstrap.admin')
        self.assertEqual(admin.get('/api/auth/session').get_json()['role'], 'admin')
        self.assertEqual(admin.get('/api/accounts').status_code, 200)

    def test_profile_suspension_and_permission_changes_apply_to_existing_session(self):
        admin, csrf = self.login('admin')
        designer, _ = self.login()
        self.assertEqual(admin.post('/api/profiles/p-designer/suspend', json={}, headers=csrf).status_code, 200)
        self.assertEqual(designer.get('/api/company').status_code, 403)
        self.assertEqual(designer.post('/api/auth/login', json={'identifier': 'designer.one', 'password': PASSWORD}).status_code, 403)
        profile = self.repository.find_profile('p-admin')
        profile.permissions = ['accounts:read']
        self.repository.update_profile(profile)
        self.assertEqual(admin.post('/api/accounts/designer-b/suspend', json={}, headers=csrf).status_code, 403)

    def test_persistence_errors_never_succeed_and_transactions_roll_back(self):
        client, csrf = self.login()
        original = Member2Repository.create_company
        def fail_after_insert(store, *args):
            original(store, *args)
            raise sqlite3.OperationalError('simulated disk failure')
        with patch.object(Member2Repository, 'create_company', fail_after_insert):
            response = client.post('/api/company', json=COMPANY, headers=csrf)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_json()['error']['code'], 'PERSISTENCE')
        self.assertNotIn('disk', response.get_data(as_text=True))
        self.assertIsNone(client.get('/api/company').get_json()['company'])

    def test_migration_preserves_legacy_member1_records(self):
        filename = str(Path(self.directory.name) / 'legacy.sqlite')
        connection = connect_database(filename)
        connection.executescript(Path('backend/schema.sql').read_text())
        repo = Repository(connection)
        repo.create_profile(UserProfile('old-profile', 'Old Designer', 'designer', ['projects:manage']))
        repo.create_account(UserAccount('old-account', 'old.designer', 'old@example.test', self.password_hash, 'old-profile'))
        connection.close()
        initialize_database(filename)
        connection = connect_database(filename)
        try:
            self.assertEqual(connection.execute('PRAGMA user_version').fetchone()[0], 3)
            self.assertEqual(Repository(connection).find_account('old-account').password_hash, self.password_hash)
            self.assertIsNone(Member2Repository(Repository(connection)).company('old-account'))
        finally:
            connection.close()
