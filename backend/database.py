"""Database connection, transactions, and repositories for Interior Designer Platform."""

import contextlib
import json
import sqlite3
import time
import hashlib
from datetime import datetime, timezone
from pathlib import Path

from backend.models import (
    CompanyInformation,
    InteriorDesignProject,
    IDPCategory,
    Favourite,
    ProjectView,
    Report,
    ReportPeriod,
    UserAccount,
    UserProfile,
    utc_timestamp,
)
from backend.validation import normalize


def token_hash(token: str) -> str:
    """SHA-256 hash for session security tokens."""
    return hashlib.sha256(token.encode()).hexdigest()


def connect_database(filename: str) -> sqlite3.Connection:
    """Connect to SQLite database with foreign keys and strict constraints enabled."""
    connection = sqlite3.connect(filename, timeout=30.0)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA foreign_keys = ON;")
        connection.execute("PRAGMA journal_mode = WAL;")
        connection.execute("PRAGMA busy_timeout = 30000;")
    except sqlite3.OperationalError:
        pass
    connection.create_function("normalize", 1, normalize)
    connection.create_function("clean", 1, lambda x: str(x).strip())
    connection.create_function("utc_timestamp", 1, utc_timestamp)
    return connection


def initialize_database(filename: str) -> None:
    """Initialize the database tables and reporting triggers."""
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


# 1. Base Repository: User Profiles and Accounts (US01..US10)
class Repository:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    # Shared infrastructure for US01-US48: commit related writes together or roll them back on failure.
    @contextlib.contextmanager
    def transaction(self):
        cursor = self.connection.cursor()
        cursor.execute("BEGIN IMMEDIATE;")
        try:
            yield cursor
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise

    # US05 - Search User Profiles: load profiles and filter them by name.
    def list_profiles(self, query: str = "") -> list[UserProfile]:
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM user_profiles ORDER BY name_key, profile_id;")
        keyword = normalize(query)
        return [p for r in cursor.fetchall() if (p := read_profile(r)) is not None
                and (not keyword or keyword in p.name.casefold())]

    # US02 - View User Profile; also retrieve the profile used by access checks.
    def profile_with_id(self, profile_id: str) -> UserProfile | None:
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM user_profiles WHERE profile_id = ?;", (profile_id,))
        return read_profile(cursor.fetchone())

    find_profile = profile_with_id

    # US01, US03 - Look up profile names to support duplicate-name validation.
    def profile_with_name(self, name: str) -> UserProfile | None:
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM user_profiles WHERE name_key = ?;", (normalize(name),))
        return read_profile(cursor.fetchone())

    # US01 - Create User Profile: persist its role, permissions, and status.
    def create_profile(self, profile: UserProfile) -> None:
        cursor = self.connection.cursor()
        cursor.execute(
            """INSERT INTO user_profiles (profile_id, name, name_key, role, permissions_json, status)
               VALUES (?, ?, ?, ?, ?, ?);""",
            (profile.profile_id, profile.name, normalize(profile.name), profile.role,
             json.dumps(profile.permissions), profile.status),
        )

    # US03, US04 - Persist profile changes, including suspension status.
    def update_profile(self, profile: UserProfile) -> None:
        cursor = self.connection.cursor()
        cursor.execute(
            """UPDATE user_profiles
               SET name = ?, name_key = ?, role = ?, permissions_json = ?, status = ?
               WHERE profile_id = ?;""",
            (profile.name, normalize(profile.name), profile.role, json.dumps(profile.permissions),
             profile.status, profile.profile_id),
        )

    # US10 - Search User Accounts: load accounts for controller-side keyword filtering.
    def list_accounts(self) -> list[UserAccount]:
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM user_accounts ORDER BY username_key, account_id;")
        return [a for r in cursor.fetchall() if (a := read_account(r)) is not None]

    # US07 - View User Account; also resolve accounts for authenticated access.
    def account_with_id(self, account_id: str) -> UserAccount | None:
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM user_accounts WHERE account_id = ?;", (account_id,))
        return read_account(cursor.fetchone())

    find_account = account_with_id

    # US06, US08 - Check username uniqueness; US11, US18, US35, US47 - Find the login account.
    def account_with_username(self, username: str) -> UserAccount | None:
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM user_accounts WHERE username_key = ?;", (normalize(username),))
        return read_account(cursor.fetchone())

    # US06, US08 - Check email uniqueness; US11, US18, US35, US47 - Support email login.
    def account_with_email(self, email: str) -> UserAccount | None:
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM user_accounts WHERE email_key = ?;", (normalize(email),))
        return read_account(cursor.fetchone())

    # US06 - Create User Account: store the password hash and assigned profile.
    def create_account(self, account: UserAccount) -> None:
        cursor = self.connection.cursor()
        cursor.execute(
            """INSERT INTO user_accounts (account_id, username, username_key, email, email_key,
                                          password_hash, profile_id, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?);""",
            (account.account_id, account.username, normalize(account.username),
             account.email, normalize(account.email), account.password_hash,
             account.profile_id, account.status),
        )

    # US08, US09 - Persist account details and status; session revocation is handled separately.
    def update_account(self, account: UserAccount) -> None:
        cursor = self.connection.cursor()
        cursor.execute(
            """UPDATE user_accounts
               SET username = ?, username_key = ?, email = ?, email_key = ?,
                   password_hash = ?, profile_id = ?, status = ?
               WHERE account_id = ?;""",
            (account.username, normalize(account.username),
             account.email, normalize(account.email), account.password_hash,
             account.profile_id, account.status, account.account_id),
        )


