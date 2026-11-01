# CurrencyHub Quickstart and Validation Guide

This guide covers the local backend, Angular web client, Flutter Android
client, and the acceptance scenarios used to check the shared experience.
Automated tests use fake or mocked providers and must not contact live BNM or
CoinGecko services.

## Prerequisites

- Windows with PowerShell, Git, and the repository checked out.
- Python and the existing backend virtual environment at
  `backend\.venv\Scripts\python.exe`.
- Microsoft SQL Server reachable from the backend, an existing
  `currencyhub` database, and Microsoft ODBC Driver 18 for SQL Server. The
  checked-in connection template uses Windows integrated authentication;
  SQL Server authentication can instead be configured locally without
  committing credentials.
- Node.js and npm compatible with the versions declared/configured by the
  project, and the existing dependencies in `web\node_modules`.
- Flutter/Dart and an Android Studio Android Emulator. `flutter doctor` can
  report missing local Flutter/Android tooling.

## Backend setup and startup

Open PowerShell at the repository root:

```powershell
Set-Location backend
Copy-Item .env.example .env
```

Edit only the local, ignored `backend\.env` for this machine. In particular,
set `DATABASE_URL` to a SQLAlchemy `mssql+pyodbc` URL for the local SQL Server
and database. The placeholder-safe Windows-auth template shape is:

```text
mssql+pyodbc:///?odbc_connect=DRIVER={ODBC+Driver+18+for+SQL+Server};SERVER=<server>;DATABASE=currencyhub;Trusted_Connection=yes;TrustServerCertificate=yes
```

Create the `currencyhub` database on the SQL Server instance before migrating.
The configured identity needs permission to create/alter the schema and to
read/write application data. Keep passwords and any real credentials in local
configuration only.

The application settings load `.env` files. Alembic's
`backend\alembic\env.py`, however, uses the process-level `DATABASE_URL`
environment variable when it is set and otherwise its `alembic.ini` default.
Before migration, set the current PowerShell process variable to the same
connection URL as the local configuration (do not commit it):

```powershell
$env:DATABASE_URL = '<your local SQLAlchemy connection URL>'
.\.venv\Scripts\python.exe -m alembic upgrade head
```

Start the API from `backend`:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The backend listens on port `8000`; `0.0.0.0` permits the Android Emulator to
reach the host service. The configured local CORS origins permit Angular at
`http://localhost:4200` and `http://127.0.0.1:4200`.

Useful local API URLs:

- API root: `http://localhost:8000/`
- OpenAPI documentation: `http://localhost:8000/docs`
- Health: `http://localhost:8000/api/v1/health`
- Supported currencies: `http://localhost:8000/api/v1/currencies`
- Latest rates: `http://localhost:8000/api/v1/rates/latest`
- Conversion: `POST http://localhost:8000/api/v1/convert`
- History: `GET http://localhost:8000/api/v1/history`
- Analytics: `GET http://localhost:8000/api/v1/analytics`
- Refresh: `POST http://localhost:8000/api/v1/rates/refresh`

The API adapters use the configured BNM and CoinGecko-compatible services
when the real application is run. Do not use the live backend in automated
tests; use the repository's fake providers instead.

## Angular web

In a second PowerShell window at the repository root:

```powershell
Set-Location web
npm start
```

Open `http://localhost:4200`. The Angular API client defaults to
`http://localhost:8000/api/v1`; the backend must be running and its configured
CORS origins must include the web origin.

Run web validation without starting a browser manually:

```powershell
cmd /c npm test -- --watch=false
cmd /c npm run build
```

## Flutter Android Emulator

Ensure an Android Emulator is running and Flutter can see it:

```powershell
Set-Location mobile
flutter doctor
flutter devices
```

Run the app on the listed emulator device:

```powershell
flutter run -d <emulator-device-id>
```

The Flutter API client defaults to `http://10.0.2.2:8000/api/v1`; `10.0.2.2`
is the Android Emulator host-machine alias. Keep the backend bound to port
`8000` as above. Flutter's native HTTP client does not use browser CORS.

