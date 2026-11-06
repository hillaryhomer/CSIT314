# CSIT314 - Members 1-6

React/TypeScript frontend with a shared Python Flask + SQLite backend. Member 1 implements US01-08; Member 2 implements account search/suspension, shared login/logout and company management; Member 3 implements US20-29 project management; Member 4 implements US30-34 keyword/category/style search, details and private persistent favourites. All features use the same accounts, sessions, projects and categories. Member 5 implements US37-38 persistent customer detail views and designer shortlist totals. Member 6 implements US39-46 shared category CRUD/search and calendar reports from retained project/view events.

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

Customers need the customer role and projects:discover permission to save and access `/favourites`. Public discovery/detail work without login. Keyword/category/style filters combine with AND and can be reset together. Saved is an add-only state, not a remove toggle.

Alternatively, serve the built frontend and API together:

```powershell
npm.cmd run build
.venv\Scripts\python.exe -m backend.app --serve-ui
```

Open http://127.0.0.1:3001/login. `python app.py` delegates to the same backend entry point. Set `PORT`, `DATABASE_PATH`, `APP_ORIGIN`, and `COOKIE_SECURE=1` as appropriate for another origin or HTTPS environment.

The database is `data/member1.sqlite`. Startup or `python -m backend.app --init` migrates existing data to version 6, preserving existing accounts, sessions, companies, projects, images and categories. Favourites have a unique customer/project pair constraint and survive refresh, restart and login again. Install requirements (including Pillow for image validation) before starting. Session expiry is eight hours.

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
backend/customer_boundary.py    Member 4 HTTP Boundary
backend/customer_controllers.py Five customer discovery/favourite use cases
backend/favourite_entity.py     Favourite relationship Entity
backend/favourite_repository.py Favourite Repository and shortlist-count adapter
backend/member4.sql             Version 4 migration
backend/validation.py           Shared validation and bcrypt helpers
src/member1/                    Admin profile/account screens and API adapter
src/member2.tsx                 Shared auth, route guards, company management
src/member3/                    Project forms/details and live catalog adapters
src/member4/                    Customer discovery, details, save and favourites
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
npm.cmd run test:e2e:member4
npm.cmd run test:e2e:member5
npm.cmd run test:e2e:member6
```

Backend and browser tests use disposable databases. `PYTHON` selects the browser harness interpreter. On machines where `python` resolves to a Windows Store alias, use an installed interpreter explicitly. The pgAdmin embedded Python available in the audit environment can execute tests but does not provide the standard `venv` module.

## Development-only identity

For Member 1 demonstration without real login:

```powershell
.venv\Scripts\python.exe -m backend.app --dev --seed
.venv\Scripts\python.exe -m backend.app --dev
```

`--dev` uses a fixed server-side admin identity and intentionally cannot demonstrate real logout. It is disabled when APP_ENV or NODE_ENV is production. Development seed passwords are random and unknown; use `--create-admin` for a login-capable administrator.

See [Member 4 customer APIs, privacy and integration contracts](docs/MEMBER4.md), [Member 3 project APIs](docs/MEMBER3.md), [Member 2 architecture](docs/MEMBER2.md), and [Member 1 coverage](docs/MEMBER1.md). The original UML/specification is not present; field limits, category lifecycle, visibility and shortlist metric policy are documented assumptions pending confirmation against the lecturer's/group documents. Plain GET retrieval remains side-effect free; customer detail openings use the Member 5 atomic recorder. See [Member 5 metrics, seed and verification](docs/MEMBER5.md).

See [Member 6 category policy, real reports, migration and verification](docs/MEMBER6.md). Reports use Asia/Makassar calendar periods and explicitly identify incomplete pre-migration history.
