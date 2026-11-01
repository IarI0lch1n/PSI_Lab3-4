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

- Web measurement/result: **MANUAL REQUIRED** (not measured in this record).
- Flutter measurement/result: **MANUAL REQUIRED** (not measured in this record).
- Method: start a stopwatch when the converter screen is ready for input; stop
  only after both the result and both rate contexts are visible. Record each
  platform's elapsed time and pass only if it is under 30 seconds.
