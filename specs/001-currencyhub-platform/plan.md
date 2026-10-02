# Implementation Plan: CurrencyHub

**Branch**: `001-currencyhub-platform` | **Date**: 2026-10-02 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from [spec.md](spec.md) and the project constitution in [.specify/memory/constitution.md](.specify/memory/constitution.md)

## Summary

CurrencyHub will be implemented as a single full-stack product with one shared Python backend and two client applications: an Angular web client and a Flutter mobile client. The backend remains the system of record for rate normalization, persistence, provider integration, and analytics generation. Both frontends consume the same backend API and persist the latest successful snapshot locally so they can continue to show useful information during outages or offline periods.

The architecture continues to use Clean Architecture across Domain, Application, Infrastructure, and API layers. The key design correction is that a rate snapshot is treated as a consistency boundary containing many individual rate entries, not as one global source value. Each rate entry retains its own currency, normalized rate-to-MDL value, nominal/unit metadata, provider/source, effective timestamp, freshness state, and fallback indicator. Historical analytics are derived from normalized per-currency rate entries rather than storing duplicated pairwise historical tables.

## Technical Context

**Language/Version**: Python 3 (targeted 3.11+), TypeScript (Angular), Dart (Flutter)

**Primary Dependencies**: FastAPI, SQLAlchemy 2, Alembic, Pydantic, httpx, pytest, Angular, Flutter, Microsoft SQL Server, BNM XML integration, CoinGecko-compatible API integration

**Storage**: Microsoft SQL Server with SQLAlchemy ORM and Alembic migrations

**Testing**: pytest for backend tests, Angular unit tests for UI and validation logic, Flutter widget/unit tests for mobile behavior; no test depends on live BNM or CoinGecko services

**Target Platform**: Web app and Android-focused mobile client; Android Studio Emulator used for local demonstration and validation

**Project Type**: Full-stack service with shared API, web frontend, and mobile frontend

**Performance Goals**: Rate refresh and conversion requests should remain fast under normal conditions; cached snapshots should render immediately when the backend is unavailable; analytics should be computed from persisted normalized entries without creating redundant N×N pair storage

**Constraints**: Decimal-safe arithmetic only; no floating-point conversion logic; no direct SQL Server access from frontend; no third-party credentials in frontend code; same-screen values must come from one validated snapshot; invalid input never converts; cached and fallback data must be explicitly labeled

**Scale/Scope**: 18 supported currencies (10 fiat + 8 crypto), 30-day analytical retention, shared API contract across web and mobile clients

## Constitution Check

*GATE: Must pass before implementation. Re-check at the end of design.*

Pass: The implementation plan remains aligned with the constitution and specification.

- Architecture constraint: the backend keeps the required Domain, Application, Infrastructure, and API separation and avoids direct FastAPI, SQLAlchemy, SQL Server, BNM, or CoinGecko dependence in the Domain and Application layers.
- Dependency injection: repositories, providers, cache layers, and rate-resolution strategies will be injected via interfaces and factory logic.
- Data and source rules: fiat and crypto values are normalized into a common internal representation; a snapshot remains a consistent boundary of individual entries; each entry tracks provider source and freshness metadata.
- Financial correctness: all conversions use Decimal arithmetic and a normalized MDL basis, including correct handling of nominal units when provider quotes are based on 10, 100, or 1000 units.
- Offline/cached behavior: last successful backend data is persisted locally in both frontends and the UI must show stale or cached status with the original timestamp.
- Security: credentials remain limited to backend configuration; no secrets are committed; local development uses .env.example and environment variables.
- Git and process: specification and plan remain in place before implementation; work is scoped to the feature branch and review-ready.

## Project Structure

### Documentation (this feature)

