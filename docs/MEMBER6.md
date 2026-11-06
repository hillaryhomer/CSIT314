# Member 6: categories and calendar reports

## Story checklist and architecture

| Story | Controller | Result |
| --- | --- | --- |
| US39 Create IDP Category | CreateIDPCategoryController | Persisted category; immediately shared with designer/customer modules |
| US40 View IDP Category | ViewIDPCategoryController | Stored detail; searchable list through US43 |
| US41 Update IDP Category | UpdateIDPCategoryController | Stable ID, live name/description update through shared joins |
| US42 Delete IDP Category | DeleteIDPCategoryController | Confirmed soft deletion; historical project links preserved |
| US43 Search IDP Categories | SearchIDPCategoryController | Trimmed, normalized substring search on name/description |
| US44 Generate Daily Report | GenerateDailyReportController | Selected local calendar day |
| US45 Generate Weekly Report | GenerateWeeklyReportController | Monday to next Monday containing reference date |
| US46 Generate Monthly Report | GenerateMonthlyReportController | Full selected calendar month |

All eight stories are implemented against shared Flask/SQLite and React. Platform Manager login/logout uses Member 2; backend requires role manager and categories:manage or reports:read as appropriate. Existing cookie, active account/profile, Origin and JSON/CSRF checks apply. No role or identity from the browser is trusted. No CI/CD, export, scheduled report or snapshot feature was added.

No official assignment brief/UML/lecturer signature document or AGENTS.md was available in this repository. The attached request and existing group contracts define this implementation. Read/search/generate controllers return data; display feedback remains in React. Entities have no display or Create methods.

## Main files

| File | Responsibility |
| --- | --- |
| backend/category_entity.py | IDPCategory state and input validation |
| backend/category_repository.py | Shared category SQL and entity mapping |
| backend/category_controllers.py | Five category use cases; manager access, transactions, duplicate handling |
| backend/report_service.py | ReportPeriod calendar model, timezone conversion, shared report orchestration |
| backend/report_repository.py | Timestamp-range aggregation and coverage in one SQL snapshot |
| backend/report_controllers.py | Three report use cases and reports:read enforcement |
| backend/manager_boundary.py | HTTP category/report routes |
| backend/member6.sql | Schema 6 migration, category constraints, event retention ledger and atomic triggers |
| backend/database.py, backend/app.py | Shared connection functions, incremental migration and route registration |
| src/member6/ManagerPages.tsx | Category list/detail/forms/confirmation and real report generation Boundary |
| src/App.tsx | Existing /manager/categories and /manager/reports routes wired to real screens |
| tests/test_member6.py | Isolated integration, migration, concurrency, calendar and failure tests |
| tests/browser/member6.spec.ts | Browser CRUD/cancel/failure and known report counts |
| tests/browser_member6_fixture.py | Guarded synthetic report fixture for the disposable browser database |

## Category rules

Fields: stable categoryId, trimmed NFKC name (1-100 characters), description (0-2000), createdAt and updatedAt. New timestamps are UTC ISO 8601; legacy category creation/update times are NULL and shown as unrecorded, because those dates were never stored. Status is retained from the shared model. New categories are Active. No additional status/restore workflow is introduced.

Names use the repository's existing normalization (NFKC, trim, lowercase). A unique name_key index prevents duplicates, including concurrent writes. Database triggers enforce normalized keys, trimmed names and field limits as well as controller validation. Names of deleted categories remain reserved. Existing normalized name collisions cause migration failure and rollback rather than merging categories or silently reassigning projects; the group must resolve any pre-existing collision using its prior schema before retrying migration. Existing data is never reset.

Deletion always soft-deletes, setting deleted_at and status=Suspended. Manager searches exclude deleted categories; detail/edit/delete subsequently return 404. Projects, images and favourites are not deleted. Member 3's existing transactional check rejects assignment to inactive categories, including a form opened before deletion. An existing project can retain its category while editing other fields. Shared public category options retain inactive categories for historical discovery/filtering and mark them inactive; designer forms exclude them for new assignments. No restore endpoint exists.

Create/edit/delete forms load real records, prevent concurrent submits and remain open with input/error on failure. Cancel performs no write. Deleted categories cannot be renamed. Name changes immediately appear on projects/customer results because those join by categoryId.

## Report definitions and historical availability

Only two supported activity metrics are exposed:

| Metric | Meaning | Original source and timestamp | Report source |
| --- | --- | --- | --- |
| projectsCreated | Recorded project creation events within the range, including projects subsequently deleted | interior_design_projects.created_at | report_events kind project_created |
| viewEvents | Recorded authorized customer detail openings within the range, including repeat visits; not unique visitors | project_views.occurred_at | report_events kind project_view |

These are activities during a period, not end-of-period project totals or current favourites. No favourite-additions metric is displayed: current favourites are not a complete historical additions ledger. Member 5 shortlist totals continue to count current unique relationships, without changes to saving/list privacy.

Schema 6 backfills creation/view events only from genuine surviving source timestamps. It does not invent prior visits, deleted activity or old category timestamps. report_coverage.retained_since records when continuous retention began. Reports beginning before that timestamp explicitly display **Incomplete historical coverage**, with the retained-since timestamp and explanation. Zero means zero recorded events, and must not be interpreted as proof of no unrecorded historical activity.

After migration, INSERT triggers on the real project and project_view tables copy one anonymous event within the original transaction. Source writes roll back if ledger insertion fails. Member 5 view event uniqueness remains the only deduplication point; no frontend report increment is added. Ledger keys include event kind and project/event identity, preventing double joins or repeated recordings. The ledger keeps event IDs, project IDs and timestamps without customer/account identity. It deliberately retains event references after project hard deletion, not live relational foreign keys. This preserves reporting history while Member 5's live project view/favourite tables keep their existing cascade policy. There is no reporting ledger mutation API.

