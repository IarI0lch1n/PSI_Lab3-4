# Implementation Plan: CurrencyHub

**Branch**: `001-currencyhub-platform` | **Date**: 2026-10-02 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from [spec.md](spec.md) and the project constitution in [.specify/memory/constitution.md](.specify/memory/constitution.md)

## Summary

CurrencyHub will be delivered as a single full-stack product with one shared Python backend and two client applications: an Angular web client and a Flutter mobile client. The backend will own all business logic, persistence, provider integration, rate normalization, and analytics generation. Both clients will consume the same backend API, display a consistent snapshot of rate data, and persist the last successful backend response locally so they remain useful during outages or backend unavailability.

The implementation will follow the approved Clean Architecture boundaries, use decimal arithmetic for all financial calculations, support both fiat and crypto sources, and preserve freshness metadata so cached and fallback values are never presented as live data. Historical analysis will use persisted data to compute 7-day and 30-day summaries and trend direction without exceptions when datasets are empty.

## Technical Context

**Language/Version**: Python 3 (targeted 3.11+), TypeScript (Angular), Dart (Flutter)

**Primary Dependencies**: FastAPI, SQLAlchemy 2, Alembic, Pydantic, httpx, pytest, Angular, Flutter, Microsoft SQL Server, BNM XML source integration, CoinGecko-compatible JSON API integration

**Storage**: Microsoft SQL Server with SQLAlchemy ORM and Alembic migrations

**Testing**: pytest for Python backend, Angular unit tests for web validation and presentation, Flutter widget/unit tests for mobile behavior; no test depends on live BNM or CoinGecko services

**Target Platform**: Web application and Android-focused mobile app; Android Studio Emulator used for local mobile validation

**Project Type**: Full-stack web service plus web and mobile clients

**Performance Goals**: Each API request for latest snapshot and conversion should complete quickly under normal conditions; cached snapshots should render immediately when network is unavailable; 7-day and 30-day analytics should be computed from persisted data without blocking the UI

**Constraints**: Decimal-safe arithmetic only; no floating-point conversion logic; no direct SQL Server access from frontend; no third-party credentials or secrets in frontend code; explicit fallback/cached labels required; same-screen values must come from one validated snapshot; invalid values must never convert

**Scale/Scope**: 18 supported currencies (10 fiat + 8 crypto), historical records retained for 7-day and 30-day analytics, shared API contract for web and mobile clients

## Constitution Check

*GATE: Must pass before implementation. Re-check at the end of design.*

Pass: The implementation plan is aligned with the constitution and specification.

- Architecture constraint: The backend will use the required Domain, Application, Infrastructure, and API layers and will not directly depend on FastAPI, SQLAlchemy, SQL Server, BNM, or CoinGecko in the Domain/Application layers.
- Dependency injection: Repositories, providers, and caching services will be injected through interfaces and factory logic.
- Data and source rules: BNM XML and crypto API JSON will be normalized into a common internal representation; fallback rules will treat weekends and holidays with previous-rate reuse; all snapshots will keep source and freshness metadata.
- Financial correctness: all monetary conversions will use Decimal arithmetic and a normalized MDL-based rate representation.
- Offline and cached data: both clients will persist the last successful backend snapshot locally and clearly display stale or cached data with timestamps.
- Security: secrets remain server-side only; environment configuration will provide connection details and API keys; no deployment secrets will be committed.
- Git and process: specification and plan are in place before implementation; all code work will remain scoped to the feature branch and merge through review.

## Project Structure

### Documentation (this feature)