# 2. Company & Session Repository (US11..US19, US35..US36, US47..US48)
class CompanyRepository:
    def __init__(self, repository):
        self.connection = repository.connection

    # US11, US18, US35, US47 - Resolve an unexpired session for authenticated requests.
    def session(self, token):
        if not token:
            return None
        return self.connection.execute(
            'SELECT * FROM auth_sessions WHERE token_hash=? AND expires_at>?',
            (token_hash(token), int(time.time())),
        ).fetchone()

    # US12, US19, US36, US48 - Log out by deleting the stored session.
    def remove_session(self, token):
        self.connection.execute('DELETE FROM auth_sessions WHERE token_hash=?', (token_hash(token),))

    # US11, US18, US35, US47 - Store a hashed session token with an eight-hour expiry.
    def create_session(self, token, account_id, csrf):
        self.connection.execute('DELETE FROM auth_sessions WHERE expires_at<=?', (int(time.time()),))
        self.connection.execute('INSERT INTO auth_sessions VALUES (?, ?, ?, ?)',
                                (token_hash(token), account_id, csrf, int(time.time()) + 28800))

    # US09 - Suspend User Account and revoke all of its existing sessions.
    def suspend_account(self, account_id):
        self.connection.execute("UPDATE user_accounts SET status='Suspended' WHERE account_id=?", (account_id,))
        self.connection.execute('DELETE FROM auth_sessions WHERE account_id=?', (account_id,))

    # US14, US17 - Retrieve the designer-owned company for viewing or controller-side searching.
    def company(self, owner_id):
        row = self.connection.execute('SELECT * FROM companies WHERE owner_id=?', (owner_id,)).fetchone()
        return CompanyInformation(**dict(row)).to_dict() if row else None

    # US13 - Create Company Profile: associate company information with its designer.
    def create_company(self, company_id, owner_id, values):
        self.connection.execute('INSERT INTO companies VALUES (?, ?, ?, ?, ?, ?, ?)',
            (company_id, owner_id, values['name'], values['regNumber'], values['address'], values['contact'], values['description']))

    # US15 - Update Company Information using both company ID and owner ID.
    def update_company(self, company_id, owner_id, values):
        self.connection.execute('UPDATE companies SET name=?, reg_number=?, address=?, contact=?, description=? WHERE company_id=? AND owner_id=?',
            (values['name'], values['regNumber'], values['address'], values['contact'], values['description'], company_id, owner_id))

    # US16 - Delete Company Information belonging to the specified designer.
    def delete_company(self, company_id, owner_id):
        self.connection.execute('DELETE FROM companies WHERE company_id=? AND owner_id=?', (company_id, owner_id))


