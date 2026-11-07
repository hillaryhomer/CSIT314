# CSIT314 Project Audit & Verification Report

Date: 7 November 2026. Scope: All 48 User Stories, tracked source, configuration, diagrams (`CSIT314.drawio`, `CSIT314_Consistency_Fixes.drawio`, `CSIT314_All_Roles_Wireframes.drawio`), backend SQLite schemas (v1–v6), and production build.

---

## 1. Executive Summary

The project is a complete, fully integrated web application consisting of a React/TypeScript frontend and a Python Flask + SQLite backend, implementing all 48 User Stories approved by the lecturer. All six member increments (Members 1–6) are complete, and all consistency fixes from `CSIT314_Consistency_Fixes.drawio` have been incorporated and verified.

---

## 2. Resolution of Historical Audit Findings

| No. | Finding | Prior Severity | Resolution Status | Verification Evidence |
| :---: | :--- | :---: | :---: | :--- |
| **1** | Production assets fail on deep URLs | P1 | **RESOLVED** | `vite.config.ts` sets `base: '/'`. Deep routes (`/admin/profiles`, `/designer/current`, etc.) load root-relative bundles properly. |
| **2** | Designer space shows other studios' projects | P2 | **RESOLVED** | Server-side ownership enforcement via session `g.actor_id`. Project queries filter by `owner = account_id`. Avatar displays logged-in account username. |
| **3** | Required-form marks do not enforce validation | P2 | **RESOLVED** | Form controls in account, company, category, and project modals now enforce native `required`, client-side constraints, `aria-invalid`, and `aria-describedby` linked to error labels. |
| **4** | Desktop search button lacks accessible name | P2 | **RESOLVED** | `src/components.tsx:SearchBox` provides `aria-label={placeholder}` on search inputs, ensuring accessible screen-reader labels. |
| **5** | Empty company search lacks explanation | P3 | **RESOLVED** | `src/member2.tsx:CompanyManagement` renders the shared `Empty` component when keyword search yields no match. |
| **6** | Story-mapping document references incomplete | P3 | **RESOLVED** | `src/data.ts:storyCoverage` and wireframe `WF27` map all 48 User Stories to concrete screens and endpoints. |

---

## 3. Incorporation of `CSIT314_Consistency_Fixes.drawio`

The codebase strictly adheres to the repair diagrams in `CSIT314_Consistency_Fixes.drawio`:

1. **US24 & US29 (Unified Search Controller `SearchIDPC`)**:
   - `backend/project_controllers.py` implements the shared `SearchIDPC` (`SearchIDPController`), which applies the status filter (`status='Current'` for US24, `status='Past'` for US29).
   - `backend/project_boundary.py` routes `/api/designer/projects/<kind>` to `SearchIDPC` with the respective status.
2. **US32 (Add Favourite IDP Sequence & `AddFAVC`)**:
   - `backend/customer_controllers.py` defines `AddFAVC = AddFavouriteController`.
   - `add_favourite(customerId, projectId)` strictly follows the sequence:
     1. Verify project via `find(project_id, public=True)`.
     2. Check existence via `store.exists(customer_id, project_id)`.
     3. If not exists, insert via `store.add(Favourite(...))`.
   - `backend/favourite_repository.py` implements `exists(customerId, projectId)` and `count_by_project(project_ids)`.
3. **Unified Class Models 1 & 2 Entities and Properties**:
   - `CompanyInformation` (`CI`): `designerId` / `designer_id` mapped to `owner_id`.
   - `InteriorDesignProject` (`IDP`): `designerId` / `designer_id`, `projectId`, `categoryId` properties.
   - `Favourite` (`FAV`): `customerId`, `projectId`, `savedAt` properties.
   - `ProjectView` (`PV`): `viewId`, `projectId`, `viewedAt` properties.
   - `Session`: Dataclass entity defined matching Class Model 1 (`sessionId`, `accountId`, `expiresAt`, `revoked`).
   - `Report`: Dataclass entity defined matching Class Model 2 (`periodStart`, `periodEnd`, `generatedAt`, `metrics`).
   - `UserProfile` (`UP`), `UserAccount` (`UA`), `IDPCategory` (`IDPC`) aliases and diagram properties aligned.
