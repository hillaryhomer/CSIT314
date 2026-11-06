# Member 2 implementation

Member 4 now supplies private customer favourites through the same sessions and schema version 4. See [MEMBER4.md](MEMBER4.md) for current customer contracts and the shared logout/session race fixes.

Member 3 extends the same database to schema version 3; see [MEMBER3.md](MEMBER3.md) for project/image/category tables. The version 2 migration described here remains part of the migration chain.

US09–19, US35–36 and US47–48 use the same Flask application, `UserAccount`, `UserProfile`, bcrypt helpers and SQLite database as Member 1. `app.py` at the repository root delegates to `backend.app`; the old in-memory registration/company application and unused templates were removed.

## Architecture

- Boundary: `backend/app.py` accepts requests and returns JSON; React renders forms, details, errors and confirmations.
- Control: `backend/member2.py` validates requests, checks role/access, and coordinates transactions.
- Entity: `backend/models.py` contains `UserAccount`, `UserProfile`, and `CompanyInformation`. Company entities have no create method.
- Repository: `backend/member2_repository.py` contains session/company SQL. Account/profile persistence remains in `backend/database.py`.
- UI: `src/member2.tsx`, shared API adapter, and `src/member1/AdminManagement.tsx`.

No original UML or official field specification is present. Names and return types cannot be certified against a missing diagram.

## Authentication and access

Login accepts username or email, verifies the existing bcrypt hash, and checks both account and profile status. The server returns the role and permissions from the assigned profile. React uses that role for redirects and route guards; no browser role selector determines access.

The browser receives an opaque random cookie (`HttpOnly`, `SameSite=Strict`, eight-hour expiry). SQLite stores only its SHA-256 digest, account ID, expiry and CSRF token. The session survives refresh and server restart. Login rotates the current browser's session; logout deletes it from SQLite, so replaying the old cookie fails. Other browser sessions remain signed in until logout, expiry or account suspension.

Every protected request rechecks the latest account/profile state. Account suspension preserves the account and company, sets `Suspended`, and deletes all sessions for that account in the same transaction. Self-suspension is rejected. Profile suspension also blocks access on the next request, without changing account status.

Writes require JSON, an allowed Origin when supplied, and a matching `X-CSRF-Token` for real sessions. API responses use `Cache-Control: no-store`. `COOKIE_SECURE=1` enables HTTPS-only cookies for HTTPS hosting. Set `APP_ORIGIN` to the exact frontend origin if it differs from the default. Local `--serve-ui` defaults to the backend's own origin; separate Vite development defaults to `http://127.0.0.1:5173`.

`--dev` intentionally uses a fixed administrator identity for Member 1 development tests. It does not provide meaningful login/logout and is rejected in production environments. Run without `--dev` for real sessions.

## Company rules

One company per designer account. The owner always comes from the verified session, not submitted JSON. The API rejects unsupported fields including `companyId` and `ownerId`. Update/delete query by both company ID and the current owner. Another designer's ID returns 404.

Fields: company name (required, up to 120 characters), address (required, up to 500), contact details (required, up to 254), description (optional, up to 4000), and business registration number (optional, up to 80). These preserve existing fields; the registration number is not claimed as an official requirement. Values are normalized/trimmed and validated on the server. No particular national registration format is imposed.

Search compares the keyword against the current designer's own company fields. It returns that company plus a `matches` flag; it never returns another designer's company. The UI distinguishes an absent company, no keyword match, loading and failure. Cancel sends no mutation. Delete removes only the company row; there is no cascade to accounts or projects.

## API

| Method | Path | Result/access |
| --- | --- | --- |
| POST | `/api/auth/login` | `{identifier,password}` → account, role, permissions, CSRF token + cookie |
| GET | `/api/auth/session` | Current session/role from server |
| POST | `/api/auth/logout` | Deletes current session |
| GET | `/api/accounts?q=keyword` | Admin with `accounts:read`; array of accounts with profile/status and no credentials |
| POST | `/api/accounts/:id/suspend` | Admin with `accounts:write`; preserved account with Suspended status |
| GET | `/api/company?q=keyword` | Designer's own company or null, plus matches |
| POST | `/api/company` | Create current designer's company |
| PUT | `/api/company/:id` | Update owned company |
| DELETE | `/api/company/:id` | Delete owned company only |

All write endpoints except login require a JSON body, including `{}` for logout, suspend and delete. Errors preserve the Member 1 `{error:{code,message,fields}}` format. SQLite failures return 500 and transactions roll back.

## Migration and initial access

Startup adds version 2 tables (`auth_sessions`, `companies`) to an existing version 1 database. Account IDs, profiles, statuses and bcrypt hashes are preserved. The database remains `data/member1.sqlite` unless `DATABASE_PATH` is set. No application database was reset to implement this change.

Create a login-capable administrator interactively:

```powershell
python -m backend.app --create-admin
```

Passwords are entered with `getpass`, validated, hashed, and never printed. Existing usernames/emails are rejected; the command does not overwrite an existing account. Development seed administrators have random unknown passwords, so create your own administrator for real login. Then use the Member 1 admin screens to create the other accounts.

## Verification

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
npm.cmd run build
npm.cmd run test:e2e
npm.cmd run test:e2e:member2
```

Set `PYTHON` to a working interpreter for the browser harness if `python` is a Windows App Execution Alias. Browser fixtures are restricted to a disposable database in `.test-data`; their credentials are test-only.

Backend coverage includes all four roles, Member 1 account creation → real login, restart persistence, forged/expired sessions, CSRF and Origin rejection, ownership, immutable IDs, company CRUD/search, suspension of live sessions, suspended profiles, permission changes, logout-cookie replay, storage rollback, and migration from version 1. Browser coverage exercises company CRUD/cancel/retry, Member 1 account creation and search/suspension with a second browser session, role redirects and logout access denial.

Verified on 5 November 2026: 28 backend tests, 7 Member 1 browser tests and 3 Member 2 browser tests passed. TypeScript and the Vite production build passed. The browser harness owns and stops its Python process through IPC, avoiding a hanging Windows process-tree shutdown.

Member 3 now provides persistent project management and shared customer discovery. Favourite persistence, analytics activity, category CRUD and reports still depend on their respective members; this document does not claim those modules are complete.