# 3. Project & Image Repository (US20..US31)
class ProjectRepository:
    def __init__(self, repository):
        self.connection = repository.connection

    # US20, US22, US25, US27, US30 - Supply category choices for project forms and discovery filters.
    def categories(self):
        return [dict(categoryId=r['category_id'], name=r['name'], description=r['description'], status=r['status'])
                for r in self.connection.execute('SELECT * FROM project_categories ORDER BY name')]

    # US20, US22, US25, US27 - Retrieve category status for controller-side project validation.
    def category(self, category_id):
        return self.connection.execute('SELECT * FROM project_categories WHERE category_id=?', (category_id,)).fetchone()

    # US20, US22, US25, US27 - Link a project to its designer company when one exists.
    def company_id(self, owner):
        row = self.connection.execute('SELECT company_id FROM companies WHERE owner_id=?', (owner,)).fetchone()
        return row[0] if row else None

    # US21, US26, US30, US31, US33, US34 - Build project results with category, designer, company, and image URLs.
    def serialize(self, row):
        if row is None:
            return None
        keys = InteriorDesignProject.__dataclass_fields__
        result = InteriorDesignProject(**{k: row[k] for k in keys}).to_dict()
        result.update(categoryName=row['category_name'], categoryStatus=row['category_status'],
                      companyName=row['company_name'], designerName=row['username'])
        result['images'] = [dict(imageId=r['image_id'], url='/api/project-images/' + r['image_id'])
                            for r in self.connection.execute('SELECT image_id FROM project_images WHERE project_id=? ORDER BY position', (row['project_id'],))]
        return result

    SELECT = '''SELECT p.*, c.name AS category_name, c.status AS category_status,
                       co.name AS company_name, a.username
                FROM interior_design_projects p
                JOIN project_categories c ON c.category_id=p.category_id
                JOIN user_accounts a ON a.account_id=p.owner_account_id
                JOIN user_profiles up ON up.profile_id=a.profile_id
                LEFT JOIN companies co ON co.company_id=p.company_id'''
    VISIBLE = "a.status='Active' AND up.status='Active' AND up.role='designer' AND EXISTS (SELECT 1 FROM json_each(up.permissions_json) permission WHERE permission.value='projects:manage')"

    # US21, US26, US31 - Retrieve project details; owner/public filters also support update, delete, and favourite checks.
    def find(self, project_id, owner=None, status=None, public=False):
        clauses, args = ['p.project_id=?'], [project_id]
        if owner is not None:
            # US21, US23, US26, US28: Restrict single project retrieval to project owner
            clauses.append('p.owner_account_id=?'); args.append(owner)
        if status is not None:
            clauses.append('p.status=?'); args.append(status)
        if public:
            clauses.append(self.VISIBLE)
        return self.serialize(self.connection.execute(self.SELECT + ' WHERE ' + ' AND '.join(clauses), args).fetchone())

    # US24, US29, US30, US33, US34 - Search designer projects, the public catalog, or a customer favourite list.
    def search(self, status=None, owner=None, query='', category_id='', public=False, style='', favourite_customer=None):
        clauses, args = ['1=1'], []
        for column, value in [('p.status', status), ('p.owner_account_id', owner), ('p.category_id', category_id or None)]:
            if value is not None:
                # Feature: Project Ownership Isolation (US20–US29)
                # Ensures each designer only accesses projects belonging to their own account
                clauses.append(column + '=?'); args.append(value)
        if public:
            clauses.append(self.VISIBLE)
        if favourite_customer is not None:
            # Feature: Private Favourites Shortlist (US32–US34)
            # Restricts results to projects bookmarked by the authenticated customer
            clauses.append('EXISTS (SELECT 1 FROM favourites f WHERE f.project_id=p.project_id AND f.customer_account_id=?)')
            args.append(favourite_customer)
        rows = self.connection.execute(self.SELECT + ' WHERE ' + ' AND '.join(clauses) + ' ORDER BY p.created_at DESC, p.project_id', args).fetchall()
        keyword = normalize(query)
        selected_style = normalize(style)
        return [self.serialize(r) for r in rows
                if (not selected_style or normalize(r['style']) == selected_style)
                and keyword in normalize(' '.join(r[k] or '' for k in ('title','description','style','category_name','company_name')))]

    # US30 - Search Catalog IDPs: supply distinct styles from publicly visible projects.
    def styles(self):
        rows = self.connection.execute(self.SELECT + ' WHERE ' + self.VISIBLE + ' ORDER BY p.style,p.project_id').fetchall()
        unique = {}
        for r in rows:
            unique.setdefault(normalize(r['style']), r['style'])
        return sorted(unique.values())

    # US20, US25 - Create projects; US22, US27 - Update projects and replace their stored images.
    def save(self, project, images, new=False):
        if new:
            self.connection.execute('''INSERT INTO interior_design_projects
                (project_id,owner_account_id,company_id,title,description,category_id,style,status,created_at,updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?)''',
                (project.project_id, project.owner_account_id, project.company_id, project.title,
                 project.description, project.category_id, project.style, project.status, project.created_at, project.updated_at))
        else:
            self.connection.execute('''UPDATE interior_design_projects SET
                company_id=?,title=?,description=?,category_id=?,style=?,status=?,updated_at=? WHERE project_id=?''',
                (project.company_id, project.title, project.description, project.category_id,
                 project.style, project.status, project.updated_at, project.project_id))
        self.connection.execute('DELETE FROM project_images WHERE project_id=?', (project.project_id,))
        for image in images:
            self.connection.execute('INSERT INTO project_images VALUES (?,?,?,?,?)',
                (image.image_id, project.project_id, image.position, image.mime_type, image.content))

    # US23, US28 - Delete a Current or Past project after controller ownership checks.
    def delete(self, project_id):
        self.connection.execute('DELETE FROM interior_design_projects WHERE project_id=?', (project_id,))

    # US21, US26, US31 - Retrieve image bytes and MIME type for project displays.
    def image(self, image_id):
        row = self.connection.execute('SELECT mime_type, content FROM project_images WHERE image_id=?', (image_id,)).fetchone()
        return (row['mime_type'], row['content']) if row else None


