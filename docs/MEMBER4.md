> Member 5 integration supersedes the historical unavailable-recorder notes below: see [MEMBER5.md](MEMBER5.md). Customer detail POST now atomically returns details and records a deduplicated event; GET remains side-effect free.

# Member 4: Customer discovery and favourites

Implemented on 6 November 2026 using the shared React/TypeScript, Flask and SQLite stack. Project/category records come from Member 3's repository and category adapter; authentication and accounts come from Members 1/2.

## US30-34 checklist

| Story | Control | Boundary | Result |
| --- | --- | --- | --- |
| US30 Search IDPs | SearchIDPController.execute | GET `/api/catalog/projects?q=&categoryId=&style=` | Project array; combined keyword/category/style filters |
| US31 View detailed IDP | ViewIDPController.execute | GET `/api/catalog/projects/:projectId` | Latest project details with personal Saved status |
| US32 Add favourite | AddFavouriteController.execute | POST `/api/favourites` | Persisted unique customer/project pair; idempotent repeat |
| US33 View favourite list | ViewFavouriteListController.execute | GET `/api/favourites` | Current customer's visible saved projects |
| US34 Search favourite list | SearchFavouriteListController.execute | GET `/api/favourites?q=` | Keyword search restricted to that customer's favourites |

US33 is the customer's favourite list. Designer shortlist totals (US38) remain Member 5's responsibility. Remove Favourite is not added: there is no delete/toggle action or endpoint in this scope.

## Architecture and files

| File | Responsibility |
| --- | --- |
| `backend/customer_boundary.py` | HTTP Boundary for five use cases and style options |
| `backend/customer_controllers.py` | Search/detail/favourite controls, role/permission/visibility checks and transactions |
| `backend/favourite_entity.py` | Immutable Favourite state; no Create/display method |
| `backend/favourite_repository.py` | Favourite persistence and Member 5 shortlist-count adapter |
| `backend/project_repository.py` | Existing shared project source, style/favourite filters and safe public projection |
| `backend/member4.sql` | Version 4 migration and unique relationship/foreign-key constraints |
| `src/member4/CustomerPages.tsx` | Catalog filters, detail, save feedback and private favourite list |
| `src/member4/types.ts`, `customer.css` | Public response types and responsive styling |
| `src/member2.tsx` | Shared session/CSRF client; protects against stale authentication replies and logout-before-session-load |
| `src/App.tsx` | Existing navigation wired to real customer screens |
| `tests/test_member4.py` | Real-session backend integration, ownership, concurrency and rollback tests |
| `tests/browser/member4.spec.ts` | Customer browser workflows on an isolated database |

The existing InteriorDesignProject entity is reused. A separate customer IDP entity/store is not introduced. SQL stays in repositories, coordination in controllers, and displays/errors/success feedback in React Boundaries. View/Search return records; Add returns saved state and the saved project. No UML or lecturer signature document was found, so these names/JSON contracts cannot be certified against an unavailable Boolean-return diagram.

## Search and visibility rules

- Keyword: NFKC normalization, trimming and lowercase comparison using the existing shared normalization helper. Literal substring matching includes title and description, plus style/category/company name.
- Category: exact shared category ID; blank means all categories.
- Style: exact normalized style match (case-insensitive and trimmed); blank means all styles.
- Combined filters use AND. The keyword's searchable fields use OR. Example: keyword coastal + category CAT001 + style Japandi must satisfy all three filters.
- Blank/whitespace-only keyword lists every available project matching the remaining filters. Reset Filters clears all three controls.
- Style choices come from `GET /api/catalog/styles`, derived and deduplicated from visible project records. Categories come from the existing `/api/project-categories` endpoint, not a frontend constant.
- Public discovery/detail remain accessible without login, following the existing Member 3 assumption. Both Current and Past projects are visible only while the owner account/profile is active, the profile is designer and has projects:manage. No approval/publication workflow is invented.
- Historical projects may retain a suspended category under Member 3's policy; filters can still identify those records. Category CRUD remains Member 6 work.

The public projection includes project ID, title, description, category, style, status, image URLs, company name and project timestamps. It excludes ownerAccountId, companyId, account username/email, permissions, passwords/hashes, and company private contact/address fields. Designer display falls back to Interior Designer if there is no publishable company name.

## Favourite ownership and persistence

The customer ID is the verified session account ID. Every favourite endpoint requires an active customer account/profile with projects:discover permission. Origin, JSON and CSRF checks use Member 2's existing middleware. Request bodies cannot supply customerId/ownerAccountId; unsupported query fields are rejected as well. There is no API for querying another customer's list.

The schema uses `PRIMARY KEY(customer_account_id, project_id)`, with foreign keys to the existing account and project tables. The Add controller checks access and project visibility inside the same write transaction as insertion. INSERT ... ON CONFLICT DO NOTHING makes repeated and concurrent saves idempotent. Existing savedAt timestamps are preserved. UI Saved state is set only after a successful server response and the Save button is disabled while in flight/already saved.

Favourite lists join the current project source instead of copying project fields. Designer edits immediately affect subsequent catalog/detail/favourite reads. If a designer becomes unavailable, the relationship is retained but hidden from the list; it reappears if visibility is restored. Hard-deleting a project cascades to its favourite relationships and images, so there are no broken references. It does not delete the customer, company, or unrelated projects/favourites.