4. **BCE Entity Methods**:
   - As specified by the lecturer's pattern (*"both Control and Entity have `bool Update(CI x)`; the Entity returns `true`"*), all Entity classes (`CI`, `UP`, `UA`, `Session`, `IDP`, `IDPC`, `FAV`, `PV`, `Report`) now declare their respective BCE operations (`Create`, `Update`, `Delete`, `Search`, `findPublishedById`, `listOwned`, `exists`, `Record`, `GenerateDaily`, `GenerateWeekly`, `GenerateMonthly`, `aggregate`).
5. **Metric Source Policy**:
   - Shortlists (US38) are derived directly from `favourites` records.
   - View counts (US37) are derived directly from `project_views` records.
   - Reports (US44–US46) aggregate `report_events` using Asia/Makassar calendar periods. No artificial `ProjectEngagement` entity is used.

---

## 4. 48 User Stories Summary Status

| Group | Stories | Status | Backend Controller | Route / Boundary |
| :--- | :---: | :---: | :--- | :--- |
| **User Admin** | US01–US05 | **COMPLIANT** | `CreateUPC`, `ViewUPC`, `UpdateUPC`, `SuspendUPC`, `SearchUPC` | `/api/profiles` |
| **User Admin** | US06–US10 | **COMPLIANT** | `CreateUAC`, `ViewUAC`, `UpdateUAC`, `SuspendUAC`, `SearchUAC` | `/api/accounts` |
| **User Admin Auth** | US11–US12 | **COMPLIANT** | `LogInUAC`, `LogOutSessionC` | `/api/auth/login`, `/api/auth/logout` |
| **Designer Company** | US13–US17 | **COMPLIANT** | `CreateCIC`, `ViewCIC`, `UpdateCIC`, `DeleteCIC`, `SearchCIC` | `/api/company` |
| **Designer Auth** | US18–US19 | **COMPLIANT** | `LogInUAC`, `LogOutSessionC` | `/api/auth/login`, `/api/auth/logout` |
| **Current Projects** | US20–US24 | **COMPLIANT** | `CreateCurrentIDPC`, `ViewCurrentIDPC`, `UpdateCurrentIDPC`, `DeleteCurrentIDPC`, `SearchIDPC` | `/api/designer/projects/current` |
| **Past Projects** | US25–US29 | **COMPLIANT** | `CreatePastIDPC`, `ViewPastIDPC`, `UpdatePastIDPC`, `DeletePastIDPC`, `SearchIDPC` | `/api/designer/projects/past` |
| **Customer** | US30–US34 | **COMPLIANT** | `SearchIDPController`, `ViewIDPDetailsC`, `AddFAVC`, `ViewFAVListC`, `SearchFAVListC` | `/api/catalog/projects`, `/api/favourites` |
| **Customer Auth** | US35–US36 | **COMPLIANT** | `LogInUAC`, `LogOutSessionC` | `/api/auth/login`, `/api/auth/logout` |
| **Designer Analytics**| US37–US38 | **COMPLIANT** | `ViewPVCountsC`, `ViewFAVCountsC` | `/api/designer/analytics` |
| **Platform Manager** | US39–US43 | **COMPLIANT** | `CreateIDPCC`, `ViewIDPCC`, `UpdateIDPCC`, `DeleteIDPCC`, `SearchIDPCC` | `/api/manager/categories` |
| **Platform Reports** | US44–US46 | **COMPLIANT** | `GenerateDailyReportC`, `GenerateWeeklyReportC`, `GenerateMonthlyReportC` | `/api/manager/reports` |
| **Manager Auth** | US47–US48 | **COMPLIANT** | `LogInUAC`, `LogOutSessionC` | `/api/auth/login`, `/api/auth/logout` |

---

## 5. Verification Status

- Python compilation (`py_compile backend/*.py`): **PASSED** (0 errors).
- Architecture & BCE Consistency Script (`scratch/verify_all_consistency.js`): **13/13 PASSED**.
- BCE Entity Methods Presence Check: **100% PASSED**.