# 4. IDP Category Repository (US39..US43)
class CategoryRepository:
    def __init__(self, repository):
        self.connection = repository.connection

    @staticmethod
    def entity(row):
        return IDPCategory(row['category_id'], row['name'], row['description'], row['status'],
                           row['created_at'], row['updated_at'], row['deleted_at']) if row else None

    # US40 - View IDP Category: retrieve a category that has not been soft-deleted.
    def find(self, category_id):
        return self.entity(self.connection.execute(
            'SELECT * FROM project_categories WHERE category_id=? AND deleted_at IS NULL', (category_id,)).fetchone())

    # US43 - Search IDP Categories by normalized name or description.
    def search(self, query):
        return [self.entity(row).to_dict() for row in self.connection.execute('''
            SELECT * FROM project_categories WHERE deleted_at IS NULL
            AND instr(normalize(name || ' ' || description),?)>0 ORDER BY name_key,category_id
        ''', (normalize(query),))]

    # US39, US41 - Support duplicate category-name checks before creation or update.
    def duplicate(self, name, excluding=None):
        return self.connection.execute('SELECT 1 FROM project_categories WHERE name_key=? AND category_id<>?',
                                       (normalize(name), excluding or '')).fetchone() is not None

    # US39, US41, US42 - Create, update, or soft-delete a category by persisting deleted_at.
    def save(self, category, new=False):
        if new:
            self.connection.execute('''INSERT INTO project_categories
                (category_id,name,description,status,name_key,created_at,updated_at,deleted_at) VALUES (?,?,?,?,?,?,?,?)''',
                (category.categoryId, category.name, category.description, category.status, normalize(category.name),
                 category.createdAt, category.updatedAt, category.deletedAt))
        else:
            self.connection.execute('''UPDATE project_categories SET name=?,name_key=?,description=?,status=?,
                updated_at=?,deleted_at=? WHERE category_id=?''',
                (category.name, normalize(category.name), category.description, category.status,
                 category.updatedAt, category.deletedAt, category.categoryId))