```text
specs/001-currencyhub-platform/
├── spec.md              # Product requirements and acceptance tests
├── plan.md              # This file
├── research.md          # Design decisions and rationale
├── data-model.md        # Domain and persistence model
├── quickstart.md        # Validation and local setup guide
├── contracts/
│   └── rates-api.md     # Shared REST contracts and responses
├── checklists/
│   └── requirements.md  # Validation checklist for the feature
└── tasks.md             # Generated later by spec-kit tasks workflow
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── api/
│   │   ├── routers/
│   │   ├── schemas/
│   │   └── dependencies/
│   ├── application/
│   │   ├── dto/
│   │   ├── services/
│   │   └── use_cases/
│   ├── domain/
│   │   ├── entities/
│   │   ├── value_objects/
│   │   ├── interfaces/
│   │   ├── enums/
│   │   └── exceptions/
│   ├── infrastructure/
│   │   ├── database/
│   │   ├── repositories/
│   │   ├── providers/
│   │   └── cache/
│   ├── core/
│   │   ├── config/
│   │   ├── logging/
│   │   └── security/
│   └── main.py
├── tests/
│   ├── unit/
│   ├── integration/
│   └── contract/
├── alembic/
│   ├── versions/
│   └── env.py
├── .env.example
├── requirements.txt
└── pytest.ini

web/
├── src/
│   ├── app/
│   │   ├── core/
│   │   │   ├── api/
│   │   │   ├── models/
│   │   │   ├── services/
│   │   │   └── storage/
│   │   ├── features/
│   │   │   ├── converter/
│   │   │   ├── rates/
│   │   │   └── analytics/
│   │   └── shared/
│   └── assets/
├── angular.json
├── package.json
├── tsconfig.json
└── tests/

mobile/
├── lib/
│   ├── core/
│   │   ├── api/
│   │   ├── cache/
│   │   └── theme/
│   ├── features/
│   │   ├── converter/
│   │   │   ├── data/
│   │   │   ├── domain/
│   │   │   └── presentation/
│   │   ├── rates/
│   │   │   ├── data/
│   │   │   ├── domain/
│   │   │   └── presentation/
│   │   └── analytics/
│   │       ├── data/
│   │       ├── domain/
│   │       └── presentation/
│   └── main.dart
├── test/
├── pubspec.yaml
└── analysis_options.yaml
```

**Structure Decision**: The codebase will be organized as a three-workstream implementation: one shared backend API and two frontends. Backend responsibilities center on domain logic, persistence, provider abstraction, analytics, and API orchestration; the Angular and Flutter clients remain focused on UI state, cached offline behavior, and calling the backend API through stable client services.

## Domain Model

The domain model will model the core business objects without tying them to infrastructure or HTTP concerns.

### Currency
- code: string
- name: string
- type: Fiat or Crypto
- is_supported: bool

Rules:
- supported values are restricted to the required supported currency set
- code must be unique
- type is explicit and immutable in the domain model

### RateSnapshot
- snapshot_id: UUID
- captured_at: datetime
- source_name: string
- source_type: Live | Fallback | Cached
- rate_date: date
- is_stale: bool
- rates: list or map of normalized rate values

Rules:
- one snapshot contains all supported values for a consistent point in time
- freshness metadata remains part of the snapshot
- a refresh must not partially replace the currently visible snapshot

### ExchangeRateRecord
- currency_pair: CurrencyPair
- value: Decimal
- effective_at: datetime
- source_name: string
- source_type: Live | Fallback | Cached

Rules:
- value must be greater than zero
- records are persisted for historical analytics and fallback decisions

### ProviderInfo
- provider_id
- name
- kind: fiat or crypto
- base_url or config metadata
- active flag

Rules:
- provider metadata is persisted separately from the rate data
- provider source is traceable in API responses and stored records

### AnalyticsSummary
- base_currency
- quote_currency
- period: 7d or 30d
- values: list of time points
- minimum, maximum, average
- absolute_change
- percentage_change
- trend: GROWTH | DECLINE | UNCHANGED
- source_state: live | fallback | cached

Rules:
- trend is derived explicitly from first and last values
- empty dataset results in empty-state output instead of an exception

## Database Model

The database will persist enough data for current snapshots, offline recovery, and historical analytics without storing user accounts or personal data.

### Tables

1. currencies
   - id
   - code
   - name
   - type
   - is_supported
   - created_at

2. rate_snapshots
   - id
   - captured_at
   - source_name
   - source_type
   - rate_date
   - is_stale
   - created_at

3. exchange_rates
   - id
   - snapshot_id (FK)
   - currency_code
   - quote_to_mdl_rate
   - nominal_unit
   - source_name
   - source_type
   - created_at

4. historical_rates
   - id
   - base_currency
   - quote_currency
   - rate_value
   - effective_at
   - source_name
   - source_type
   - created_at

