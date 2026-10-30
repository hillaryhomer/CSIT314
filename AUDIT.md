# CSIT314 Project Audit

Date: 22 October 2026. Scope: all tracked source and configuration, documentation, assets, installed dependencies, and the production build. This audit did not modify the implementation.

## Summary

The project is a React/TypeScript interface prototype, consistent with the README scope. The build succeeds, but deployment, interface data consistency, validation, and accessibility issues remain. It is not a complete functional application. The original task specification was unavailable, so the claimed coverage of 48 user stories could not be independently verified.

## Findings

### 1. P1 - Production assets fail to load on deep URLs

Locations: `vite.config.ts:3`, `src/App.tsx:46`.

Using `base:'./'` creates relative `./assets/...` references. At `/admin/profiles`, the browser resolves them as `/admin/assets/...`, while the real files are under `/assets/...`. Refreshing or opening a nested route directly can display a blank page even when the HTML fallback is configured as described in the README.

Recommendation: use an absolute base of `/` for root hosting, then test direct loading and refresh for every production route. Subdirectory hosting requires corresponding router and asset URL changes.

### 2. P2 - Designer space shows other studios' projects

Locations: `src/App.tsx`, `src/data.ts`.

The sidebar shows Studio Kanso, but portfolio records are not restricted to that owner. Projects from other studios and their edit/delete controls may appear, and analytics may use all projects. This is a prototype data-consistency issue rather than evidence of a backend data leak because the Member 1 backend did not implement the preview data model.

Recommendation: add owner identity to fixtures and filter portfolio and analytics records by the selected designer. Apply server-side ownership rules when a backend is added.

### 3. P2 - Required-form marks do not enforce validation

The visual required marker is not consistently backed by native form validation or accessible error associations. Account, company, category, and project forms should expose required attributes and associated messages on the actual controls.

Recommendation: add native constraints, linked error text, and submit/keyboard verification.

### 4. P2 - Desktop search button lacks an accessible name

A desktop search button may rely on visually hidden mobile text. Add a persistent accessible name or a screen-reader-only label.

Recommendation: use `aria-label="Search projects"` or equivalent persistent text.

### 5. P3 - Empty company-search results lack an explanation

When no company matches, the interface should show an explicit empty state rather than rendering an empty details panel.

Recommendation: render the shared Empty component for zero-result searches.

### 6. P3 - Story-mapping document references are incomplete

Check the README and source coverage mapping together before relying on the interface as evidence of all functional requirements. Add or update the promised mapping document when task acceptance criteria are available.

## Declared Functional Boundaries

- Login/logout does not verify credentials or manage sessions; role selection and routes remain preview-only.
- Create/update/delete/suspend, favourites, and image upload actions show notifications only and do not persist changes outside Member 1 functionality.
- The preview has no complete API, authorization model, server-side data isolation, or browser persistence for non-Member-1 screens.
- Analytics and reports use sample values; report dates are not used for calculations.
- Package scripts should include the required lint and automated-test commands before production delivery.

These limitations are consistent with a prototype scope. A complete application would require server authentication and authorization, persistence, business-rule enforcement, and integration testing.

## Verification and Limits

- `npm.cmd run build`: passed, including `tsc --noEmit` and Vite production build.
- `npm.cmd ls --depth=0`: all directly declared dependencies are installed without missing or invalid reports.
- Source review found no fetch, localStorage, sessionStorage, eval, or dangerouslySetInnerHTML usage in the reviewed source.
- Font license and notice files are available. Photo provenance and licensing could not be verified from the available project files.
- Browser interaction, visual contrast, screen-reader behavior, and real viewport checks require further testing.

## Dependency Finding: P1 - Vite High-Severity Advisory

Location: package.json.

The audit identified a high-severity Vite advisory with additional related advisories. A Windows path-check bypass could contribute to command injection if an attacker controls arguments in an exploitable development workflow. Exploitability was not tested here, and this finding primarily affects development tooling rather than a statically hosted production build.

Recommendation: upgrade Vite to a release that resolves the applicable advisories, update the lockfile, rerun npm audit and the production build, and review whether the development server should bind to all network interfaces.
