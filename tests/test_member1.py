"""Tests using Python's built-in unittest. No pytest or mock server is required."""

from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from backend.app import AuthenticatedContext, DevelopmentContext, create_app
from backend.controllers import effective_access
from backend.database import Repository, connect_database, initialize_database
from backend.models import AppError, UserAccount, UserProfile
from backend.validation import hash_password, verify_password


PASSWORD = "a secure test passphrase"
PROFILE = {"name": "Project Designers", "role": "designer", "permissions": ["projects:manage"]}
ADMIN_PERMISSIONS = ["profiles:read", "profiles:write", "accounts:read", "accounts:write"]


class Member1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.password_hash = hash_password(PASSWORD)

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="csit314-python-")
        self.filename = str(Path(self.directory.name) / "test.sqlite")
        initialize_database(self.filename)
        self.connection = connect_database(self.filename)
        self.repository = Repository(self.connection)
        self.repository.create_profile(UserProfile("admin-profile", "User Admin", "admin", ADMIN_PERMISSIONS))
        self.repository.create_account(UserAccount("admin", "test.admin", "admin@example.test", self.password_hash, "admin-profile"))
        self.app = create_app(self.filename, DevelopmentContext("development", "admin"))
        self.client = self.app.test_client()

    def tearDown(self):
        self.connection.close()
        self.directory.cleanup()

    def create_profile(self, name="Project Designers"):
        response = self.client.post("/api/profiles", json={**PROFILE, "name": name})
        self.assertEqual(response.status_code, 201)
        return response.get_json()

    def account_input(self, profile_id, username="designer.one"):
        return {"username": username, "email": username + "@example.test",
                "password": PASSWORD, "profileId": profile_id}

    def create_account(self, profile_id, username="designer.one"):
        response = self.client.post("/api/accounts", json=self.account_input(profile_id, username))
        self.assertEqual(response.status_code, 201)
        return response.get_json()

    def test_profile_create_view_update_and_search(self):
        profile = self.create_profile()
        profile_id = profile["profileId"]
        self.assertEqual(profile["status"], "Active")
        self.assertEqual(self.client.get(f"/api/profiles/{profile_id}").get_json(), profile)
        self.assertEqual(len(self.client.get("/api/profiles?name=DESIGNERS").get_json()), 1)
        self.assertEqual(len(self.client.get("/api/profiles?name=").get_json()), 2)
        self.assertEqual(self.client.get("/api/profiles?name=projects:manage").get_json(), [])
        self.assertEqual(self.client.get("/api/profiles?name=%25").get_json(), [])
        response = self.client.put(f"/api/profiles/{profile_id}", json={**PROFILE, "name": "Renamed Designers"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["profileId"], profile_id)
        self.assertEqual(self.repository.find_profile(profile_id).name, "Renamed Designers")

    def test_profile_validation_and_case_insensitive_uniqueness(self):
        self.create_profile()
        invalid_inputs = [
            {**PROFILE, "name": "   "}, {**PROFILE, "name": "x" * 81},
            {**PROFILE, "role": "superuser"}, {**PROFILE, "permissions": []},
            {**PROFILE, "permissions": ["invented"]},
            {**PROFILE, "permissions": ["projects:manage", "projects:manage"]},
            {**PROFILE, "permissions": [{}]}, {**PROFILE, "status": "Suspended"},
        ]
        for data in invalid_inputs:
            with self.subTest(data=data):
                self.assertEqual(self.client.post("/api/profiles", json=data).status_code, 400)
        duplicate = self.client.post("/api/profiles", json={**PROFILE, "name": " PROJECT DESIGNERS "})
        self.assertEqual(duplicate.status_code, 409)
        self.assertIn("name", duplicate.get_json()["error"]["fields"])
        profile = self.create_profile("Ｃａｆé")
        self.assertEqual(self.client.post("/api/profiles", json={**PROFILE, "name": "café"}).status_code, 409)
        self.assertEqual(self.client.put(f"/api/profiles/{profile['profileId']}", json={**PROFILE, "name": "CAFÉ"}).status_code, 200)

    def test_suspend_preserves_profile_and_rejects_repeat(self):
        profile_id = self.create_profile()["profileId"]
        endpoint = f"/api/profiles/{profile_id}"
        self.assertEqual(self.client.post(endpoint + "/suspend", json={}).get_json()["status"], "Suspended")
        self.assertIsNotNone(self.repository.find_profile(profile_id))
        self.assertEqual(self.client.post(endpoint + "/suspend", json={}).status_code, 409)
        response = self.client.put(endpoint, json={**PROFILE, "name": "Still Suspended"})
        self.assertEqual(response.get_json()["status"], "Suspended")

    def test_missing_records_return_not_found(self):
        for endpoint in ("/api/profiles/missing", "/api/accounts/missing"):
            self.assertEqual(self.client.get(endpoint).status_code, 404)
            self.assertEqual(self.client.put(endpoint, json={}).status_code, 404)
        self.assertEqual(self.client.post("/api/profiles/missing/suspend", json={}).status_code, 404)

    def test_account_creation_hashes_password_and_hides_credentials(self):
        profile_id = self.create_profile()["profileId"]
        account = self.create_account(profile_id)
        stored = self.repository.find_account(account["accountId"])
        self.assertTrue(stored.password_hash.startswith("$2b$12$"))
        self.assertNotEqual(stored.password_hash, PASSWORD)
        self.assertTrue(verify_password(PASSWORD, stored.password_hash))
        self.assertFalse(verify_password("incorrect password", stored.password_hash))
        self.assertFalse(verify_password("a" * 73, stored.password_hash))
        viewed = self.client.get(f"/api/accounts/{account['accountId']}").get_json()
        for record in (account, viewed, *self.client.get("/api/accounts").get_json()):
            self.assertNotIn("password", record)
            self.assertNotIn("passwordHash", record)
            self.assertNotIn(stored.password_hash, str(record))

    def test_account_validation_and_duplicate_rejection(self):
        profile_id = self.create_profile()["profileId"]
        data = self.account_input(profile_id)
        invalid_inputs = [
            {**data, "username": "  "}, {**data, "username": "bad user"},
            {**data, "email": "bad-email"}, {**data, "password": "short"},
            {**data, "password": " " * 12}, {**data, "password": "é" * 37},
            {**data, "profileId": "missing"}, {**data, "status": "Suspended"},
        ]
        for values in invalid_inputs:
            with self.subTest(values=values):
                self.assertEqual(self.client.post("/api/accounts", json=values).status_code, 400)
        self.create_account(profile_id)
        for values in ({**data, "username": " DESIGNER.ONE "},
                       {**data, "username": "other.user", "email": " DESIGNER.ONE@EXAMPLE.TEST "}):
            self.assertEqual(self.client.post("/api/accounts", json=values).status_code, 409)

    def test_profile_rename_keeps_account_assignment(self):
        profile_id = self.create_profile()["profileId"]
        account = self.create_account(profile_id)
        self.client.put(f"/api/profiles/{profile_id}", json={**PROFILE, "name": "Renamed Studio"})
        viewed = self.client.get(f"/api/accounts/{account['accountId']}").get_json()
        self.assertEqual(viewed["profileId"], profile_id)
        self.assertEqual(viewed["profileName"], "Renamed Studio")

    def test_account_update_preserves_id_hash_and_suspended_status(self):
        self.repository.create_account(UserAccount("suspended", "suspended.user", "suspended@example.test",
                                                   self.password_hash, "admin-profile", "Suspended"))
        data = {"username": "updated.user", "email": " Updated@Example.Test ", "profileId": "admin-profile"}
        result = self.client.put("/api/accounts/suspended", json=data)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.get_json()["accountId"], "suspended")
        self.assertEqual(result.get_json()["email"], "updated@example.test")
        self.assertEqual(result.get_json()["status"], "Suspended")
        self.assertEqual(self.repository.find_account("suspended").password_hash, self.password_hash)
        for extra in ({"password": PASSWORD}, {"status": "Active"}, {"passwordHash": self.password_hash}):
            self.assertEqual(self.client.put("/api/accounts/suspended", json={**data, **extra}).status_code, 400)
        self.assertEqual(self.client.put("/api/accounts/suspended", json={**data, "username": "TEST.ADMIN"}).status_code, 409)

    def test_suspended_profile_blocks_new_assignment_and_effective_access(self):
        profile_id = self.create_profile()["profileId"]
        account = self.create_account(profile_id)
        self.client.post(f"/api/profiles/{profile_id}/suspend", json={})
        self.assertEqual(self.repository.find_account(account["accountId"]).status, "Active")
        self.assertEqual(self.repository.find_account(account["accountId"]).profile_id, profile_id)
        with self.assertRaises(AppError) as failure:
            effective_access(self.repository, account["accountId"])
        self.assertEqual(failure.exception.code, "FORBIDDEN")
        self.assertEqual(self.client.post("/api/accounts", json=self.account_input(profile_id, "another.user")).status_code, 400)
        data = {"username": "retained.user", "email": account["email"], "profileId": profile_id}
        self.assertEqual(self.client.put(f"/api/accounts/{account['accountId']}", json=data).status_code, 200)
        other = self.create_profile("Active profile")["profileId"]
        second = self.create_account(other, "other.user")
        changed = {**data, "username": "other.user", "email": second["email"]}
        self.assertEqual(self.client.put(f"/api/accounts/{second['accountId']}", json=changed).status_code, 400)

    def test_password_hash_from_previous_javascript_backend_still_works(self):
        old_hash = "$2b$12$atOnIC.uUgdTPFXrPQJ.5em1p3HlYh3KwAuG5b7TDhBJgAV3AHExO"
        self.assertTrue(verify_password(PASSWORD, old_hash))
        self.assertFalse(verify_password("wrong password", old_hash))

    def test_authorization_and_browser_identity_claims(self):
        closed = create_app(self.filename, AuthenticatedContext()).test_client()
        forged = closed.post("/api/profiles", json={**PROFILE, "actorId": "admin"}, headers={"X-Admin-Id": "admin"})
        self.assertEqual(forged.status_code, 401)
        profile_id = self.create_profile()["profileId"]
        self.repository.create_account(UserAccount("customer", "customer.user", "customer@example.test", self.password_hash, profile_id))
        customer = create_app(self.filename, DevelopmentContext("development", "customer")).test_client()
        for method, path, body in (
            ("GET", "/api/profiles", None), ("POST", "/api/profiles", PROFILE),
            ("GET", f"/api/profiles/{profile_id}", None), ("PUT", f"/api/profiles/{profile_id}", PROFILE),
            ("POST", f"/api/profiles/{profile_id}/suspend", {}),
            ("GET", "/api/accounts", None), ("GET", "/api/accounts/admin", None),
            ("POST", "/api/accounts", {}), ("PUT", "/api/accounts/admin", {}),
        ):
            self.assertEqual(customer.open(path, method=method, json=body).status_code, 403)
        self.assertEqual(self.client.get("/api/accounts/admin", headers={"X-Admin-Id": "customer"}).status_code, 200)
        for role, permissions in (("admin", ["projects:manage"]), ("customer", ADMIN_PERMISSIONS)):
            self.repository.update_profile(UserProfile(profile_id, "Restricted", role, permissions))
            self.assertEqual(customer.get("/api/profiles").status_code, 403)
        self.connection.execute("UPDATE user_accounts SET status='Suspended' WHERE account_id='admin'")
        self.assertEqual(self.client.get("/api/profiles").status_code, 403)

    def test_admin_self_lockout_protection(self):
        self.assertEqual(self.client.post("/api/profiles/admin-profile/suspend", json={}).status_code, 403)
        for data in ({"name": "Admin", "role": "customer", "permissions": ADMIN_PERMISSIONS},
                     {"name": "Admin", "role": "admin", "permissions": ["profiles:read"]}):
            self.assertEqual(self.client.put("/api/profiles/admin-profile", json=data).status_code, 403)
        profile_id = self.create_profile()["profileId"]
        data = {"username": "test.admin", "email": "admin@example.test", "profileId": profile_id}
        self.assertEqual(self.client.put("/api/accounts/admin", json=data).status_code, 403)
        self.assertEqual(self.repository.find_account("admin").profile_id, "admin-profile")

    def test_recheck_assignment_after_hashing(self):
        profile_id = self.create_profile()["profileId"]

        def suspend_during_hash(password):
            profile = self.repository.find_profile(profile_id)
            profile.status = "Suspended"
            self.repository.update_profile(profile)
            return self.password_hash

        with patch("backend.controllers.hash_password", side_effect=suspend_during_hash):
            response = self.client.post("/api/accounts", json=self.account_input(profile_id))
        self.assertEqual(response.status_code, 400)
        self.assertIsNone(self.repository.account_with_username("designer.one"))

    def test_database_reopen_keeps_records_and_hashes(self):
        profile = self.create_profile()
        account = self.create_account(profile["profileId"])
        # Recreate the application as if the backend process restarted.
        restarted = create_app(self.filename, DevelopmentContext("development", "admin")).test_client()
        self.assertEqual(restarted.get(f"/api/profiles/{profile['profileId']}").get_json(), profile)
        self.assertEqual(restarted.get(f"/api/accounts/{account['accountId']}").get_json(), account)
        self.assertTrue(verify_password(PASSWORD, self.repository.find_account(account["accountId"]).password_hash))

    def test_storage_errors_constraints_and_rollback(self):
        with self.assertLogs(self.app.logger, level="ERROR"):
            with patch.object(Repository, "create_profile", side_effect=sqlite3.OperationalError("private SQL details")):
                response = self.client.post("/api/profiles", json=PROFILE)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_json()["error"]["code"], "PERSISTENCE")
        self.assertNotIn("private SQL", response.get_data(as_text=True))
        self.assertIsNone(self.repository.profile_with_name(PROFILE["name"]))
        with self.assertRaises(sqlite3.IntegrityError):
            self.repository.create_account(UserAccount("bad", "bad.user", "bad@example.test", self.password_hash, "missing"))
        with self.assertRaises(ValueError):
            with self.repository.transaction():
                self.repository.create_profile(UserProfile("rollback", "Rollback", "customer", ["projects:discover"]))
                raise ValueError("cancel transaction")
        self.assertIsNone(self.repository.find_profile("rollback"))

    def test_request_errors_and_development_only_context(self):
        for environment in ("production", "test"):
            with self.assertRaises(ValueError):
                DevelopmentContext(environment)
        self.assertEqual(self.client.post("/api/profiles", data="{", content_type="application/json").status_code, 400)
        self.assertEqual(self.client.post("/api/profiles", json=PROFILE, headers={"Origin": "https://attacker.example"}).status_code, 403)
        self.assertEqual(self.client.get("/api/accounts?name=user").status_code, 400)
        self.assertEqual(self.client.post("/api/accounts/admin/suspend", json={}).status_code, 404)


if __name__ == "__main__":
    unittest.main()