5. provider_sources
   - id
   - provider_name
   - provider_type (fiat or crypto)
   - config_reference
   - is_active

6. analytics_cache (optional, if performance optimization is needed)
   - id
   - pair_key
   - period
   - payload
   - generated_at

### Database Notes
- SQLAlchemy ORM models live in the infrastructure layer and map to SQL Server tables.
- Alembic migration files will manage versioned schema evolution.
- rate snapshots are stored as points in time to allow fallback and stale-data tracking.
- the database must retain enough history for 7-day and 30-day analytics windows.

## REST API Design

All endpoints will be versioned under `/api/v1`.

### GET /api/v1/currencies
Purpose: return the supported currencies and their metadata.

Response:
- list of currency codes, names, types, and support flags

### GET /api/v1/rates/latest
Purpose: return the most recent validated rate snapshot.

Response:
- snapshot id
- captured_at
- source_name
- source_type
- rate_date
- rate map normalized to the internal representation
- stale or cached indicators

### POST /api/v1/convert
Purpose: convert one amount from source to target currency using a single consistent snapshot.

Request:
- amount
- source_currency
- target_currency

Response:
- source_amount
- converted_amount
- source_currency
- target_currency
- rate_value
- rate_date
- source_name
- freshness_state

### GET /api/v1/history
Purpose: return historical values for a selected base and target currency over a requested period.

Query params:
- base_currency
- quote_currency
- period (7d or 30d)

Response:
- ordered time series
- source state metadata
- empty-state response if no records exist

### GET /api/v1/analytics
Purpose: return statistical summary and trend data for a pair and period.

Required response fields:
- points / time series
- minimum
- maximum
- average
- absolute_change
- percentage_change
- trend
- data source/freshness metadata

### All-currencies snapshot pattern
For the all-currencies comparison screen, the backend will return a single normalized snapshot object that contains all visible values for the same captured timestamp. This prevents the web and mobile clients from mixing different refresh times while computing all visible currencies from a common base.

## External Provider Integration

### Provider Architecture
The backend will use adapters and a shared rate-provider abstraction.

**Common abstraction**
- RateProvider interface
- fetch_latest_rates()
- fetch_historical_rates(currency_pair, period)
- get_metadata()

**Implementations**
- BnmRateProvider / BnmRateAdapter
- CoinGeckoRateProvider / CoinGeckoRateAdapter

### BNM Integration
- Fetch XML data from the National Bank of Moldova
- Parse XML into a normalized internal representation
- Map values to supported fiat currencies with correct nominal-unit handling
- Normalize quoting rules so all rates are represented in a common internal basis: 1 unit of currency = X MDL
- For missing weekend or holiday values, use the most recent valid previous rate and explicitly mark the result as fallback

### Crypto Integration
- Fetch current and historical JSON data from CoinGecko or a documented equivalent
- Parse rates into a normalized internal representation
- Support fiat-to-crypto and crypto-to-crypto conversions
- Store historical values for analytics windows

### Provider Patterns
- Adapter: used for BNM and crypto provider integrations
- Strategy: used to decide fallback logic, especially weekend/holiday handling and fallback selection
- Factory Method: used to create the appropriate provider based on currency type or source selection
- Facade: used by the API layer through a high-level application service that exposes current rates, conversion, multi-currency calculations, and analytics
- Repository: used for persistence behind domain/application interfaces
- Unit of Work: used for transactional persistence when snapshot and historical record updates must commit together

## Caching and Fallback Design

### Backend resilience
- On every refresh, the backend attempts a live provider fetch.
- Valid snapshots are persisted and become the active latest snapshot.
- On provider failure, the last valid snapshot remains usable and is not discarded.
- When BNM has no rate for a weekend or holiday, the backend uses the latest valid previous rate and labels it as a fallback source.
- Cached and fallback metadata are included in API responses as separate state values.

### Frontend resilience
- Web: Angular stores the last successful backend snapshot in browser local storage.
- Mobile: Flutter stores the last successful snapshot in persistent local storage using a suitable persistent cache implementation.
- When the backend or network is unavailable, both clients show the last successful cached snapshot.
- UI must mark cached or stale rows with the original timestamp and source status.
- If no cached data exists, the UI displays an explicit unavailable state.