Private UI content resets on account changes; protected reads are rechecked on the server and refetched on page focus. A shared logout fix waits for the initial session check and always calls the logout API before reporting success, preventing a quick click from merely hiding a still-valid server session. Stale session responses cannot replace a newer accepted login.

## API contracts

```text
GET  /api/catalog/projects?q=coastal&categoryId=CAT001&style=Japandi
GET  /api/catalog/projects/:projectId
GET  /api/catalog/styles
GET  /api/favourites
GET  /api/favourites?q=coastal
POST /api/favourites
```

POST body and response:

```json
{"projectId":"IDP-..."}
```

```json
{
  "project": {"projectId":"IDP-...", "title":"Coastal Loft", "saved":true, "savedAt":"UTC ISO 8601", "...":"other public project fields"},
  "saved": true,
  "created": true
}
```

New relationship: 201/created true. Existing relationship: 200/created false, saved true. GET list endpoints return arrays. Detail returns a project object. Public catalog/detail includes a per-session saved Boolean; savedAt is returned only for the signed-in authorized customer's own saved record. Anonymous/other-role reads do not disclose someone else's Saved status.

Errors preserve `{error:{code,message,fields}}`: validation 400, unauthenticated 401, unauthorized role/permission 403, unavailable/deleted project 404, database failure 500. SQLite errors roll back the save and do not produce success feedback. Private/API responses use no-store through the shared middleware.

## Integration contracts

**Member 2:** existing opaque cookies, CSRF header and server account/profile checks. No alternate login, localStorage identity or client-supplied customer ID. Suspension prevents private favourite access on the next request. Relationships remain stored unless their project is deleted.

**Member 3:** one interior_design_projects source. Public search adds filters/projection without changing designer CRUD ownership. Favourite records reference stable project_id values and use ON DELETE CASCADE for consistent project deletion. Existing Member 3 regression tests compare the public subset rather than expecting internal owner/company identifiers in public JSON.

**Member 5:** `ProjectActivityAdapter(repository).shortlist_count(project_id)` derives an integer directly from unique favourite pairs. No separately incremented counter, outbox, dashboard or fake analytics values are added. Duplicate saves cannot raise the count twice; another customer's first save contributes one. Proposed contract: count persisted unique pairs, including temporarily hidden relationships, until project deletion. Confirm metric policy with Member 5 before changing this definition.

`view_tracking_available` is now true. Plain detail GET remains side-effect free. Member 5's authorized customer detail POST returns details and records one timestamped event atomically. The customer Boundary uses a stable event ID across retries; see [MEMBER5.md](MEMBER5.md) for the current metric and API contracts.

**Member 6:** category IDs and options use the shared project_categories adapter. Member 6 must connect its future CRUD to that source. No parallel static category list is added.

## Setup, migration and run

No new dependencies beyond the existing requirements are introduced:

```powershell
python -m pip install -r requirements.txt
python -m backend.app --init
python -m backend.app
```

In another terminal run `npm.cmd run dev`, then open http://127.0.0.1:5173. For one server, run `npm.cmd run build` then `python -m backend.app --serve-ui` and open http://127.0.0.1:3001.

Use an existing customer login or create an account through the Member 1 admin screen with a customer profile and projects:discover permission. `--create-admin` is available for initial administrator setup. Real login/logout requires starting without --dev.

Startup/--init upgrades schema versions 1-3 to version 4, adding only favourites and its index. Existing accounts, profiles, sessions, companies, projects, images and categories are preserved. The database remains data/member1.sqlite unless DATABASE_PATH is configured. Back up important data before migrations. Browser projects/accounts are seeded only into guarded, disposable .test-data databases.

## Verification

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
npm.cmd run build
$env:PYTHON = (Resolve-Path '.venv\Scripts\python.exe').Path
npm.cmd run test:e2e
npm.cmd run test:e2e:member2
npm.cmd run test:e2e:member3
npm.cmd run test:e2e:member4
```

Backend coverage includes all five stories, combined/reset-equivalent empty filters, personal Saved status, public privacy, role/permission/CSRF/Origin enforcement, account/profile suspension, restart/login persistence, latest designer fields, unavailable/deleted project policy, concurrent duplicate saves, database rollback and migration preservation. Browser tests exercise combined/reset filters, images/detail, save feedback, duplicate-submit prevention, separate customer sessions, reload/login persistence, favourite search, failure/retry, missing detail, designer changes/deletion and desktop/mobile layout.

Executed on 6 November 2026:

- 47 backend tests passed, including 10 Member 4 integration tests.
- TypeScript checking and Vite production build passed.
- 6 Member 4 browser tests passed, covering desktop/mobile filters, personal favourites, duplicate submit, persistence, failure/retry and designer updates/deletion.
- Browser regression: 7 Member 1, 3 Member 2 and 4 Member 3 tests passed (20 browser tests in total).
- The category/style accessible labels and a logout-before-session-load race discovered during testing were fixed; the affected suites were rerun and passed. The logout regression now verifies an actual successful logout API response before testing Back access.

The application database was backed up to `data/member1.before-member4-ebe82008.sqlite` and migrated to version 4. Existing account/profile/company/session/category/project/image rows were compared using counts and content digests and remained identical. SQLite integrity_check returned ok; foreign_key_check reported zero violations. Test accounts/projects/favourites were created only in disposable databases.

Remaining assumptions/dependencies: original UML/official visibility details and Member 6 category CRUD. Member 5 recorder/dashboard and the persisted-pair shortlist metric are now integrated. They do not require a separate account/project/category store or prevent US30-34 from functioning.
