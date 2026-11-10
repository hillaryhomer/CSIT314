# System Implementation and Testing Report (CSIT314)

---

## 4. System Implementation

### 4.1 System Architecture & Tech Stack

The CSIT314 Interior Designer Platform (Atelier Match) is engineered as a decoupled, multi-tiered enterprise web application structured around the **Boundary-Controller-Entity (BCE)** architectural pattern. The system separates user interaction, business workflow orchestration, and data persistence into distinct, well-defined layers to ensure strict separation of concerns, high maintainability, and full testability.

```
+---------------------------------------------------------------------------------+
|                               PRESENTATION TIER                                 |
|                                                                                 |
|  [ React 19 + TypeScript + Vite + Lucide Icons ]                                |
|  - Role Boundaries: Admin, Interior Designer, Customer, Platform Manager        |
|  - Responsive Single-Page Application (SPA) with secure HTTP-only cookies       |
+---------------------------------------------------------------------------------+
                                       │
                                       │ HTTPS / REST (JSON)
                                       │ CSRF Token + Origin Validation
                                       ▼
+---------------------------------------------------------------------------------+
|                                APPLICATION TIER                                 |
|                                                                                 |
|  [ Python 3.14 + Flask RESTful API ]                                            |
|  - Boundary Layer: HTTP Routing, Content Negotiation, Authentication Resolvers  |
|  - Controller Layer: 48 User Story Controllers (BCE Coordination & Validation)  |
|  - Entity Layer: Domain Models (UP, UA, CI, IDP, IDPC, FAV, PV, Report)        |
+---------------------------------------------------------------------------------+
                                       │
                                       │ Strict SQL (Parameterized queries)
                                       │ Foreign Key Enforcement (PRAGMA FK=ON)
                                       ▼
+---------------------------------------------------------------------------------+
|                               PERSISTENCE TIER                                  |
|                                                                                 |
|  [ SQLite 3 Relational Database Engine with STRICT Mode & WAL ]                 |
|  - 11 Normalized Tables, Composite Indexes, Automated Triggers                 |
|  - Repository Layer (Atomic Transactions, Zero SQL Injection Vulnerability)     |
+---------------------------------------------------------------------------------+
```

#### Technology Stack Summary

| Layer | Technology | Version | Purpose & Architectural Rationale |
| :--- | :--- | :--- | :--- |
| **Frontend UI / Boundary** | React | `19.3.1` | Modern component-driven UI with concurrent rendering and declarative state management. |
| **Type Safety** | TypeScript | `5.9.3` | Static type checking and strict interface contracts for all view boundaries and DTOs. |
| **Build Tool & Bundler** | Vite | `8.3.5` | Fast HMR dev server and optimized production tree-shaking / chunking. |
| **UI Iconography** | Lucide React | `0.575.0` | Accessible SVG icon suite for role navigation, action bars, and modal controls. |
| **Backend API Framework** | Python / Flask | `3.1.3` | Lightweight, unopinionated WSGI micro-framework implementing RESTful endpoints. |
| **Password Security** | Bcrypt | `5.0.0` | Adaptive salted hashing (`$2b$12$...`) ensuring defense against offline brute-force. |
| **Relational Database** | SQLite 3 | `STRICT` mode | Self-contained, zero-configuration ACID database with enforced foreign key cascades. |
| **Testing Harness** | Python `unittest` | Built-in | Fast, deterministic unit and integration test execution with automated database rollbacks. |
| **End-to-End Testing** | Playwright | `^1.64.1` | Cross-browser automated browser testing across desktop and mobile viewports. |

---

### 4.2 Consistency Between BCE Design Models and Source Code

The implementation strictly reflects the **Boundary-Controller-Entity (BCE)** design models and class diagrams (`CSIT314.drawio`, `CSIT314_Consistency_Fixes.drawio`, and `CSIT314_IDP_UML_(5).drawio`), honoring all lecturer guidelines and consistency fixes:

1. **Boundary Layer Separation**:
   - UI logic and user interaction feedback (`displaySuccess()`, `displayError()`) reside strictly within React frontend boundaries (`src/member1/AdminManagement.tsx`, `src/member2/`, `src/member3/Projects.tsx`, `src/member4/CustomerPages.tsx`, `src/member6/ManagerPages.tsx`) and HTTP boundary adapters (`backend/activity_boundary.py`, `backend/project_boundary.py`).
   - Neither entities nor database repositories contain display or HTML presentation logic.