### Data freshness rules
- live: current provider data
- fallback: previous valid rate used due to holiday/weekend or provider gap
- cached: last successful snapshot used locally because backend or network is unavailable

The frontend must never silently present cached data as “fresh” data.

## Financial Calculation Design

All conversions and analytics will use Decimal arithmetic. The backend will normalize every source rate to a common internal basis prior to conversion.

### Normalized model
For each currency, store a value representing:
- 1 unit of currency = X MDL

Then conversion between any two currencies is computed as:

amount × source_rate_to_mdl / target_rate_to_mdl

This approach handles:
- fiat → fiat
- fiat → crypto
- crypto → fiat
- crypto → crypto
- same currency → same currency

### Nominal-unit handling
The system will also record and apply the nominal unit for each source quote. This avoids incorrect conversion when a provider rate is defined per 10, 100, or 1000 units rather than per single unit.

### Same-currency behavior
If source_currency == target_currency, conversion returns the original amount unchanged and still tags the result with the applicable rate source and timestamp.

## Web Frontend Architecture

**Stack**: Angular + TypeScript

**Suggested structure**:

```text
web/src/app/
├── core/
│   ├── api/
│   ├── models/
│   ├── services/
│   └── storage/
├── features/
│   ├── converter/
│   ├── rates/
│   └── analytics/
├── shared/
└── app-routing.module.ts
```

### Responsibilities
- Core API layer: typed HTTP client services for `/api/v1` endpoints
- Core storage: browser local storage for last successful snapshot
- Converter feature: classic conversion form and validation UI
- Rates feature: current rate list and freshness display
- Analytics feature: 7-day and 30-day charts and summaries
- Shared: currency helpers, formatting, validation, chart components, and common UI widgets

### UI requirements
- responsive layout for desktop and mobile-sized screens
- classic converter, all-currencies comparison, current rates view, and analytics views
- stale/cached labeling and original timestamp visibility
- no direct SQL or provider integration; all data flows through the backend API

### Local caching
- Angular persists the last successful API snapshot and rehydrates it when the backend is unavailable or the page is reopened
- the app shows the cached or stale status and timestamp until fresh data is available

## Mobile Frontend Architecture

**Stack**: Flutter + Dart; Android is the primary target; Android Studio Emulator is the demonstration environment.

**Suggested structure**:

```text
mobile/lib/
├── core/
│   ├── api/
│   ├── cache/
│   └── theme/
├── features/
│   ├── converter/
│   │   ├── data/
│   │   ├── domain/
│   │   └── presentation/
│   ├── rates/
│   │   ├── data/
│   │   ├── domain/
│   │   └── presentation/
│   └── analytics/
│       ├── data/
│       ├── domain/
│       └── presentation/
├── main.dart
```

### Responsibilities
- Core API: Dio or equivalent HTTP client configured for the backend
- Core cache: persistent local cache for the last successful snapshot
- State management: BLoC/Cubit-based flows for rates, conversion, and analytics
- Charts: a charting library suitable for time-series 7-day and 30-day charts
- Offline support: the app continues to operate with the last successful cached snapshot and shows stale status clearly

### Android emulator networking
Because localhost inside the Android Emulator does not resolve to the Windows host, backend URL configuration must use the host machine address appropriate to the local network. The recommended development setting is:
- Web/Angular client calls the host machine through an explicit local backend URL, such as `http://host.docker.internal` or the Windows host IP from the local network if needed.
- Flutter mobile app should target the host machine via `10.0.2.2` when running on the Android emulator, or the actual host machine IP when required by the local environment.

The implementation must clearly document which backend address is used for local emulator testing so the app can reach the backend reliably.

## Testing Strategy

### Backend tests
Backend tests will use mocked or fake provider implementations and must never call live providers.

**Required unit test coverage**:
- BNM XML parsing
- crypto JSON parsing
- BNM nominal/unit normalization
- direct conversion
- reverse conversion
- fiat/crypto conversion
- crypto/crypto conversion
- same-currency conversion
- zero input
- negative input
- invalid input
- malformed provider responses
- empty provider responses
- weekend/holiday fallback
- cached rate fallback
- 7-day statistics
- 30-day statistics
- empty historical data