```text
specs/001-currencyhub-platform/
├── spec.md              # Product requirements and acceptance scenarios
├── plan.md              # This file
├── research.md          # Decision log and rationale
├── data-model.md        # Persistence and domain model
├── quickstart.md        # Validation and setup guide
├── contracts/
│   └── rates-api.md     # Shared API contract
├── checklists/
│   └── requirements.md  # Requirement quality checklist
└── tasks.md             # Generated later by the tasks workflow
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

**Structure Decision**: The codebase remains split into three workstreams: a shared backend API, an Angular web frontend, and a Flutter mobile frontend. The backend is the source of truth for rate normalization, persistence, and analytics. The frontends are responsible for user interaction, local caching, and API consumption only.

## Domain Model

The domain model will define objects without tying them to infrastructure or HTTP concerns.

### Currency
- code: string
- name: string
- type: Fiat | Crypto
- is_supported: bool

Rules:
- supported codes are restricted to the approved product set
- code is unique
- type is explicit and immutable in the domain model

### RateSnapshot
- snapshot_id: UUID
- captured_at: datetime
- rates: list[RateEntry]

Rules:
- the snapshot is a consistency boundary for a point-in-time rate set
- the snapshot contains individual and independent rate entries
- a refresh must only replace the active snapshot after the entire snapshot validates successfully

### RateEntry
- currency: string
- normalized_rate_to_mdl: Decimal
- nominal_unit: int | null
- provider_name: string
- provider_type: Fiat | Crypto
- effective_at: datetime
- freshness_state: Live | Fallback | Cached
- is_fallback: bool

Rules:
- each rate entry is stored and processed independently
- a single snapshot may contain entries from multiple providers and effective timestamps
- the normalized value is the canonical value for conversion logic
- rate entries with missing weekend or holiday fiat values use previous valid data and mark is_fallback = true

### ProviderInfo
- provider_id
- name
- kind: fiat | crypto
- base_url or config metadata
- active flag

Rules:
- provider metadata is persisted separately from the rate entries
- any source or provider label is traceable back to the rate entry

### AnalyticsSummary
- base_currency
- quote_currency
- period: 7d | 30d
- points: list[HistoricalPoint]
- minimum
- maximum
- average
- absolute_change
- percentage_change
- trend: GROWTH | DECLINE | UNCHANGED
- provenance_summary: provider and freshness aggregates across the period

Rules:
- trend is derived explicitly from first and last available values
- provenance_summary must preserve source-side and target-side provider sets and counts for live, fallback, and cached rate entries
- empty datasets produce an empty-state response instead of exceptions

### HistoricalPoint
- date: date
- value: Decimal
- rate_context: provenance for the source and target RateEntry values and their shared snapshot_id

Rules:
- each point retains both currencies' provider, effective timestamp, freshness state, and fallback status
- pair values are derived from the two normalized rates in the referenced snapshot

## Database Model

The database persists rate data without storing personal user data or redundant pairwise historical records.

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
   - created_at

3. rate_entries
   - id
   - snapshot_id (FK)
   - currency_code
   - normalized_rate_to_mdl
   - nominal_unit
   - provider_name
   - provider_type
   - effective_at
   - freshness_state
   - is_fallback
   - created_at

4. provider_sources
   - id
   - provider_name
   - provider_type
   - config_reference
   - is_active
   - created_at

5. analytics_cache (optional)
   - id
   - pair_key
   - period
   - payload
   - generated_at

### Historical analytics rule
Historical pair values are not stored as a separate N×N pair matrix. Instead, historical analytics are computed by reading stored normalized rate entries and deriving the requested pair from:

amount × source_rate_to_mdl / target_rate_to_mdl

This keeps one source of truth and avoids duplicated pairwise storage.

### Historical bootstrap rule
On initial setup or first required synchronization, the backend must backfill up to the previous 30 days of available fiat and crypto history before the analytics screens are expected to be fully useful. The bootstrap process:
- fetches up to 30 days of historical fiat values from BNM
- fetches up to 30 days of historical crypto values from CoinGecko or an equivalent documented API
- normalizes both sets to the common internal rate-to-MDL representation
- stores them as rate entries under snapshots at each available time point
- applies the weekend/holiday fallback rule to fiat history where the last valid published rate is reused
- after bootstrap, normal synchronization continues to add new rate entries and snapshots

## REST API Design

The API is versioned under `/api/v1` and the contracts are aligned across the backend and both clients.

### GET /api/v1/currencies
Purpose: return the supported currencies and metadata.

Request: none

Response:
```json
{
  "currencies": [
    {
      "code": "USD",
      "name": "US Dollar",
      "type": "fiat",
      "is_supported": true
    }
  ]
}
```

### GET /api/v1/rates/latest
Purpose: return the most recent validated snapshot containing all current rate entries.

Request: none

Response:
```json
{
  "snapshot_id": "uuid",
  "captured_at": "2026-10-02T12:00:00Z",
  "rates": [
    {
      "currency": "USD",
      "normalized_rate_to_mdl": "17.40",
      "nominal_unit": 1,
      "provider_name": "BNM",
      "provider_type": "fiat",
      "effective_at": "2026-10-02T09:00:00Z",
      "freshness_state": "live",
      "is_fallback": false
    },
    {
      "currency": "BTC",
      "normalized_rate_to_mdl": "542240.10",
      "nominal_unit": 1,
      "provider_name": "CoinGecko",
      "provider_type": "crypto",
      "effective_at": "2026-10-02T10:00:00Z",
      "freshness_state": "live",
      "is_fallback": false
    }
  ]
}
```

Notes:
- the response does not model a single global source_name or source_type for the entire snapshot
- individual rate entries may come from different providers and different effective timestamps
- freshness metadata is tracked per entry

### POST /api/v1/convert
Purpose: convert one amount from a source currency to a target currency using the same validated snapshot.

Request:
```json
{
  "amount": "100.00",
  "source_currency": "EUR",
  "target_currency": "BTC"
}
```

Response:
```json
{
  "source_amount": "100.00",
  "converted_amount": "0.00347",
  "source_currency": "EUR",
  "target_currency": "BTC",
  "rate_value": "0.0000347",
  "rate_context": {
    "source_rate": {
      "currency": "EUR",
      "provider_name": "BNM",
      "effective_at": "2026-10-02T09:00:00Z",
      "freshness_state": "live",
      "is_fallback": false
    },
    "target_rate": {
      "currency": "BTC",
      "provider_name": "CoinGecko",
      "effective_at": "2026-10-02T09:30:00Z",
      "freshness_state": "live",
      "is_fallback": false
    },
    "snapshot_id": "uuid"
  }
}
```

Business rules:
- invalid input is rejected before conversion
- same-currency conversion returns the original amount
- conversion must use one consistent snapshot at one point in time
- `rate_value` is the derived pair rate and must not imply a single provider for the result
- `rate_context` identifies both rate entries used, including independent providers, effective timestamps, and freshness states

### GET /api/v1/history
Purpose: return historical values for a selected source and target currency over a requested period.

Query parameters:
- base_currency
- quote_currency
- period (7d | 30d)

Response:
```json
{
  "base_currency": "EUR",
  "quote_currency": "BTC",
  "period": "7d",
  "points": [
    {
      "date": "2026-09-26",
      "value": "0.0000321",
      "rate_context": {
        "source_rate": {
          "currency": "EUR",
          "provider_name": "BNM",
          "effective_at": "2026-09-26T09:00:00Z",
          "freshness_state": "live",
          "is_fallback": false
        },
        "target_rate": {
          "currency": "BTC",
          "provider_name": "CoinGecko",
          "effective_at": "2026-09-26T09:30:00Z",
          "freshness_state": "live",
          "is_fallback": false
        },
        "snapshot_id": "uuid"
      }
    }
  ],
  "empty": false
}
```

If there is no available history, return:
```json
{
  "base_currency": "USD",
  "quote_currency": "EUR",
  "period": "30d",
  "points": [],
  "empty": true,
  "message": "No historical data available for this pair in the selected period."
}
```

### GET /api/v1/analytics
Purpose: return summary statistics and trend data for a selected pair and period.

Query parameters:
- base_currency
- quote_currency
- period (7d | 30d)

Response:
```json
{
  "base_currency": "EUR",
  "quote_currency": "BTC",
  "period": "7d",
  "points": [
    { "date": "2026-09-26", "value": "0.0000318" },
    { "date": "2026-09-27", "value": "0.0000322" }
  ],
  "minimum": "0.0000310",
  "maximum": "0.0000330",
  "average": "0.0000320",
  "absolute_change": "0.0000004",
  "percentage_change": "1.26",
  "trend": "GROWTH",
  "provenance_summary": {
    "point_count": 7,
    "source_providers": ["BNM"],
    "target_providers": ["CoinGecko"],
    "rate_entry_freshness_counts": {
      "live": 14,
      "fallback": 0,
      "cached": 0
    },
    "fallback_entry_count": 0
  },
  "empty": false
}
```

Business rules:
- trend is calculated as first-to-last available value comparison
- empty datasets return an explicit empty-state response
- provenance summary reports source-side and target-side provider sets and freshness counts across all rate entries used in the period; it must not collapse mixed provenance into one source state

### POST /api/v1/rates/refresh
Purpose: trigger a synchronization cycle without requiring a frontend refresh action.

Request: optional provider or scope information, but not required for the default implementation.

Response:
```json
{
  "snapshot_id": "uuid",
  "captured_at": "2026-10-02T12:00:00Z",
  "updated": true,
  "rate_count": 18,
  "freshness_summary": {
    "live": 16,
    "fallback": 2,
    "cached": 0
  }
}
```

### GET /api/v1/health
Purpose: report service health and external dependency status.

Response:
```json
{
  "status": "ok",
  "backend": "healthy",
  "providers": {
    "BNM": "healthy",
    "CoinGecko": "healthy"
  },
  "last_successful_snapshot": "2026-10-02T12:00:00Z"
}
```

### All-currencies snapshot pattern
The all-currencies view will use the latest validated snapshot and the frontend will compute visible values from that single snapshot. The API returns a snapshot containing individual rate entries, each with provider and freshness metadata, ensuring all displayed values start from the same consistency boundary.

## External Provider Integration

### Provider Architecture
The backend uses adapters and a shared abstraction for external sources.

**Common abstraction**
- RateProvider interface
- fetch_latest_rates()
- fetch_historical_rates(currency_codes, period)
- get_metadata()

**Implementations**
- BnmRateProvider / BnmRateAdapter
- CoinGeckoRateProvider / CoinGeckoRateAdapter

### BNM integration
- fetch XML exchange-rate data from the National Bank of Moldova
- normalize to common internal representation with correct nominal-unit handling
- compute a normalized rate-to-MDL value per supported currency
- when data is missing for weekends or holidays, use the last valid prior rate and mark the entry as fallback

### Crypto integration
- fetch current and historical JSON data from CoinGecko or equivalent documented provider
- normalize crypto quotes to the same canonical internal representation
- persist rate entries per timestamp and currency so history can be rederived for analytics

### Provider Patterns
- Adapter: BNM and crypto provider integrations
- Strategy: fallback and refresh logic, especially weekend/holiday rules
- Factory Method: choose the correct provider for fiat or crypto data
- Facade: application-layer service exposes current rates, conversion, all-currencies calculations, and analytics
- Repository: persistence behind domain/application interfaces
- Unit of Work: transactional consistency when snapshot and entry updates must commit atomically

## Caching and Fallback Design

### Backend resilience
- the backend attempts a live refresh from configured providers
- valid snapshots are persisted as the latest normalized records
- if a refresh fails, the previous valid snapshot remains available and is not discarded
- when weekend or holiday BNM rates are missing, the latest valid prior rate is reused and flagged as fallback
- every rate entry stores its own freshness state and fallback flag

### Frontend resilience
- Web: Angular stores the latest successful backend snapshot in browser local storage
- Mobile: Flutter keeps the last successful snapshot in persistent local storage
- when network or backend connectivity fails, both clients use the local cached snapshot
- cached and stale rows show the original timestamp and source metadata
- no client silently presents cached data as fresh

### Data freshness rules
- live: data from the latest accepted source refresh
- fallback: reused previous valid rate for a known gap such as weekend/holiday
- cached: data stored locally and used because live backend data is unavailable

## Financial Calculation Design

All conversions and analytics use Decimal arithmetic and a normalized internal rate basis.

### Normalized model
For each currency, normalize to:
- 1 unit of currency = X MDL

Then conversion between arbitrary currencies uses:

amount × source_rate_to_mdl / target_rate_to_mdl

This supports:
- fiat → fiat
- fiat → crypto
- crypto → fiat
- crypto → crypto
- same currency → same currency

### Nominal-unit handling
Each rate entry stores nominal_unit information so rates quoted per 10, 100, or 1000 units are handled correctly before the conversion formula is applied.

### Same-currency behavior
When source_currency equals target_currency, the result is the original amount, while the entry still retains source and freshness metadata.

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
- core API layer: typed services for `/api/v1` resources
- core storage: browser-local persistence of latest successful snapshot
- converter feature: classic conversion and validation flows
- rates feature: current rate list and freshness metadata display
- analytics feature: 7-day and 30-day charts and summary statistics
- shared: formatting, validation, and charting utilities

### UI requirements
- responsive layouts for classic converter, all-currencies converter, current rates, and analytics screens
- no direct SQL or provider access
- fresh, cached, and fallback values are clearly identified with timestamps and provider source labels

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
- core API: Dio or equivalent HTTP client configured for backend communication
- core cache: persistent local storage for last successful snapshot
- state management: BLoC/Cubit for converter, rates, and analytics views
- charts: library appropriate for time-series 7-day and 30-day analytics
- offline support: continue to work with last successful cached snapshot and show stale/fallback state

### Android emulator networking
Because localhost inside the Android Emulator does not resolve to the Windows host, the backend URL for local development must use the host machine address appropriate to the environment.

Recommended approach:
- Angular uses the workstation host address or a configured local backend URL
- Flutter app uses `10.0.2.2` for Android emulator development or a host IP if required by the environment

This must be documented in local setup so the emulator can reach the backend reliably.

## Testing Strategy

### Backend tests
The backend test suite will use fake or mock provider implementations and must never call live providers.

**Required unit test coverage**:
- BNM XML parsing
- crypto JSON parsing
- BNM nominal-unit normalization
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
- integration tests for persistence and provider fallback flows
- API contract tests for request/response behavior

### Frontend tests
- validation tests for invalid amounts and required fields
- conversion presentation tests for output formatting and source visibility
- cached-data indicators for stale, fallback, and local cache states
- analytics presentation tests for high-level summary values and trend labels

## Configuration and Security

### Environment configuration
The backend and frontend use environment variables and sample configuration files. `.env.example` will contain placeholders only; no secrets are committed.

Required values:
- SQL Server connection string
- BNM endpoint settings
- CoinGecko provider configuration
- CORS allowed origins for local development

### Security requirements
- no SQL Server password in Git
- no API keys or tokens in frontend code
- third-party credentials remain on backend only
- no direct database or external provider access from either frontend

### CORS for local development
The backend configuration must allow Angular local development and local Flutter testing. CORS is restricted to development origins only and avoids broad wildcard settings in non-local environments.

## Local Development Workflow (Windows)

The plan assumes a Windows setup with the following flows:

1. Backend
   - create a local Python virtual environment
   - install dependencies from `requirements.txt`
   - set environment variables in `.env`
   - run FastAPI locally with uvicorn or equivalent
   - apply Alembic migrations to SQL Server

2. Web frontend
   - install Angular dependencies in `web/`
   - configure the API base URL to the local backend
   - run the Angular dev server
   - confirm CORS permits local browser requests

3. Mobile frontend
   - install Flutter dependencies in `mobile/`
   - run the Flutter app on the Android Emulator
   - target the backend through the correct emulator host address
   - verify offline and cached snapshot behavior

### Practical development notes
- each project is runnable independently
- backend must be started before testing real API flows from the clients
- both frontends share the same contract and freshness semantics
- local validation should confirm emulator/browser connectivity without production credentials

## Implementation Phases

### Phase 0 – Environment and API contract setup
- initialize backend, web, and mobile project folders
- define env files and local development settings
- finalize the `/api/v1` contract and shared data models
- establish the feature branch and review workflow

### Phase 1 – Backend domain and conversion rules
- create core domain entities and value objects
- define repository and provider interfaces
- implement conversion rules and validation logic with Decimal arithmetic
- implement normalized rate-to-MDL representation and nominal-unit handling

### Phase 2 – Persistence and provider adapters
- create SQLAlchemy models and Alembic migration scripts
- implement repository and Unit of Work patterns
- implement BNM and CoinGecko adapters with a common provider abstraction
- add strategy-based fallback and refresh selection logic

### Phase 3 – API and resilience layer
- implement FastAPI routers and schemas
- expose currencies, latest rates, conversion, history, analytics, refresh, and health endpoints
- persist snapshots and per-currency rate entries
- include source and freshness metadata in API responses

### Phase 4 – Historical bootstrap and analytics pipeline
- implement initial 30-day historical backfill for fiat and crypto data
- normalize and persist historical snapshots as rate entries
- derive pair analytics from normalized rate entries using the conversion formula
- handle empty historical datasets with clear empty-state behavior

### Phase 5 – Angular web client
- implement typed API services and local storage cache
- create classic converter, all-currencies, rates, and analytics screens
- show stale and cached states alongside original timestamps
- validate conversion and multi-currency behavior

### Phase 6 – Flutter mobile client
- implement Dio-based API client and persistent cache
- create BLoC/Cubit-based state management for currency screens
- add offline behavior and chart views for 7-day and 30-day analytics
- validate app behavior on Android Studio Emulator

### Phase 7 – Testing and release readiness
- run backend unit and integration tests with fake providers
- run frontend validation tests
- verify empty-state, fallback, and analytics behavior
- confirm all spec acceptance criteria and constitution requirements are met

## Complexity Tracking

No constitution violation requires an exception. The design stays within the approved architecture while correcting the earlier snapshot and historical-data issues by making snapshots a collection of independently tracked rate entries and storing one normalized data source for analytics derivation.