# 5. Customer Favourite Repository (US32..US34, US38)
class FavouriteRepository:
    def __init__(self, repository):
        self.connection = repository.connection

    # US30-US34 - Retrieve customer-owned favourite records for saved markers and shortlist metadata.
    def list_for_customer(self, customer_id):
        return [Favourite(**dict(row)) for row in self.connection.execute(
            'SELECT * FROM favourites WHERE customer_account_id=? ORDER BY created_at DESC,project_id', (customer_id,))]

    # US32 - Add IDP to Favourite List: ignore repeated saves of the same customer/project pair.
    def add(self, favourite):
        cursor = self.connection.execute(
            '''INSERT INTO favourites(customer_account_id,project_id,created_at) VALUES (?,?,?)
               ON CONFLICT(customer_account_id,project_id) DO NOTHING''',
            (favourite.customer_account_id, favourite.project_id, favourite.created_at))
        return cursor.rowcount == 1

    # US31, US32 - Check whether a project is already saved by this customer.
    def exists(self, customer_id, project_id):
        row = self.connection.execute(
            'SELECT 1 FROM favourites WHERE customer_account_id=? AND project_id=?',
            (customer_id, project_id)
        ).fetchone()
        return row is not None

    # US32 - Retrieve the saved favourite and its original creation timestamp.
    def find(self, customer_id, project_id):
        row = self.connection.execute('SELECT * FROM favourites WHERE customer_account_id=? AND project_id=?', (customer_id, project_id)).fetchone()
        return Favourite(**dict(row)) if row else None

    # US38 - View Project Shortlist Counts: count favourites for each requested project.
    def count_by_project(self, project_ids):
        if not project_ids:
            return {}
        placeholders = ','.join('?' for _ in project_ids)
        rows = self.connection.execute(
            f'SELECT project_id, COUNT(*) FROM favourites WHERE project_id IN ({placeholders}) GROUP BY project_id',
            tuple(project_ids)
        ).fetchall()
        return {row[0]: row[1] for row in rows}

    countByProject = count_by_project


class ProjectActivityAdapter:
    view_tracking_available = True
    def __init__(self, repository):
        self.connection = repository.connection
    # US38 - Provide the favourite count for a single project through the activity adapter.
    def shortlist_count(self, project_id):
        return self.connection.execute('SELECT COUNT(*) FROM favourites WHERE project_id=?', (project_id,)).fetchone()[0]


# 6. Activity Analytics Repository (US31, US37, US38)
class ActivityRepository:
    def __init__(self, repository):
        self.connection = repository.connection

    # US31, US37 - Record project view events once per project/event ID for view analytics.
    def record(self, event):
        return self.connection.execute(
            'INSERT INTO project_views VALUES (?,?,?) ON CONFLICT(project_id,event_id) DO NOTHING',
            (event.project_id, event.event_id, event.occurred_at)).rowcount == 1

    # US37, US38 - Return view and shortlist counts restricted to the designer-owned projects.
    def counts(self, owner, project_id=None):
        return [dict(row) for row in self.connection.execute('''
            SELECT p.project_id AS projectId,p.title,p.status,
              (SELECT COUNT(*) FROM project_views v WHERE v.project_id=p.project_id) AS views,
              (SELECT COUNT(*) FROM favourites f WHERE f.project_id=p.project_id) AS shortlists
            FROM interior_design_projects p WHERE p.owner_account_id=?
            AND (? IS NULL OR p.project_id=?) ORDER BY p.created_at DESC,p.project_id
        ''', (owner, project_id, project_id))]


# 7. Platform Report Repository and Service (US44..US46)
class ReportRepository:
    def __init__(self, repository):
        self.connection = repository.connection

    # US44-US46 - Count report events within the requested time interval and return retention coverage.
    def aggregate(self, start, end):
        rows = self.connection.execute('''SELECT c.retained_since,e.kind,COUNT(e.event_key) AS total
            FROM report_coverage c LEFT JOIN report_events e ON e.occurred_at>=? AND e.occurred_at<?
            GROUP BY c.retained_since,e.kind''', (start, end)).fetchall()
        return {r['kind']: r['total'] for r in rows if r['kind']}, rows[0]['retained_since']


class ReportService:
    def __init__(self, store):
        self.store = store

    # US44 - Daily Report; US45 - Weekly Report; US46 - Monthly Report: build metrics for the calendar period.
    def generate(self, kind, value, now=None):
        period = ReportPeriod.parse(kind, value)
        now = now or datetime.now(timezone.utc)
        start, end = utc_timestamp(period.start.isoformat()), utc_timestamp(period.end.isoformat())
        cutoff = min(period.end, now)
        counts, retained_since = self.store.aggregate(start, utc_timestamp(cutoff.isoformat()))
        metrics = {
            'projectsCreated': counts.get('project_created', 0),
            'projectViews': counts.get('project_view', 0),
        }
        return {
            'kind': kind, 'period': value,
            'start': period.start.isoformat(), 'end': period.end.isoformat(),
            'partial': now < period.end, 'retainedSince': retained_since,
            'metrics': metrics,
        }
