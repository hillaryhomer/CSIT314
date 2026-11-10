"""Base TestCase class for all User Story automated tests.
Provides isolated temporary SQLite database and Flask test client fixtures.
"""
from pathlib import Path
import tempfile
import unittest

from backend.app import DevelopmentContext, create_app
from backend.database import Repository, connect_database, initialize_database
from backend.models import UserAccount, UserProfile
from backend.validation import hash_password

PASSWORD = "testpassword123"
ADMIN_PERMS = ["profiles:read", "profiles:write", "accounts:read", "accounts:write"]


class IdpTestCase(unittest.TestCase):
    password_hash = hash_password(PASSWORD)

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="csit314-idp-")
        self.filename = str(Path(self.directory.name) / "test.sqlite")
        initialize_database(self.filename)
        self.connection = connect_database(self.filename)
        self.repository = Repository(self.connection)
        
        # Seed default profiles
        self.repository.create_profile(UserProfile("admin-profile", "User Admin", "admin", ADMIN_PERMS))
        self.repository.create_profile(UserProfile("p-designer", "Interior Designer", "designer", ["projects:manage"]))
        self.repository.create_profile(UserProfile("p-customer", "Customer", "customer", ["projects:discover"]))
        self.repository.create_profile(UserProfile("p-manager", "Platform Manager", "manager", ["categories:manage", "reports:view"]))
        
        # Seed default accounts
        self.repository.create_account(UserAccount("admin", "test.admin", "admin@example.test", self.password_hash, "admin-profile"))
        self.repository.create_account(UserAccount("designer-1", "designer.one", "designer1@example.test", self.password_hash, "p-designer"))
        self.repository.create_account(UserAccount("customer-1", "customer.one", "customer1@example.test", self.password_hash, "p-customer"))
        self.repository.create_account(UserAccount("manager-1", "manager.one", "manager1@example.test", self.password_hash, "p-manager"))

        self.app = create_app(self.filename, DevelopmentContext("development", "admin"))
        self.client = self.app.test_client()

    def tearDown(self):
        try:
            self.connection.close()
        except Exception:
            pass
        try:
            self.directory.cleanup()
        except Exception:
            pass
