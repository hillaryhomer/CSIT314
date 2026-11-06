> Member 6 now implements categories and real reports. Schema 6 retains anonymous project/view report events after project deletion; this supersedes the earlier report-retention limitation below. See [MEMBER6.md](MEMBER6.md).

# Member 5: US37 and US38

## Delivered scope

- [x] US37: designer sees persisted view counts, including zero, for owned Current and Past projects.
- [x] US38: designer sees unique saved favourite counts for those same projects.
- [x] Member 4 customer detail recorder, shared favourite integration, isolated tests and synthetic generator.

Member 6 category CRUD and daily/weekly/monthly reports are not implemented here. This does not certify all 48 user stories. No original UML, lecturer signatures, AGENTS.md or assignment specification was found in the repository. Names follow the requested BCE convention; return values preserve counts and records rather than forcing Boolean-only reads.

## Metric definitions and access

A view is one successful authorized customer detail opening through POST `/api/catalog/projects/:id/views`, with `{ "eventId": "a-stable-random-UUID" }`. The transaction validates the current customer, resolves the visible shared project, builds its detail projection, and inserts one event. It returns `{project, recorded}`; recorded is false for a duplicate. Failed validation, denied access, missing projects and failed database writes do not add events. An event committed before a lost HTTP response remains counted; replaying the same ID retrieves details without counting again.

The detail Boundary keeps one event ID across rendering, effect reruns and Retry, and creates another when the dialog is reopened. Requests for a different project use another ID. Card/list/search/image/plain detail GET reads do not count. Anonymous and designer detail access remains available through existing GETs and does not count. Views count repeat customer visits, **not unique visitors**. They do not prove that a human read the returned details. Server sessions determine identity; the browser supplies only an event ID, never a total. JSON, Origin and CSRF checks use the existing middleware.

Shortlists count current unique persisted favourite customer/project relationships. Repeated saves add nothing; another customer's first save adds one. Relationships temporarily hidden by account suspension remain counted, matching Member 4's retention policy. No remove-favourite operation exists or was added. If removal is agreed later, deleting a relation automatically reduces the derived count. Favourite success is still shown only after persistence succeeds. Customer private lists/search and saved status retain Member 4's ownership enforcement.

Analytics GETs require an active designer with projects:manage. SQL filters by the server session owner; another owner's ID returns 404. Responses contain project ID, title, status, views and shortlists, without customer identities. Both aggregates use one SQL snapshot. Dashboard has loading, empty, error/retry, explicit Refresh counts and focus refresh. Designer detail errors continue using Member 3's existing Boundary.

## Main files and contracts

| File | Role |
| --- | --- |
| backend/activity_boundary.py | Analytics list/detail GET and customer detail/view POST |
| backend/activity_controllers.py | ViewIDPViewsController, ViewIDPShortlistsController and transactional RecordIDPViewController |
| backend/activity_entity.py | Immutable ProjectView state; no display or Create method |
| backend/activity_repository.py | Event insertion and owner-scoped aggregate SQL |
| backend/member5.sql | Schema 5 migration, composite uniqueness, timestamp index and cascade FK |
| backend/database.py, backend/app.py | Incremental migration and shared HTTP wiring |
| src/member3/Catalog.tsx | Designer analytics Boundary at /designer/analytics |
| src/member4/CustomerPages.tsx | Stable event identity and atomic customer detail retrieval |
| backend/seed_member5.py | Guarded synthetic demo generator |
| tests/test_member5.py | Sessions, metrics, ownership, rollback, concurrency, restart, deletion and seed guards |
| tests/browser/member5.spec.ts | Lost-response retry, customer save, dashboard counts and refresh |

GET `/api/designer/analytics` returns an array of `{projectId,title,status,views,shortlists}`. GET `/api/designer/analytics/:id` returns one owned record. Both named read controllers offer `execute(project_id=None)` and return both counts from the same aggregate query. The Boundary uses the combined result instead of issuing two potentially inconsistent reads.

## Setup, migration and demo

Use an installed Python with requirements.txt dependencies:

