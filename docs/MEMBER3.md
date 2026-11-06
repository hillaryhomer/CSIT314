# Member 3: Current and Past Interior Design Projects

Member 4 now extends this implementation with style filters, safe public projections and persistent favourites in schema version 4. See [MEMBER4.md](MEMBER4.md); the Member 4 contract supersedes the historical favourite integration placeholder and public owner/company ID fields below.

Implemented on 6 November 2026 using the existing React/TypeScript, Flask, SQLite, UserAccount/UserProfile and Member 2 session infrastructure. No separate designer/account store is introduced.

## User-story checklist

All ten use cases are implemented and exercised by backend integration tests and browser workflows.

| Story | Controller in `backend/project_controllers.py` | Boundary | Status |
| --- | --- | --- | --- |
| US20 Create Current | CreateCurrentIDPController.execute | POST `/api/designer/projects/current` | Implemented and tested |
| US21 View Current | ViewCurrentIDPController.execute | GET `/api/designer/projects/current/:id` | Implemented and tested |
| US22 Update Current | UpdateCurrentIDPController.execute | PUT `/api/designer/projects/current/:id` | Implemented and tested |
| US23 Delete Current | DeleteCurrentIDPController.execute | DELETE `/api/designer/projects/current/:id` | Implemented and tested |
| US24 Search Current | SearchCurrentIDPController.execute | GET `/api/designer/projects/current?q=` | Implemented and tested |
| US25 Create Past | CreatePastIDPController.execute | POST `/api/designer/projects/past` | Implemented and tested |
| US26 View Past | ViewPastIDPController.execute | GET `/api/designer/projects/past/:id` | Implemented and tested |
| US27 Update Past | UpdatePastIDPController.execute | PUT `/api/designer/projects/past/:id` | Implemented and tested |
| US28 Delete Past | DeletePastIDPController.execute | DELETE `/api/designer/projects/past/:id` | Implemented and tested |
| US29 Search Past | SearchPastIDPController.execute | GET `/api/designer/projects/past?q=` | Implemented and tested |

Each public controller delegates shared rules to ProjectController. Current/Past collections never mix, including view/update/delete by ID. Update does not change status. Search is normalized with the existing NFKC/trim/lowercase helper, matches title/description/style/category/company, and an empty keyword lists all owned projects in the selected collection. Search returns project records, not a Boolean.

## BCE and principal files

| Layer | File | Responsibility |
| --- | --- | --- |
| Boundary | `backend/project_boundary.py` | Registers HTTP endpoints and translates requests/responses |
| Boundary | `src/member3/Projects.tsx` | Owned list/search, detail, create/update forms, confirmations, errors and success feedback |
| Boundary | `src/member3/Catalog.tsx` | Live customer catalog/detail; category and analytics read adapters |
| Control | `backend/project_controllers.py` | Ten use cases, permissions, ownership, category rules and transactions |
| Entity | `backend/project_entity.py` | InteriorDesignProject state and public serialization; no Create/display methods |
| Repository | `backend/project_repository.py` | Parameterized SQL for shared projects, images and categories |
| Validation | `backend/project_validation.py` | Project fields and real image validation/re-encoding |
| Migration | `backend/member3.sql`, `backend/database.py` | Schema version 3, preserving existing accounts/company/sessions |
| Tests | `tests/test_member3.py`, `tests/browser/member3.spec.ts` | Isolated integration and browser workflows |

Display feedback stays in React. No UML/signature document exists in this checkout, so these controller names and JSON return contracts are implementation choices, not claims of compliance with an unavailable diagram. If a lecturer requires Boolean mutation returns, adapt the Boundary/Control contract together while retaining a clear way to fetch records for View/Search.

## Model and validation assumptions

The original task specification and UML were not supplied. The minimal model proposed in the request is used:

- Stable UUID-based `projectId`; `ownerAccountId` is derived from the verified session.
- `companyId` is the designer's company at creation, or null if none exists. A company is not required to create a project. The client cannot assign another company.
- Required `title` (1-160 characters), `description` (1-6000), `categoryId` (existing active category), and `style` (1-100).
- Fixed `status`: Current or Past, determined by the selected endpoint/controller.
- Optional `images` (0-5), server-generated `createdAt` and `updatedAt` in UTC ISO 8601.
- No progress, completion date, approval, publication workflow or Current-to-Past conversion is added.

Text is normalized and trimmed on the server. The API rejects unsupported fields, including projectId, ownerAccountId, companyId, status and timestamps. The ID, owner, company link, creation timestamp and status are preserved during project edits.

## Request and response contracts

Create and PUT accept the full editable record:

```json
{
  "title": "Garden Studio",
  "description": "Material-led residential design",
  "categoryId": "CAT001",
  "style": "Japandi",
  "images": [
    {"data": "BASE64_FILE_CONTENT", "mimeType": "image/png"}
  ]
}
```

PUT can retain an existing image with `{"imageId":"IMG-..."}`. Images omitted from the submitted array are removed. An omitted images property means an empty array. An image ID must already belong to that project; borrowed or duplicate IDs are rejected. New uploads receive new IDs. Client filenames and arbitrary remote image URLs are never used for storage.

Successful create returns 201 and a project object; view/update return the object, search returns an array, and delete returns `{"deleted":true}`. Objects contain the model fields plus categoryName, categoryStatus, companyName, designerName and `images:[{imageId,url}]`. There are no fabricated views/shortlists or account passwords/hashes.