Run mobile validation:

```powershell
flutter analyze
flutter test
dart format --output=none --set-exit-if-changed lib test
```

## Runnable validation scenarios

Use the fake/mock providers in automated tests. For interactive scenarios
against a local backend, confirm the local provider/database setup is
available before treating the returned rates as demonstration data.

1. **Open without sign-in**: Open the web app or Android app; confirm current
   rates and per-currency source/freshness are available without account
   creation.
2. **Classic conversion**: Convert a positive amount between different
   supported currencies; identify each rate leg's provider, effective time,
   freshness, and fallback-used status.
3. **Invalid input**: Try blank, zero, negative, and non-numeric amounts;
   verify no result is produced and the user receives validation feedback.
4. **Same-currency conversion**: Select the same source and target; verify the
   original entered amount is preserved.
5. **All-currencies comparison**: Enter an amount and change the input
   currency; verify all visible values use one complete snapshot.
6. **Analytics**: Review 7-day and 30-day pair summaries and point context;
   verify empty history has an explicit empty state.
7. **Offline/cache**: Persist a complete snapshot, simulate a provider/network
   failure, and verify cached entries retain their original provider/effective
   time and are not mislabeled as fallback.
8. **Unavailable rates**: Remove a required entry or provide no usable
   snapshot; verify the missing currency is identified and no complete
   conversion/pair is shown.
9. **Restart/rehydration**: Restart the client with the network unavailable;
   verify the complete cached snapshot remains available and is not relabeled
   live.
10. **Refresh failure preservation**: Attempt an incomplete/failed refresh;
    verify the previous complete snapshot remains unchanged.
11. **Cross-client consistency**: Exercise equivalent data scenarios on web
    and mobile; compare provider, effective time, freshness, stale, and
    fallback-used metadata.

The backend, Angular, and Flutter test suites cover these behaviors with fake
or mocked data and do not call live providers.

## Environment and security checks

The checked-in `backend\.env.example` contains a local SQL Server connection
template and explicitly named placeholder DB/provider credentials; it does
not contain real DB credentials or provider keys. `backend\.env` and other
`.env` files are ignored, with only `.env.example` allowed into version
control. The tracked Angular and Flutter source scan found no database
credentials or provider secrets. A tracked-text credential-pattern scan
matched only configuration placeholders, provider configuration references,
and test fixtures; no real secret was identified.

The backend's default CORS allowlist is limited to the local Angular origins
`http://localhost:4200` and `http://127.0.0.1:4200`; it does not use a wildcard
and does not allow browser credentials. The app allows only `GET` and `POST`
with `Accept` and `Content-Type` headers. Flutter's native HTTP client does
not rely on CORS. Keep any custom local origins narrowly scoped.

The configured product scope remains informational: the API route set covers
currencies, rates, conversion, history, analytics, health, and refresh. It
does not add accounts, authentication, transfers, wallets, portfolios, or
financial transaction processing, as required by FR-026. These notes follow
the configuration boundaries in the project specification and constitution.

## Requirement mapping and acceptance record

- **FR-001**: The app's current-rates entry points require no sign-in; use
  scenarios 1 and 2 to inspect access and conversion.
- **FR-022**: The shared API base paths and the web/emulator host URLs above
  support equivalent essential capabilities; scenario 11 compares them.
- **FR-023**: Run the mobile client in the Android Emulator at phone size and
  check the rates, conversion, and analytics screens remain usable.
- **SC-001**: Measure from when the converter screen is ready for input until
  both the conversion result and its rate context are visible. The target is
  under 30 seconds; record web and Flutter measurements separately. A
  command-line test is not a substitute for this interactive timing.
- **SC-012**: Scenario 11 checks equivalent provenance fields and shared
  meanings across clients.

### SC-001 interactive timing record

- Web: **PASS — 0.20 seconds** in one browser-assisted run against a local
  mock API. Timing began when the Amount field was ready, included entering
  `25`, selecting USD to BTC, and submitting; it stopped after the result,
  both providers, and both original effective timestamps were visible.