```powershell
python -m pip install -r requirements.txt
python -m backend.app --init
npm.cmd run build
python -m backend.app --serve-ui
```

Startup/--init upgrades versions 1-4 to 5 without resetting existing accounts, sessions, projects, favourites or images. DATABASE_PATH selects the existing shared database; default is data/member1.sqlite. View history starts at deployment; old visits cannot be reconstructed. Project hard deletion cascades to views and favourites, matching Member 3/4 policy.

Create a NEW dedicated demo database, then start against it:

```powershell
python -m backend.seed_member5 --database .test-data/member5-demo.sqlite --environment development --seed 5
$env:DATABASE_PATH = '.test-data/member5-demo.sqlite'
python -m backend.app --serve-ui
```

The generator refuses existing files, the default application database and production environments. It has no destructive reset. Repeated runs should choose a new filename. Seed controls deterministic project/event IDs; synthetic account names, scenario distribution and starting counts are reproducible (security hashes, company IDs and operational timestamps need not be byte-identical).

Log in with designer1, designer2, designer3, customer1 or customer2, password `Synthetic demo password 5`. Designer1's DEMO-5-1-Current starts with **3 views / 2 shortlists**. Its Past project and designer2's projects start at **0 / 0**. Designer3 has no projects and demonstrates the empty dashboard. Categories use the real migration defaults; companies, hashed accounts, Current/Past projects, views and favourites use shared models/controllers/repositories.

To verify: sign in as customer1, open Demo Current 1: views become 4. Close/reopen: 5. Saving it again leaves shortlists at 2. Open and save Demo Past 1: it becomes 1/1. Log in as designer1 and refresh /designer/analytics to inspect counts. Restart the server and inspect again; counts persist. Designer2 cannot retrieve designer1's per-project analytics.

## Integration notes

Member 3: unchanged project IDs, ownership and Current/Past data; hard deletion removes activity by foreign key. Owner detail GET never records customer activity.

Member 4: GET remains side-effect free. Authorized customer UI uses the single atomic POST recorder, with a stable UUID reused after network failure. No second counter or favourite event is emitted. Existing add-only favourites remain the shortlist source. The old unavailable-recorder notes in earlier handoffs are superseded by this document.

Member 6: `project_views(project_id,event_id,occurred_at)` stores UTC ISO timestamps, indexed by occurred_at/project_id. Future report queries can use half-open UTC intervals (`occurred_at >= start AND occurred_at < end`) and group by project. Favourites provide created_at for retained relations only; they do not constitute a complete historical event ledger or historical shortlist snapshot. Hard project deletion removes its view history. Confirm retention and report timezone requirements before building historical reports. No reporting endpoint or customer-tracking identity is introduced here.

## Verification commands

```powershell
python -m unittest discover -s tests -p 'test_*.py' -v
npm.cmd run build
$env:PYTHON = (Get-Command python).Source
npm.cmd run test:e2e
npm.cmd run test:e2e:member2
npm.cmd run test:e2e:member3
npm.cmd run test:e2e:member4
npm.cmd run test:e2e:member5
```

Tests use disposable databases, not the application database. On this machine the available pgAdmin embedded interpreter isolates sys.path; its equivalent invocation inserts the repo root before unittest discovery: `python -c "import sys,unittest;sys.path.insert(0,'.');r=unittest.TextTestRunner().run(unittest.defaultTestLoader.discover('tests'));sys.exit(not r.wasSuccessful())"`. The browser harness already applies that workaround.

Remaining assumptions: original lecturer UML/signatures, final metric policy and Member 6 report retention/timezone contracts await group confirmation. These do not block the implemented Member 5 workflows.


Verification completed on 6 November 2026: 51 backend tests passed; Chromium browser suites passed Member 1: 7, Member 2: 3, Member 3: 4, Member 4: 6, Member 5: 1 (21 total). Production build and TypeScript check passed. Existing migration-version assertions and browser mocks/unavailable-metric expectations were updated to the new schema/API behavior before final reruns.