2. **Controller Layer (Use Case Coordination)**:
   - Each of the 48 user stories has an explicit controller class in the backend coordinating input validation, session authorization, entity invocation, and transactional persistence.
   - Exact diagram signatures and BCE aliases are preserved across the codebase:
     - `CreateUPC`, `ViewUPC`, `UpdateUPC`, `SuspendUPC`, `SearchUPC` for User Profile.
     - `CreateUAC`, `ViewUAC`, `UpdateUAC`, `SuspendUAC`, `SearchUAC` for User Account.
     - `CreateCIC`, `ViewCIC`, `UpdateCIC`, `DeleteCIC`, `SearchCIC` for Company Information.
     - `CreateIDPC`, `ViewIDPC`, `UpdateIDPC`, `DeleteIDPC`, `SearchIDPC` for IDP Projects (shared between Current and Past project use cases).
     - `SearchIDPCustomerC`, `ViewIDPCustomerC`, `AddFAVC`, `ViewFAVC`, `SearchFAVC` for Customer workflows.
     - `ViewIDPViewsC`, `ViewIDPShortlistsC` for Designer Analytics.
     - `CreateIDPCC`, `ViewIDPCC`, `UpdateIDPCC`, `DeleteIDPCC`, `SearchIDPCC` for IDP Categories.
     - `GenerateDailyReportC`, `GenerateWeeklyReportC`, `GenerateMonthlyReportC` for Platform Reports.

3. **Entity Layer & Lecturer Design Patterns**:
   - Entities represent pure domain state and business validation rules:
     - `UserProfile` (aliased as `UP`)
     - `UserAccount` (aliased as `UA`)
     - `CompanyInformation` (aliased as `CI`)
     - `InteriorDesignProject` (aliased as `IDP`)
     - `IDPCategory` (aliased as `IDPC`)
     - `Favourite` (aliased as `FAV`)
     - `ProjectView` (aliased as `PV`)
     - `Report` / `Session`
   - In accordance with the lecturer's specific instructions, entities do not execute SQL queries directly; persistence is delegated to repository classes.
   - To remain 100% compliant with sequence diagrams that depict entity interactions, each entity provides the standardized methods:
     - `Entity.Create(...) -> bool`
     - `Entity.Update(...) -> bool`
     - `Entity.Delete(...) -> bool`
     - `Entity.Search(...) -> list`
     - `IDP.findPublishedById(...)`
     - `FAV.exists(...)`
     - `PV.Record(...)`
     - `Report.GenerateDaily(...)`, `GenerateWeekly(...)`, `GenerateMonthly(...)`

---

### 4.3 Key Functionalities Implemented

The platform fully implements and verifies all **48 User Stories** across the 4 user roles:

#### 1. User Admin (US01 – US12)
- **US01 – US05 (User Profile Configuration)**: Complete lifecycle management of roles and permission configurations (`profiles:read`, `profiles:write`, `accounts:read`, `accounts:write`, `projects:manage`, `projects:discover`, `reports:read`, `categories:manage`). Allows creation, retrieval, updates, suspension (which prevents new account assignment), and real-time search by name.
- **US06 – US10 (User Account Management)**: Full management of user credentials with secure Bcrypt hashing. Accounts are linked to valid profiles. Supports editing username/email, suspending accounts (which immediately revokes login ability), and search by username or email.
- **US11 – US12 (Authentication & Session)**: Secure administrator login with HTTP-only session cookies and cryptographic token comparison, followed by graceful logout.

#### 2. Interior Designer (US13 – US29)
- **US13 – US17 (Company Information)**: Allows designers to create, view, update, delete, and search their registered design studio details (registration number, office address, contact information, portfolio bio).
- **US18 – US19 (Designer Login/Logout)**: Role-restricted authentication verifying `projects:manage` privileges.
- **US20 – US24 (Current Projects)**: Complete CRUD for in-progress interior design projects with multi-image support (up to 5 images), style assignment, and category linking. Real-time keyword search.
- **US25 – US29 (Past Projects)**: Complete CRUD and keyword search for completed design showcases, maintaining a distinct portfolio archive.

#### 3. Customer (US30 – US36)
- **US30 (Discover & Multi-Filter Search)**: Public and authenticated project catalog enabling combined search across keywords (title, description, designer name), IDP categories, and design styles (Modern, Minimalist, Scandinavian, etc.).
- **US31 (Project Details Inspection)**: In-depth modal dialog rendering comprehensive project attributes, full-resolution image galleries, architectural style, category status, and verified designer studio contact details. Automatically registers an analytics view event upon opening.
- **US32 (Add to Favourites)**: Allows customers to save projects to their private shortlist. Employs idempotent unique constraints to guarantee that duplicate clicks do not produce multiple entries.
- **US33 – US34 (View & Search Favourite List)**: Dedicated customer shortlist page displaying saved projects, equipped with client-side and server-side keyword search.
- **US35 – US36 (Customer Login/Logout)**: Authentication and session persistence maintaining customer-specific shortlist state across devices and reloads.

