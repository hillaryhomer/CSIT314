# Member 1 Checklist

All controllers are in **backend/controllers.py**. The API boundary is in backend/app.py, entities are in backend/models.py, and SQL/repository code is in backend/database.py. React screens remain in src/member1/AdminManagement.tsx.

| Story | Controller | Endpoint |
| --- | --- | --- |
| US01 Create profile | CreateUserProfileController | POST /api/profiles |
| US02 View profile | ViewUserProfileController | GET /api/profiles/:id |
| US03 Update profile | UpdateUserProfileController | PUT /api/profiles/:id |
| US04 Suspend profile | SuspendUserProfileController | POST /api/profiles/:id/suspend |
| US05 Search profile names | SearchUserProfileController | GET /api/profiles?name= |
| US06 Create account | CreateUserAccountController | POST /api/accounts |
| US07 View account | ViewUserAccountController | GET /api/accounts/:id |
| US08 Update account | UpdateUserAccountController | PUT /api/accounts/:id |

`GET /api/accounts` lists records only; it is not Member 1 account-search functionality. Account suspension, deletion, password reset, and reactivation were not added.

## Reading the Code

1. Start with routes in app.py: React input is received there.
2. Inspect the controller for each story: check permissions, validation, and business rules.
3. Inspect the Repository: SQL uses parameters, foreign keys, and transactions.
4. Inspect models.py: public JSON is returned without password hashes.

Shared validation is in validation.py. The old TypeScript, Express, bcryptjs, tsx, and concurrently backend was removed. No additional abstract repository, service factory, or UnitOfWork interface was added. The database and old JSON format remain compatible so existing screens and data are not broken.

## Testing

Backend tests use Python unittest in tests/test_member1.py. Browser tests in tests/browser/member1.spec.ts use Flask and a dedicated test database.

Coverage includes the eight stories, validation, duplicate checks, profile renaming, account relationships, password hashing, suspension, administrator access, lockout prevention, storage/error transactions, database restart, and compatibility with hashes from the previous JavaScript backend. Browser tests cover reload, cancel, retry, duplicate submission, inline errors, stale assignments, and mobile layout.

Verification on 23 October 2026:

- 16 Python unittest tests: passed.
- 7 Chromium browser tests with Flask API: passed (30.8 seconds).
- TypeScript frontend and production build: passed.
- Legacy database check: IDs, relationships, statuses, and account hashes remained intact.
- `git diff --check`: passed.

Browser tests use the production build and a mobile Chromium viewport, not a physical device. Real login and sessions depend on Member 2 and have not been tested.
