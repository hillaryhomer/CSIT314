"""Disposable browser-test accounts. Never run against the application's database."""
import os
from pathlib import Path

from backend.database import connect_database, Repository
from backend.models import UserAccount
from backend.validation import hash_password

filename = Path(os.environ['DATABASE_PATH']).resolve()
if filename.parent != Path('.test-data').resolve() or not filename.name.startswith('python-browser-'):
    raise RuntimeError('Browser fixtures require a dedicated test database.')
connection = connect_database(str(filename))
try:
    repository = Repository(connection)
    password_hash = hash_password('browser test password 123')
    with repository.transaction():
        for role in ('admin', 'designer', 'customer', 'manager'):
            repository.create_account(UserAccount('browser-' + role, 'browser.' + role, role + '@browser.test', password_hash, 'dev-profile-' + role))
        repository.create_account(UserAccount('browser-designer-b', 'browser.designer.b', 'designer-b@browser.test', password_hash, 'dev-profile-designer'))
finally:
    connection.close()