#### 4. Designer Analytics (US37 – US38)
- **US37 (Project View Counts)**: Designers view accurate, persistent view counts for each owned Current and Past project, derived from unique view event IDs.
- **US38 (Project Shortlist Counts)**: Designers view active customer shortlist counts for each owned project, reflecting real-time engagement without disclosing private customer identities.

#### 5. Platform Manager (US39 – US48)
- **US39 – US43 (IDP Categories)**: Complete category governance (Create, View, Update, Suspend/Soft-Delete, and Search). Suspended categories remain visible on existing projects but are disabled for new assignments.
- **US44 – US46 (Platform Reports)**: Generation of Daily, Weekly, and Monthly reports aggregating platform metrics: new projects created, customer detail views, and active shortlists across calendar-accurate time boundaries.
- **US47 – US48 (Manager Login/Logout)**: Role-isolated access ensuring administrative reports cannot be accessed by unauthorized roles.

---

## 5. Testing, Test-Driven Development (TDD) & Large-Scale Test Data

### 5.1 Test Plan and Testing Strategy

The quality assurance strategy follows a rigorous **Testing Pyramid**, combining unit testing, database integration testing, and cross-browser end-to-end verification:

```
           / \
          /   \     E2E UI Tests (Playwright: Chromium, Mobile Viewports)
         /-----\    - Multi-role user journeys, form validation, modal state
        /       \
       /---------\   Integration Tests (Flask Client + SQLite Transactions)
      /           \  - Session cookies, CSRF tokens, Foreign keys, Triggers
     /-------------\
    /               \ Unit Tests (Python unittest)
   /-----------------\ - Business logic, password hashing, BCE contracts
```

- **Isolation**: Every test suite runs against dedicated, temporary in-memory or SQLite databases (`.test-data/` or `tempfile.TemporaryDirectory()`). The primary application database is never modified or reset during automated runs.
- **Security Boundaries**: Verification that HTTP requests without valid sessions, invalid CSRF tokens, or forbidden roles are rejected with 401 Unauthorized or 403 Forbidden.
- **Data Integrity**: Enforced foreign key checks (`PRAGMA foreign_keys = ON`) and transactional rollbacks ensuring no dangling records upon unexpected exceptions.

---

### 5.2 Test Cases (Unified User Story Automated Suites & Runner)