Delete requires a JSON `{}` body and the shared CSRF header. Errors use the existing `{error:{code,message,fields}}` contract. Missing or unowned management IDs return 404. Another role or a designer without `projects:manage` receives 403; an absent/expired/revoked session receives 401.

## Image policy and atomic persistence

Chosen limits, pending an official specification: JPEG, PNG or WebP; up to five files, 2 MiB per file both before and after re-encoding, 12 megapixels per file, no animation. Project JSON requests allow up to 16 MiB to accommodate base64; other API requests retain the existing 16 KiB limit.

Pillow checks the actual format, claimed MIME, size, dimensions, decoding and animation. Images are re-encoded from pixels to discard filenames, metadata and trailing content. The browser supplies a local preview but server validation remains authoritative.

Images are stored as SQLite BLOBs, with generated IDs and persistent `/api/project-images/:imageId` URLs. Project metadata and all image additions/removals use one SQLite transaction. A database/image persistence failure rolls back the whole operation; no orphan files or half-created projects remain. Cancellation never uploads or mutates the database.

Image records belong exclusively to a project. Deleting that project cascades only to its images; removing an image from one project never deletes another project's image. A referenced category cannot be physically deleted. Deleting a company sets a project's companyId to null and preserves the project, account and images.

## Integration and visibility

**Member 1/2:** same database, account IDs, profile role/permissions, opaque cookie sessions and CSRF checks. Designer operations require an active account, active profile, designer role and `projects:manage`, with access rechecked inside mutations. Account suspension revokes sessions and removes its projects/images from public discovery; no project data is deleted by suspension.

**Member 4:** `GET /api/catalog/projects?q=&categoryId=` and `GET /api/catalog/projects/:id` use the same repository/tables as designer management. The homepage reads these endpoints, and details are fetched again from the server. Designer creates/updates/deletes are reflected immediately on the next catalog request. There is no second static project catalog. Favourites remain an explicit integration placeholder; persistence belongs to Member 4 and is not claimed complete.

Visibility assumption: the existing public discovery screen can show Current and Past projects from active accounts with an active designer profile and project-management permission. No approval/publication lifecycle is invented. Public data excludes credentials. Confirm this visibility rule with the group if public access should differ.

**Member 5:** shared project IDs and ownership now feed persistent customer detail views and favourite-derived shortlist counts. The analytics Boundary lists owned Current/Past projects with both counts. Project deletion cascades to views and favourites. See [MEMBER5.md](MEMBER5.md) for event deduplication, metrics and report retention limits.

**Member 6:** the repository has no category entity/backend from Member 6. A minimal shared `project_categories` table and read endpoint `/api/project-categories` are provided. The three previously displayed category IDs/names are seeded once; React no longer keeps a separate category array. Designer forms, customer filters and the manager category read screen use that endpoint. Member 6 must connect its CRUD to this source rather than create another store.

Category policy assumption: a suspended category cannot be selected for a new project or a new assignment. An existing project may retain its suspended category while other fields are edited; historical details show an inactive label. Referenced categories use ON DELETE RESTRICT. Category CRUD, analytics and favourites are not implemented as part of Member 3.

## Setup, migrate and run

Use a working Python interpreter (or the project's virtual environment):

```powershell
python -m pip install -r requirements.txt
python -m backend.app --init
python -m backend.app --create-admin  # only if a login-capable admin is needed
python -m backend.app
```

In another terminal, run `npm.cmd run dev` and open http://127.0.0.1:5173/login. Assign a designer account a profile with designer role and projects:manage permission. Open `/designer/current` or `/designer/past` after login. Company creation is optional.

For a single server, run `npm.cmd run build` then `python -m backend.app --serve-ui` and open http://127.0.0.1:3001. Real login requires running without --dev. Existing DATABASE_PATH/APP_ORIGIN/COOKIE_SECURE settings remain supported.

Startup/--init migrates version 1 or 2 to version 3 without changing existing identity/company/session records. New tables: project_categories, interior_design_projects and project_images. No sample designer projects are seeded into the application's database. Back up important databases before applying migrations.

## Verification

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
npm.cmd run build
$env:PYTHON = (Resolve-Path '.venv\Scripts\python.exe').Path
npm.cmd run test:e2e
npm.cmd run test:e2e:member2
npm.cmd run test:e2e:member3
```

Backend tests and browser fixtures use separate disposable databases. The browser harness uses real sessions for Members 2/3 and a fixed development identity only for Member 1 regression tests.

Executed: 37 backend tests passed (including 9 Member 3 integration tests), TypeScript/Vite build passed, 4 Member 3 browser workflows passed, and the 7 Member 1 plus 3 Member 2 browser regression tests passed. The failure/retry browser workflow was rerun with two immediate submit events and verified that only one request was sent. Coverage includes all ten use cases, category/image validation, server ownership/roles/permissions, status separation, case-insensitive and empty search, restart persistence, Cancel, customer/designer shared data, missing records, failed saves/retry, image cleanup and transactional rollback. `git diff --check` passed.

The local application database was backed up as `data/member1.before-member3-580bd317.sqlite` and migrated to version 3. All existing account/profile/company/session rows were compared before and after and remained identical. SQLite integrity_check returned ok and foreign_key_check reported zero violations. No test projects were inserted into the application database.

Remaining integration blockers are the missing official UML/field/visibility specification, Member 4 favourite persistence, Member 5 activity storage and Member 6 category CRUD. These do not require a second project source or block the implemented ten project-management use cases.