- Flutter Android: **NOT RUN**. The configured emulator was available, but
  `flutter run` required installing Android SDK Platform 35. The command was
  stopped before installation because acceptance validation must not install
  packages. Flutter widget tests are not a substitute for this interactive
  timing.
- SC-001 overall: **NOT YET VERIFIED** until a Flutter Android timing is
  recorded. Start timing when the converter screen is ready for input; stop
  only after the result and both rate contexts are visible. Pass only if each
  platform completes in under 30 seconds.

### T063 automated scenario and requirement record

The complete deterministic suites passed: backend **395 passed** (one
Starlette deprecation warning), Angular **88 passed** in 8 files and production
build succeeded, and Flutter **84 passed**, analysis reported no issues, and
formatting reported 18 files with no changes. Backend tests have an autouse
HTTPX guard that rejects requests to BNM and CoinGecko domains; backend
provider tests use `MockTransport` or fake providers. Web and Flutter widget
tests use mocked API clients.

| Requirements | Outcome and evidence |
|---|---|
| FR-003–FR-006 | Automated pass: conversion, invalid-input validation, same-currency handling, provenance, and unavailable-rate tests passed in backend and both clients. |
| FR-007–FR-010 | Automated pass: all-currency calculations, per-entry provenance, and snapshot/effective-time distinctions passed in both clients. |
| FR-011–FR-014 | Automated pass: refresh, 7/30-day analytics, pair provenance, and incomplete-point handling passed in backend and client suites. |
| FR-015–FR-018 | Automated pass: outage/cache reuse, persistence and rehydration, unusable-cache handling, and unavailable states passed in both clients. |
| FR-019–FR-021 | Automated pass: BNM fallback, source-aware staleness, and atomic replacement/preservation passed in backend and client suites. |
| FR-022 | Automated pass: equivalent client contract and freshness-semantic tests passed. |
| FR-023 | Automated pass: Flutter phone-sized widget usability tests passed; interactive emulator acceptance remains unmeasured. |
| FR-024–FR-025 | Automated pass: client tests for plain-language freshness, provenance, and unavailable/error messages passed. |
| SC-002–SC-004 | Automated pass: conversion consistency, invalid input, and same-currency result tests passed. |
| SC-005–SC-006 | Automated pass: per-leg provenance and independent cached/fallback/stale rendering tests passed. |
| SC-007 | Automated pass: 7/30-day analytics, mixed provenance, and empty-state tests passed. |
| SC-008–SC-009 | Automated pass: outage/restart cache tests and distinct snapshot/effective-time/freshness tests passed. |
| SC-010 | **NOT RUN**: requires an unfamiliar human participant; tracked under T065. |
| SC-011–SC-012 | Automated pass: unavailable required-rate and cross-client semantic tests passed. |
| SC-013–SC-015 | Automated pass: BNM fallback/publication-day and cryptocurrency 15-minute boundary tests passed. |
| SC-016–SC-018 | Automated pass: cache usability, complete-snapshot replacement, and restart persistence tests passed. |

T063 remains incomplete until the Flutter interactive timing is recorded.

### T064 API contract verification

The published latest-rates entries, both conversion legs, and both legs of
each history point expose `freshness_state`, `is_fallback`, and `is_stale`
while preserving provider and effective time. Analytics and refresh
freshness summaries report primary live/fallback/cached counts separately
from stale and fallback-used counts. The backend schema and contract tests
confirm these shapes; **34 focused backend contract/integration tests
passed** (one existing Starlette deprecation warning). The verified
endpoints, schema names, and test files are recorded in
[`contracts/rates-api.md`](./contracts/rates-api.md).

T064 outcome: **PASS** for FR-003, FR-013, FR-014, FR-019–FR-025 and
SC-005–SC-009, SC-012–SC-018. SC-010 remains a human usability gate under
T065; the Android interactive timing for SC-001 remains unverified under
T063.
