# CSIT314 - Members 1, 2 and 3

React/TypeScript frontend with a shared Python Flask + SQLite backend. Member 1 implements US01-08; Member 2 implements account search/suspension, shared login/logout and company management; Member 3 implements US20-29 Current/Past project CRUD, search and image storage. Customer discovery reads the same project database. Favourite persistence, analytics activity and category management remain integration work for their respective members.

## Setup

Requires Python 3.11+ and Node.js 22.12+:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
npm.cmd ci
.venv\Scripts\python.exe -m backend.app --create-admin
```

The last command asks for a username, email and password. It creates a new administrator without overwriting existing accounts. Passwords require at least 12 characters and at most 72 UTF-8 bytes.

## Run with real login

Backend:

```powershell
.venv\Scripts\python.exe -m backend.app
```

Frontend, in another terminal:

```powershell
npm.cmd run dev
```

Open http://127.0.0.1:5173/login. Sign in as the administrator, create the required UserProfiles with their roles/permissions, and create accounts assigned to those profiles. Each account can then sign in through the same login page. Designers need the designer role and projects:manage permission to manage `/designer/current` and `/designer/past`. Company information, projects and uploaded images save to SQLite. A company is optional for project creation.

Alternatively, serve the built frontend and API together:

```powershell
npm.cmd run build
.venv\Scripts\python.exe -m backend.app --serve-ui
```

Open http://127.0.0.1:3001/login. `python app.py` delegates to the same backend entry point. Set `PORT`, `DATABASE_PATH`, `APP_ORIGIN`, and `COOKIE_SECURE=1` as appropriate for another origin or HTTPS environment.

The database is `data/member1.sqlite`. Startup or `python -m backend.app --init` migrates existing data to version 3, preserving accounts, profiles, company records and sessions. Project/image/category tables are added without resetting data. Install the updated requirements (including Pillow for server image validation) before starting. Sessions and project/image records survive server restart; session expiry is eight hours.

## Structure

```text
backend/app.py                  HTTP Boundary and session/access middleware
backend/controllers.py          Member 1 Controls and effective_access
backend/member2.py              Member 2 Controls
backend/models.py               UserProfile, UserAccount, CompanyInformation Entities
backend/database.py             Member 1 Repository and schema migrations
backend/member2_repository.py   Company/session Repository
backend/schema.sql              Existing Member 1 schema
backend/member2.sql             Version 2 migration
backend/project_boundary.py     Member 3 HTTP routes and shared read adapters
backend/project_controllers.py  Ten Current/Past project use cases
backend/project_entity.py       InteriorDesignProject entity
backend/project_repository.py   Shared project/category/image SQL
backend/project_validation.py   Project and actual image validation
backend/member3.sql             Version 3 migration
backend/validation.py           Shared validation and bcrypt helpers
src/member1/                    Admin profile/account screens and API adapter
src/member2.tsx                 Shared auth, route guards, company management
src/member3/                    Project forms/details and live catalog adapters
```

Flow: React -> Flask Boundary -> Control -> Repository -> SQLite. Displays and confirmations stay in the frontend. Server-side roles and ownership determine access.

## Tests

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
npm.cmd run build
npm.cmd exec playwright install chromium
$env:PYTHON = (Resolve-Path '.venv\Scripts\python.exe').Path
npm.cmd run test:e2e
npm.cmd run test:e2e:member2
npm.cmd run test:e2e:member3
```

Backend and browser tests use disposable databases. `PYTHON` selects the browser harness interpreter. On machines where `python` resolves to a Windows Store alias, use an installed interpreter explicitly. The pgAdmin embedded Python available in the audit environment can execute tests but does not provide the standard `venv` module.

## Development-only identity

For Member 1 demonstration without real login:

```powershell
.venv\Scripts\python.exe -m backend.app --dev --seed
.venv\Scripts\python.exe -m backend.app --dev
```

`--dev` uses a fixed server-side admin identity and intentionally cannot demonstrate real logout. It is disabled when APP_ENV or NODE_ENV is production. Development seed passwords are random and unknown; use `--create-admin` for a login-capable administrator.

See [Member 3 stories, API, image policy and integration contracts](docs/MEMBER3.md), [Member 2 architecture](docs/MEMBER2.md), and [Member 1 coverage](docs/MEMBER1.md). The original UML/specification is not present; field limits, category lifecycle and public project visibility are documented implementation assumptions pending confirmation against the lecturer's documents.