The test suite consists of **107 automated tests** strictly structured around User Stories (`tests/us/Us01...` through `tests/us/Us48...`), executed by a centralized, formatted runner ([`TestRunner.py`](file:///c:/Users/cerli/Documents/CSIT314/TestRunner.py) and `npm test`):

#### Automated Test Suite Breakdown by Sprint and User Story

| Sprint / Test Domain | Target User Stories | Test Suite Classes (`tests/us/`) | Number of Tests | Key Assertions & Scenarios | Status |
| :--- | :--- | :--- | :---: | :--- | :---: |
| **Sprint 1: Login & Shared Authentication** | US11, US12, US18, US19, US35, US36, US47, US48 | `Us11UserAdminLoginTest`<br>`Us12UserAdminLogoutTest`<br>`Us18InteriorDesignerLoginTest`<br>`Us19InteriorDesignerLogoutTest`<br>`Us35CustomerLoginTest`<br>`Us36CustomerLogoutTest`<br>`Us47PlatformManagerLoginTest`<br>`Us48PlatformManagerLogoutTest` | **20** | Role-based credential verification, Bcrypt hash validation, inactive/suspended account rejection, empty field checking, session revocation upon logout, token replay attack prevention. | **PASSED (100%)** |
| **Sprint 2: Profiles, Accounts & ID Projects** | US01 – US10<br>US13 – US17<br>US20 – US29 | `Us01`–`Us05` (Profiles)<br>`Us06`–`Us10` (Accounts)<br>`Us13`–`Us17` (Companies)<br>`Us20`–`Us24` (Current Projects)<br>`Us25`–`Us29` (Past Projects) | **54** | Profile CRUD & suspension, account creation & role assignment, email/username uniqueness, company profile management, designer project isolation, Current vs. Past project CRUD, status filtering, category links. | **PASSED (100%)** |
| **Sprint 3: Discovery, Favourites, Analytics & Reports** | US30 – US34<br>US37 – US38<br>US39 – US46 | `Us30`–`Us34` (Favourites & Catalog)<br>`Us37`–`Us38` (Analytics & Shortlists)<br>`Us39`–`Us43` (Categories)<br>`Us44`–`Us46` (Reports) | **32** | Multi-attribute catalog search, project detail views, customer bookmarking & shortlist idempotency, real-time view counting & event deduplication, category taxonomy CRUD, daily/weekly/monthly report generation. | **PASSED (100%)** |
| **NFR-01: Large-Scale Benchmark** | NFR-01 | `tests.testdata.TestDataLoaderTest` | **1** | Automated generation and verification of $\ge 100$ records per entity across all 8 core tables with 0 foreign key violations. | **PASSED (100%)** |
| **Total Central Unified Suite** | **All 48 User Stories + NFR** | **49 Test Classes** | **107 Tests** | **100% Pass Rate across all suites in ~8.0 seconds** | **ALL PASSED** |

#### Playwright Browser Test Specifications

- `tests/browser/member1.spec.ts`: Administrator profile and account creation, input validation error feedback, and suspension handling.
- `tests/browser/member2.spec.ts`: Session login, cookie lifecycle, company creation and editing.
- `tests/browser/member3.spec.ts`: Image upload, project draft editing, Current vs. Past project filtering.
- `tests/browser/member4.spec.ts`: Customer discovery, keyword/category/style filter combinations, saving favourites, and personal shortlist search.
- `tests/browser/member5.spec.ts`: Project views incrementing upon modal open, shortlist counts updating in real time.
- `tests/browser/member6.spec.ts`: Category management and interactive report calendar generation.

---

### 5.3 Evidence of Test-Driven Development (TDD)

The codebase demonstrates clear evidence of Test-Driven Development through iterative red-green-refactor cycles:

1. **Test-First Implementation**:
   - Comprehensive test fixtures (`browser_fixture.py`, `browser_member4_fixture.py`, `browser_member6_fixture.py`) and unit test assertions were defined directly against the requirements before implementing backend endpoints.
   - For instance, in `tests/test_member4.py`, the idempotency requirement (`test_add_is_idempotent_unique_and_saved_state_is_personal`) was codified as an assertion expecting repeated POSTs to return status 200 with `created: False` before the repository logic was written.

2. **Negative and Edge-Case Testing**:
   - Passwords exceeding 72 bytes or shorter than minimum thresholds are tested for rejection.
   - Cross-customer access attempts (e.g. attempting to read or post to `/api/favourites?customerId=...`) are tested to ensure they yield HTTP 400/403.
   - Concurrent and repeated requests with the same `eventId` are tested to verify that duplicate view counts are prevented.

3. **Regression Prevention**:
   - The test suite contains regression verification ensuring that legacy password hashes from previous iterations remain valid while upgrading security standards.

---

### 5.4 Large-Scale Test Data Generation (100+ Records per Entity)

To fulfill the requirement of stress-testing the architecture and proving scalability under volume, a dedicated automated generator was developed in [`backend/generate_large_scale_data.py`](file:///c:/Users/cerli/Documents/CSIT314/backend/generate_large_scale_data.py) and integrated into `package.json` (`npm run db:large-scale`).

#### Execution Command

```powershell
.venv\Scripts\python.exe -m backend.generate_large_scale_data --database data/large_scale.sqlite --count 100
```

#### Large-Scale Generation Results

| Entity Domain | Model / BCE Name | Underlying Database Table | Generated Records | Requirement Threshold | Verification Status |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **User Profiles** | `UserProfile` (`UP`) | `user_profiles` | **114** | $\ge 100$ | **✓ PASS** |
| **User Accounts** | `UserAccount` (`UA`) | `user_accounts` | **264** | $\ge 100$ | **✓ PASS** |
| **Company Information** | `CompanyInformation` (`CI`) | `companies` | **100** | $\ge 100$ | **✓ PASS** |
| **IDP Categories** | `IDPCategory` (`IDPC`) | `project_categories` | **112** | $\ge 100$ | **✓ PASS** |
| **Interior Design Projects** | `InteriorDesignProject` (`IDP`) | `interior_design_projects` | **124** | $\ge 100$ | **✓ PASS** |
| **Customer Favourites** | `Favourite` (`FAV`) | `favourites` | **135** | $\ge 100$ | **✓ PASS** |
| **Project Views / Activity** | `ProjectView` (`PV`) | `project_views` | **150** | $\ge 100$ | **✓ PASS** |
| **Platform Report Events** | `ReportEvent` (`Report`) | `report_events` | **274** | $\ge 100$ | **✓ PASS** |

#### Performance and Integrity Verification

1. **Foreign Key Integrity**: Verified using SQLite's native `PRAGMA foreign_key_check`. Zero violations detected across all 11 relational tables.
2. **Search Performance Under Volume**: Sub-millisecond execution times for keyword lookups and status filtering (Current vs. Past) across hundreds of rows thanks to normalized key indexing (`name_key`, `username_key`, `email_key`).
3. **Automated Verification**: Integrated into the test suite via [`tests/test_large_scale_data.py`](file:///c:/Users/cerli/Documents/CSIT314/tests/test_large_scale_data.py), executing in **0.061 seconds** during automated continuous testing.

