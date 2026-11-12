# Atelier Match — CSIT314

Interior design project discovery and management platform with a React/TypeScript
frontend and a shared Flask/SQLite backend. The application supports User Admin,
Interior Designer, Customer and Platform Manager accounts across US01–US48.

## Requirements

- Python 3.11 or newer. GitHub Actions uses Python 3.12.
- Node.js 22.12 or newer.

## Setup

Run these commands from the project root:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
npm.cmd ci
.venv\Scripts\python.exe -m backend.app --create-admin
```

The final command creates an administrator without overwriting existing accounts.
Passwords require at least 6 characters and at most 72 UTF-8 bytes.

## Run the application

```powershell
npm.cmd run dev
```

Vite starts the Python backend automatically. Open http://127.0.0.1:5173/login.
The frontend proxies `/api` requests to the backend at http://127.0.0.1:3002.

To serve the production build and API together:

```powershell
npm.cmd run build
.venv\Scripts\python.exe -m backend.app --serve-ui
```

Open http://127.0.0.1:3002/login. `python app.py` uses the same backend entry point.

## Accounts and permissions

Sign in as the administrator, create user profiles, then assign accounts to them.
A profile must exist before an account can be created. The shared login page
uses the account's server-side role and permissions.

- Interior Designers need `projects:manage` to manage Current and Past projects.
- Customers need `projects:discover` to save and access their private favourites.
- Platform Managers need `categories:manage` for categories and `reports:read` for reports.

Public project discovery and details are available without login. Keyword,
category and style filters combine with AND. Saving a favourite is idempotent.
Company information is optional when creating a project.

## Storage and configuration

The default database is `data/atelier_match.sqlite`. Startup initializes the
schema when needed. Accounts, sessions, companies, projects, images, categories,
favourites and activity records are stored in SQLite. Sessions expire after eight
hours. Reports use calendar periods in Asia/Makassar and aggregate project
creation and view events.

Set `PORT`, `DATABASE_PATH`, `APP_ORIGIN` and `COOKIE_SECURE` when configuring
another environment. Use `COOKIE_SECURE=1` when serving over HTTPS.

## Project structure

```text
backend/app.py                       Application factory, request middleware and CLI
backend/boundary.py                  HTTP routes
backend/controllers.py               Use-case controllers and access checks
backend/models.py                    Domain models
backend/database.py                  SQLite connections and repositories
backend/schema.sql                   Schema and reporting triggers
backend/validation.py                Input, password and image validation
backend/generate_large_scale_data.py  Bulk sample-data generation
src/admin/                           Profile and account management
src/auth.tsx                         Authentication and company management
src/projects/                        Designer project management and catalogue
src/customer/                        Discovery, details and favourites
src/manager/                         Categories and reports
tests/test_all.py                    Legacy scenario suite and data-generation test
TestRunner.py                        Grouped terminal test report
```

Request flow: React → Flask routes → controllers → repositories → SQLite.
Role, permission and ownership checks are enforced by the backend.

## Tests

```powershell
npm.cmd test
npm.cmd run test:unit
npm.cmd run build
```

Use `npm test` in CMD, macOS or Linux. In PowerShell, `npm.cmd` avoids the
`npm.ps1` execution-policy restriction. The test scripts select the Windows
`.venv` interpreter when available, otherwise `python` from PATH.

The existing suite contains 106 legacy user-story scenarios and one bulk-data
test. The scenario methods currently use placeholder assertions, so their PASS
status alone does not establish feature correctness. Tests use temporary databases.

## Development identity

```powershell
.venv\Scripts\python.exe -m backend.app --dev --seed
.venv\Scripts\python.exe -m backend.app --dev
```

Development mode uses a fixed administrator identity and cannot demonstrate real
login/logout. It is disabled when `APP_ENV` or `NODE_ENV` is `production`.
Use `--create-admin` and start without `--dev` to test real authentication.
