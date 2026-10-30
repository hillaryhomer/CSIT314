# CSIT314 - Member 1

The backend uses **Python + Flask + SQLite**. The existing React frontend remains in place so the visual presentation is unchanged. Scope: **US01-US08**, covering profile management and user-account creation, viewing, and updates.

## Structure

```text
backend/
  app.py          receives HTTP requests (Boundary)
  controllers.py  eight user-story controllers (Control)
  models.py       UserProfile and UserAccount (Entity)
  database.py     reads and writes SQLite data (Repository)
  validation.py   validates input and hashes passwords
  schema.sql      database tables
src/member1/      React screens and API calls
tests/            Python and browser tests
```

Data flow: **React Form -> Flask API -> Controller -> Repository -> SQLite**.

The backend contains five main Python files and English comments.

## Installation

Requires **Python 3.11+** and **Node.js 22.12+**. Run from the project folder:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
npm.cmd ci
.venv\Scripts\python.exe -m backend.app --dev --seed
```

The seed command creates the tables and development sample data once. It does not reset existing data. The database is stored in `data/member1.sqlite`. The schema, IDs, and existing bcrypt hashes remain compatible.

## Running

Terminal 1 - backend:

```powershell
.venv\Scripts\python.exe -m backend.app --dev
```

Terminal 2 - frontend:

```powershell
npm.cmd run dev
```

Open http://127.0.0.1:5173/admin/profiles or http://127.0.0.1:5173/admin/accounts.

The frontend forwards `/api` requests to Flask on port 3001. Data remains after refreshes and restarts. The role selector in the header changes the preview screen only.

## Testing

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
npm.cmd run build
npm.cmd exec playwright install chromium
$env:PYTHON = (Resolve-Path '.venv\Scripts\python.exe').Path
npm.cmd run test:e2e
```

`PYTHON` selects the interpreter used by the browser tests. Browser tests use a separate database, not the application data. See the [Member 1 checklist and results](docs/MEMBER1.md).

If `python --version` does not work, install standard Python or choose an available interpreter. Browser testing uses Python 3.13.12 through the environment that provides pgAdmin. The embedded interpreter does not include the `venv` module, so the standard `venv` instructions above require a standard Python installation.

## Scope Boundaries

Login/logout, account search, and account suspension remain Member 2 responsibilities. Development mode uses a server-side administrator identity for demonstration and is not real login. Without `--dev`, APIs reject access until Member 2 installs session checks. Development mode is rejected when `APP_ENV` or `NODE_ENV` is production.

The [Member 2 handoff](docs/MEMBER2_HANDOFF.md) explains repository usage, password hashes, and shared access checks. Other member pages remain previews.