**Test structure**:
- unit tests for domain rules and conversion logic
- integration tests for application services and persistence
- API contract tests for request/response behavior

### Frontend tests
- validation tests for invalid amounts and required fields
- conversion presentation tests for output formatting and source visibility
- cached-data indicators for stale, fallback, and local cache states
- analytics presentation tests for minimum, maximum, average, change, percentage change, and trend labels

### Non-functional validation
- verify cached data is never mislabeled as fresh
- verify same-screen values use a single consistent snapshot
- verify empty historical datasets yield a clear user-facing empty state

## Configuration and Security

### Environment configuration
The backend and frontend configuration will use environment files and environment variables. A sample file, `.env.example`, will be included without real credentials.

Required environment values include:
- SQL Server connection string
- BNM endpoint information
- CoinGecko or equivalent provider configuration
- optional CORS allowed origins for local web/mobile development

### Security requirements
- no SQL Server passwords committed to Git
- no API keys committed to Git
- no tokens in frontend code
- only backend hosts the third-party provider credentials
- no direct database or external provider access from either frontend

### CORS for local development
The backend will configure CORS to allow local Angular development and, where necessary, Flutter local API access for Android emulator or development device testing. The app should permit development origins only and avoid broad wildcard settings in non-local environments.

## Local Development Workflow (Windows)

The plan assumes a Windows development environment with the following flows:

1. Backend
   - create a local Python virtual environment
   - install dependencies from `requirements.txt`
   - set environment variables in `.env`
   - run FastAPI app locally with uvicorn or equivalent
   - ensure SQL Server is available and Alembic migrations are applied

2. Web frontend
   - install Angular dependencies in `web/`
   - configure the API base URL to the local backend
   - run Angular dev server locally
   - confirm CORS is configured for local browser development

3. Mobile frontend
   - install Flutter dependencies in `mobile/`
   - run the app in Android Studio Emulator
   - target the backend through `10.0.2.2` for emulator-based local testing
   - verify cached states work offline and when the backend is unavailable

### Practical development notes
- Each project should be runnable independently.
- Backend services must be started before frontend testing if the app depends on live API data.
- The web and mobile clients should share the same data contract and freshness semantics.
- Local testing should verify API connectivity from emulator, browser, and local host without requiring live production credentials.

## Implementation Phases

### Phase 0 – Project setup and shared contracts
- initialize backend, web, and mobile project folders
- define environment configuration and example files
- finalize API contract and common data objects
- establish branch and review workflow

### Phase 1 – Backend domain and use cases
- create domain entities and value objects
- define repository and provider interfaces
- implement currency and conversion domain rules
- implement Decimal-based conversion calculation and validation

### Phase 2 – Persistence and provider integration
- create SQLAlchemy models and Alembic migration scripts
- implement repository layer and Unit of Work
- implement BNM and crypto provider adapters
- add provider factory and strategy-based fallback logic

### Phase 3 – API and backend resilience
- implement FastAPI routers and schemas
- expose current rates, conversion, history, and analytics endpoints
- persist snapshots and historical data
- add fallback and cached-state metadata to responses

### Phase 4 – Angular web client
- create typed API services and shared models
- implement classic converter, all-currencies comparison, current rates, and analytics screens
- add local storage caching and stale/fallback indicators
- add UI validation and chart presentation where required

### Phase 5 – Flutter mobile client
- create Dio-based API layer and cache layer
- implement BLoC/Cubit-driven screens for converter, rates, and analytics
- add persistent local snapshot storage and charting
- validate offline and stale-state UX on Android emulator

### Phase 6 – Testing and quality gates
- run backend tests with fake providers
- run frontend validations and presentation tests
- verify empty-state, cache fallback, and analytics behavior
- confirm API contracts remain consistent between web and mobile clients

### Phase 7 – Final verification and handoff
- validate all acceptance criteria against the spec
- confirm no constitutional violations remain
- verify no secrets are committed
- ensure the app can run in a local Windows + Android Emulator environment

## Complexity Tracking

No constitution violations require exceptions. The design stays within the approved architecture and project constraints and keeps the solution simple while addressing the required resilience, persistence, data correctness, and multi-platform requirements.