Report SQL aggregates events directly by kind rather than joining views/favourites/projects, so multiple relations cannot multiply counts. Counts and coverage use one SQLite statement/snapshot. The ledger is activity history, not an independent mutable counter.

## Calendar and query contracts

Timezone assumption: **Asia/Makassar (UTC+08:00)**, matching the project user's timezone. Supported selected years are 2000-9998, with fixed UTC+8 calendar boundaries (modern Makassar has no DST). Daily is local midnight to next midnight; weekly is Monday midnight to next Monday; monthly is the first day to the next month's first day. All ranges are start inclusive/end exclusive. UTC conversion happens before querying; timestamps are canonical UTC with six fractional digits so microsecond boundary comparisons are exact.

Generated reports show start/end with offsets, timezone and generation time. Current periods are marked Partial and count only events up to generation; future periods are labeled Future with no activity up to now. Closed calendar periods may still have incomplete historical coverage. A failed query returns the shared error JSON and no fabricated metrics.

```text
GET    /api/manager/categories?q=keyword
POST   /api/manager/categories                    {name,description}
GET    /api/manager/categories/:categoryId
PUT    /api/manager/categories/:categoryId        {name,description}
DELETE /api/manager/categories/:categoryId        {}
GET    /api/manager/reports/daily?period=2024-02-29
GET    /api/manager/reports/weekly?period=2025-01-01
GET    /api/manager/reports/monthly?period=2024-02
```

Weekly accepts any reference date and reports its containing Monday-based week, including year-crossing weeks. Monthly accepts YYYY-MM. Report JSON includes metrics, coverage, partial/future, startInclusive/endExclusive, startUtc/endUtc, timezone and generatedAt. Unsupported fields/types/periods are rejected. No password, session token, customer identity or company contact is returned.

## Setup, migration and run

Use an installed Python with the existing requirements. No new dependencies were needed:

```powershell
python -m pip install -r requirements.txt
python -m backend.app --init
npm.cmd run build
python -m backend.app --serve-ui
```

Set DATABASE_PATH to choose the shared database (default data/member1.sqlite). Startup/--init migrates through schema 6, preserves accounts, sessions, categories, projects and favourites, and adds category metadata/indexes plus reporting history. Do not run --dev for real manager login. For a fresh install use `python -m backend.app --create-admin`; through the admin UI create a manager profile with categories:manage and reports:read and assign its account. Sign in at /login, then use /manager/categories and /manager/reports.

All application/fixture writes should use connect_database, which registers the existing normalization and new canonical timestamp functions used by database triggers. Other SQL clients may read normally; they must register these functions before writing affected tables.

## Verification and known counts

```powershell
python -m unittest discover -s tests -p 'test_*.py' -v
npm.cmd run build
$env:PYTHON = (Get-Command python).Source
npm.cmd run test:e2e
npm.cmd run test:e2e:member2
npm.cmd run test:e2e:member3
npm.cmd run test:e2e:member4
npm.cmd run test:e2e:member5
npm.cmd run test:e2e:member6
```

On this machine the pgAdmin embedded interpreter requires the repository on sys.path: `python -c "import sys,unittest;sys.path.insert(0,'.');r=unittest.TextTestRunner().run(unittest.defaultTestLoader.discover('tests'));sys.exit(not r.wasSuccessful())"`. Browser harnesses already handle this. All test databases are isolated. The report fixture explicitly refuses paths outside the guarded disposable .test-data/python-browser-* databases.

The Member 6 browser fixture creates project/view pairs at Feb 29 2024 local midnight, Feb 29's final microsecond and March 1 local midnight. Expected daily Feb 29: **2 projects / 2 views**; containing week Feb 26-Mar 4: **3/3**; monthly February 2024: **2/2**. The fixture also saves one favourite, demonstrating that it neither changes view counts nor multiplies report aggregates. These synthetic past fixtures intentionally show the historical coverage warning. The UI test creates an additional present-day project for category integration, which does not affect those 2024 counts.

Backend tests additionally exercise exact start/end, adjacent microseconds, offset conversion, leap/non-leap February, December rollover, a week crossing years, live report changes from actual customer detail POSTs, deduplication, empty periods, partial/future state, ownership/permissions, concurrent duplicate names, source/ledger rollback and category migration rollback on normalized collisions.

Verified on 6 November 2026: 51 existing backend regression tests passed, and the final Member 6 run passed all 8 new integration/migration tests (59 distinct backend tests). Chromium browser suites passed Member 1: 7, Member 2: 3, Member 3: 4, Member 4: 6, Member 5: 1 and Member 6: 2 (23 total). Production build and TypeScript check passed. The final Member 6 rerun followed fixes to explicit accessible field labels; the final migration-fixture rerun used the real bcrypt password hasher required by the shared account constraint. Test databases were isolated throughout.

## Integration and remaining assumptions

Member 2: shared account/profile permission checks and real sessions; no new auth store.

Member 3: shared category IDs and project creation events; deleted categories remain historical; stale new assignments rejected.

Member 4: shared filter options remain usable for historical inactive projects; favourites and private lists unchanged.

Member 5: same view definition and deduplication; anonymous retained reporting history survives deletion while per-project analytics continue using live source tables. Schema 6 supersedes the previous report-retention limitation in MEMBER5.md for new events and surviving backfill.

No implementation blocker remains for US39-46. Official UML signatures, final category deletion policy, final mandated report metrics and report timezone await group confirmation. The documented assumptions are used until official requirements are provided. Passing these tests does not certify every requirement across all 48 user stories.
