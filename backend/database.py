"""Repository: all SQL stays here, not in React or the controllers."""

from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3

from backend.models import UserAccount, UserProfile
from backend.validation import normalize, clean
from backend.report_service import utc_timestamp


def connect_database(filename: str) -> sqlite3.Connection:
    Path(filename).parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(filename, timeout=5, isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.create_function('normalize', 1, normalize, deterministic=True)
    connection.create_function('clean', 1, clean, deterministic=True)
    connection.create_function('utc_timestamp', 1, utc_timestamp, deterministic=True)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(filename: str) -> None:
    connection = connect_database(filename)
    try:
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        if version > 6:
            raise RuntimeError("Database version is newer than this application.")
        if version < 6:
            schema = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
            connection.executescript("BEGIN IMMEDIATE;\n" + schema + "\nCOMMIT;")
    finally:
        connection.close()


def read_profile(row: sqlite3.Row | None) -> UserProfile | None:
    if row is None:
        return None
    return UserProfile(row["profile_id"], row["name"], row["role"],
                       json.loads(row["permissions_json"]), row["status"])


def read_account(row: sqlite3.Row | None) -> UserAccount | None:
    if row is None:
        return None
    return UserAccount(row["account_id"], row["username"], row["email"],
                       row["password_hash"], row["profile_id"], row["status"])


class Repository:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    @contextmanager
    def transaction(self):
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            yield
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise

    def find_profile(self, profile_id: str) -> UserProfile | None:
        row = self.connection.execute(
            "SELECT * FROM user_profiles WHERE profile_id = ?", (profile_id,)
        ).fetchone()
        return read_profile(row)

    def profile_with_name(self, name: str) -> UserProfile | None:
        row = self.connection.execute(
            "SELECT * FROM user_profiles WHERE name_key = ?", (normalize(name),)
        ).fetchone()
        return read_profile(row)

    def search_profiles(self, name: str) -> list[UserProfile]:
        rows = self.connection.execute(
            "SELECT * FROM user_profiles WHERE instr(name_key, ?) > 0 ORDER BY name_key, profile_id",
            (normalize(name),),
        ).fetchall()
        return [read_profile(row) for row in rows]

    def create_profile(self, profile: UserProfile) -> None:
        self.connection.execute(
            "INSERT INTO user_profiles (profile_id, name, name_key, role, permissions_json, status) VALUES (?, ?, ?, ?, ?, ?)",
            (profile.profile_id, profile.name, normalize(profile.name), profile.role,
             json.dumps(profile.permissions), profile.status),
        )

    def update_profile(self, profile: UserProfile) -> None:
        self.connection.execute(
            "UPDATE user_profiles SET name=?, name_key=?, role=?, permissions_json=?, status=? WHERE profile_id=?",
            (profile.name, normalize(profile.name), profile.role,
             json.dumps(profile.permissions), profile.status, profile.profile_id),
        )

    def find_account(self, account_id: str) -> UserAccount | None:
        row = self.connection.execute(
            "SELECT * FROM user_accounts WHERE account_id = ?", (account_id,)
        ).fetchone()
        return read_account(row)

    def account_with_username(self, username: str) -> UserAccount | None:
        row = self.connection.execute(
            "SELECT * FROM user_accounts WHERE username_key = ?", (normalize(username),)
        ).fetchone()
        return read_account(row)

    def account_with_email(self, email: str) -> UserAccount | None:
        row = self.connection.execute(
            "SELECT * FROM user_accounts WHERE email_key = ?", (normalize(email),)
        ).fetchone()
        return read_account(row)

    def list_accounts(self) -> list[UserAccount]:
        rows = self.connection.execute("SELECT * FROM user_accounts ORDER BY username_key, account_id").fetchall()
        return [read_account(row) for row in rows]

    def create_account(self, account: UserAccount) -> None:
        self.connection.execute(
            "INSERT INTO user_accounts (account_id, username, username_key, email, email_key, password_hash, profile_id, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (account.account_id, account.username, normalize(account.username), account.email,
             normalize(account.email), account.password_hash, account.profile_id, account.status),
        )

    def update_account(self, account: UserAccount) -> None:
        # US08 must not change the password hash or account status.
        self.connection.execute(
            "UPDATE user_accounts SET username=?, username_key=?, email=?, email_key=?, profile_id=? WHERE account_id=?",
            (account.username, normalize(account.username), account.email,
             normalize(account.email), account.profile_id, account.account_id),
        )
