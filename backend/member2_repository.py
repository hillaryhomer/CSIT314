"""SQL for Member 2, using the same connection and transactions as Member 1."""
import hashlib
import time

from backend.models import CompanyInformation


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class Member2Repository:
    def __init__(self, repository):
        self.connection = repository.connection

    def session(self, token):
        if not token:
            return None
        return self.connection.execute(
            'SELECT * FROM auth_sessions WHERE token_hash=? AND expires_at>?',
            (token_hash(token), int(time.time())),
        ).fetchone()

    def remove_session(self, token):
        self.connection.execute('DELETE FROM auth_sessions WHERE token_hash=?', (token_hash(token),))

    def create_session(self, token, account_id, csrf):
        self.connection.execute('DELETE FROM auth_sessions WHERE expires_at<=?', (int(time.time()),))
        self.connection.execute('INSERT INTO auth_sessions VALUES (?, ?, ?, ?)',
                                (token_hash(token), account_id, csrf, int(time.time()) + 28800))

    def suspend_account(self, account_id):
        self.connection.execute("UPDATE user_accounts SET status='Suspended' WHERE account_id=?", (account_id,))
        self.connection.execute('DELETE FROM auth_sessions WHERE account_id=?', (account_id,))

    def company(self, owner_id):
        row = self.connection.execute('SELECT * FROM companies WHERE owner_id=?', (owner_id,)).fetchone()
        return CompanyInformation(**dict(row)).to_dict() if row else None

    def create_company(self, company_id, owner_id, values):
        self.connection.execute('INSERT INTO companies VALUES (?, ?, ?, ?, ?, ?, ?)',
            (company_id, owner_id, values['name'], values['regNumber'], values['address'], values['contact'], values['description']))

    def update_company(self, company_id, owner_id, values):
        self.connection.execute('UPDATE companies SET name=?, reg_number=?, address=?, contact=?, description=? WHERE company_id=? AND owner_id=?',
            (values['name'], values['regNumber'], values['address'], values['contact'], values['description'], company_id, owner_id))

    def delete_company(self, company_id, owner_id):
        self.connection.execute('DELETE FROM companies WHERE company_id=? AND owner_id=?', (company_id, owner_id))
