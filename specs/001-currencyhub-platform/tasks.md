---
description: "Task list for CurrencyHub implementation"
---

# Tasks: CurrencyHub

**Input**: Design documents from `/specs/001-currencyhub-platform/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: Test tasks are included because the project constitution requires provider-independent backend tests and frontend presentation/validation coverage. Tests must use fake or mocked providers and must not call live BNM or CoinGecko services.

**Organization**: Tasks are grouped by the five user stories in priority order. Application code is not implemented by this task-generation artifact.

## Format

Every task uses `- [ ] T### [P?] [Story?] Description with file path`. `[P]` marks tasks that can proceed independently in different files; user-story tasks carry their corresponding `[US#]` label.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the three project workspaces and safe local configuration foundations.

- [ ] T001 [P] Initialize the FastAPI backend package, pytest configuration, Alembic environment, and application entry point in `backend/requirements.txt`, `backend/pytest.ini`, `backend/alembic/env.py`, and `backend/app/main.py`
- [ ] T002 [P] Scaffold the Angular application and its test/build configuration in `web/package.json`, `web/angular.json`, and `web/src/app/app-routing.module.ts`
- [ ] T003 [P] Scaffold the Flutter application and analyzer/test configuration in `mobile/pubspec.yaml`, `mobile/analysis_options.yaml`, and `mobile/lib/main.dart`
- [ ] T004 Add placeholder-only SQL Server, BNM, CoinGecko, and CORS settings and secret exclusions in `backend/.env.example` and `.gitignore`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish domain, persistence, provider, API, and shared-client foundations required by all stories.

- [ ] T005 Implement environment-backed backend settings, structured logging, and local CORS configuration in `backend/app/core/config/settings.py` and `backend/app/core/logging/logger.py`
- [ ] T006 [P] Define currency-type and per-entry freshness enums in `backend/app/domain/enums/currency_type.py` and `backend/app/domain/enums/freshness_state.py`
- [ ] T007 Create the Currency domain entity with unique code and supported-currency validation in `backend/app/domain/entities/currency.py`
- [ ] T008 Create RateSnapshot and RateEntry domain entities, preserving per-entry provider, effective timestamp, freshness, nominal-unit, and fallback fields in `backend/app/domain/entities/rate_snapshot.py` and `backend/app/domain/entities/rate_entry.py`
- [ ] T009 Create Decimal-safe money and normalized rate value objects with positive-rate and finite-amount validation in `backend/app/domain/value_objects/money.py` and `backend/app/domain/value_objects/normalized_rate.py`
- [ ] T010 Define currency/rate repository, rate-provider, and unit-of-work interfaces in `backend/app/domain/interfaces/currency_repository.py`, `backend/app/domain/interfaces/rate_repository.py`, `backend/app/domain/interfaces/rate_provider.py`, and `backend/app/domain/interfaces/unit_of_work.py`
- [ ] T011 Map currencies, snapshots, rate entries, and provider sources to SQLAlchemy models without adding pairwise historical-rate storage in `backend/app/infrastructure/database/models.py`
- [ ] T012 Create the initial Alembic migration for currencies, rate_snapshots, rate_entries, and provider_sources and seed the 18 supported currencies in `backend/alembic/versions/001_initial_rate_schema.py` and `backend/app/infrastructure/database/seed_currencies.py`
- [ ] T013 Implement SQL Server repositories and transactional unit-of-work behavior for snapshots and entries in `backend/app/infrastructure/repositories/currency_repository.py`, `backend/app/infrastructure/repositories/rate_repository.py`, and `backend/app/infrastructure/database/unit_of_work.py`
- [ ] T014 [P] Implement BNM XML parsing, nominal-unit normalization, and fiat provider metadata in `backend/app/infrastructure/providers/bnm_rate_provider.py`
- [ ] T015 [P] Implement CoinGecko-compatible current-rate JSON parsing, normalization, and crypto provider metadata in `backend/app/infrastructure/providers/coingecko_rate_provider.py`
- [ ] T016 Implement provider construction and atomic multi-provider snapshot assembly with per-entry provenance in `backend/app/infrastructure/providers/provider_factory.py` and `backend/app/application/services/snapshot_service.py`
- [ ] T017 Configure FastAPI dependency injection, common error handling, backend startup, and provider/repository wiring in `backend/app/api/dependencies.py`, `backend/app/api/exception_handlers.py`, and `backend/app/main.py`
- [ ] T018 [P] Define shared typed rate, snapshot, and provenance models plus an Angular HTTP client in `web/src/app/core/models/rate.models.ts` and `web/src/app/core/api/rates-api.service.ts`
- [ ] T019 [P] Define shared rate, snapshot, and provenance models plus a Flutter HTTP client in `mobile/lib/core/models/rate_models.dart` and `mobile/lib/core/api/rates_api_client.dart`
- [ ] T020 Create reusable fake BNM/CoinGecko providers and isolated SQL Server repository test fixtures in `backend/tests/conftest.py` and `backend/tests/fixtures/fake_rate_providers.py`

**Checkpoint**: Shared infrastructure is ready; story phases can begin subject to the dependency graph below.

---

## Phase 3: User Story 1 - View Current Market Data (Priority: P1)

**Goal**: Open either client without sign-in and inspect supported currencies, latest validated rates, source metadata, and freshness.

**Independent Test**: Against fake provider data, load supported currencies and one complete latest snapshot in either client; all rows show currency identity, normalized value, source, effective timestamp, and freshness state without account creation.

- [ ] T021 [US1] Implement supported-currency listing and latest-snapshot retrieval use cases in `backend/app/application/use_cases/list_currencies.py` and `backend/app/application/use_cases/get_latest_snapshot.py`
- [ ] T022 [US1] Define currency/latest-rate response schemas and implement `GET /api/v1/currencies` and `GET /api/v1/rates/latest` in `backend/app/api/schemas/currency.py`, `backend/app/api/schemas/rates.py`, and `backend/app/api/routers/rates.py`
- [ ] T023 [US1] Implement provider and backend health reporting for `GET /api/v1/health` in `backend/app/api/schemas/health.py` and `backend/app/api/routers/health.py`
- [ ] T024 [US1] Add backend unit and API contract tests for BNM XML/CoinGecko JSON parsing, nominal-unit normalization, empty/malformed provider responses, supported currencies, and latest-snapshot provenance in `backend/tests/unit/test_rate_provider_parsing.py` and `backend/tests/contract/test_latest_rates_api.py`
- [ ] T025 [P] [US1] Build the Angular current-rates view with currency identity and per-entry source/freshness display in `web/src/app/features/rates/current-rates.component.ts` and `web/src/app/features/rates/current-rates.component.html`
- [ ] T026 [US1] Add Angular presentation tests for current-rate values and provider/freshness labels in `web/tests/current-rates.component.spec.ts`
- [ ] T027 [P] [US1] Build the Flutter current-rates screen with currency identity and per-entry source/freshness display in `mobile/lib/features/rates/presentation/current_rates_screen.dart`
- [ ] T028 [US1] Add Flutter widget tests for current-rate values and provider/freshness labels in `mobile/test/features/rates/current_rates_screen_test.dart`

**Checkpoint**: User Story 1 is independently usable in web and mobile.

---

## Phase 4: User Story 2 - Convert One Amount (Priority: P1)

**Goal**: Convert a valid amount between supported currencies and expose the exact source and target rate provenance used.

**Independent Test**: With a validated fake snapshot containing EUR from BNM and BTC from CoinGecko, convert EUR to BTC and inspect the derived pair rate plus both rate entries' provider, effective timestamp, freshness, fallback flag, and shared snapshot ID; invalid and same-currency cases have defined outcomes.

- [ ] T029 [US2] Implement conversion input validation and Decimal-based normalized-rate conversion, including same-currency pass-through, in `backend/app/application/use_cases/convert_currency.py`
- [ ] T030 [US2] Define conversion request/result schemas and implement `POST /api/v1/convert` with both rate contexts and snapshot ID in `backend/app/api/schemas/conversion.py` and `backend/app/api/routers/conversion.py`
- [ ] T031 [US2] Add backend unit and contract tests for fiat/fiat, fiat/crypto, crypto/fiat, crypto/crypto, reverse, same-currency, invalid amounts, and both-leg provenance in `backend/tests/unit/test_conversion.py` and `backend/tests/contract/test_conversion_api.py`
- [ ] T032 [P] [US2] Build the Angular classic converter with validation feedback and per-leg result provenance in `web/src/app/features/converter/converter.component.ts` and `web/src/app/features/converter/converter.component.html`
- [ ] T033 [US2] Add Angular converter tests for invalid input, result formatting, same-currency behavior, and both-leg provenance labels in `web/tests/converter.component.spec.ts`
- [ ] T034 [P] [US2] Build the Flutter classic converter with validation feedback and per-leg result provenance in `mobile/lib/features/converter/presentation/converter_screen.dart`
- [ ] T035 [US2] Add Flutter converter widget tests for invalid input, same-currency behavior, and per-leg provenance labels in `mobile/test/features/converter/converter_screen_test.dart`

**Checkpoint**: User Story 2 is independently usable in both clients and does not misattribute mixed-provider conversions.

---

## Phase 5: User Story 3 - Compare Many Currencies (Priority: P1)

**Goal**: Recalculate all visible currencies from one validated snapshot when the user enters an amount in any currency.

**Independent Test**: From one latest snapshot, enter a value in different currency fields and confirm all displayed amounts correspond to that same snapshot, with decimal-safe calculations and each rate's freshness visible.

- [ ] T036 [P] [US3] Add a decimal-safe TypeScript calculation service for normalized rate entries and include its decimal dependency in `web/package.json` and `web/src/app/features/rates/all-currencies.service.ts`
- [ ] T037 [P] [US3] Build the Angular all-currencies comparison screen using one snapshot for all visible values in `web/src/app/features/rates/all-currencies.component.ts` and `web/src/app/features/rates/all-currencies.component.html`
- [ ] T038 [US3] Add Angular tests for source-currency switching, decimal-safe recalculation, and single-snapshot consistency in `web/tests/all-currencies.component.spec.ts`
- [ ] T039 [P] [US3] Add a decimal package and decimal-safe normalized-rate comparison service in `mobile/pubspec.yaml` and `mobile/lib/features/rates/domain/all_currencies_calculator.dart`
- [ ] T040 [P] [US3] Build the Flutter all-currencies comparison screen using one snapshot for all visible values in `mobile/lib/features/rates/presentation/all_currencies_screen.dart`
- [ ] T041 [US3] Add Flutter widget tests for source-currency switching and single-snapshot consistency in `mobile/test/features/rates/all_currencies_screen_test.dart`

**Checkpoint**: User Story 3 recalculates the complete visible comparison from one snapshot on both clients.

---

## Phase 6: User Story 4 - Review Historical Performance (Priority: P2)

**Goal**: Show 7-day and 30-day pair history and analytics derived from normalized per-currency entries, including mixed-provider provenance.

**Independent Test**: Seed fake normalized history for both legs of a supported pair, request both windows, and receive ordered pair points with both rate contexts plus minimum, maximum, average, change, trend, and aggregate provider/freshness provenance; empty history returns the documented empty state.

- [ ] T042 [P] [US4] Add BNM historical-rate fetching and XML/date normalization for the 30-day bootstrap in `backend/app/infrastructure/providers/bnm_rate_provider.py`
- [ ] T043 [P] [US4] Add CoinGecko-compatible historical-rate fetching and timestamp normalization for the 30-day bootstrap in `backend/app/infrastructure/providers/coingecko_rate_provider.py`
- [ ] T044 [US4] Implement first-run historical bootstrap for up to 30 available days and persist normalized per-currency entries under snapshots in `backend/app/application/use_cases/bootstrap_history.py`
- [ ] T045 [US4] Implement historical entry queries and derive pair points and analytics provenance from normalized rates without pairwise storage in `backend/app/infrastructure/repositories/rate_repository.py` and `backend/app/application/services/analytics_service.py`
- [ ] T046 [US4] Define history/analytics schemas and implement `GET /api/v1/history` and `GET /api/v1/analytics`, including empty-state responses and per-point rate contexts, in `backend/app/api/schemas/analytics.py` and `backend/app/api/routers/analytics.py`
- [ ] T047 [US4] Add backend tests for historical bootstrap, pair derivation, both rate-entry contexts, 7-day/30-day summaries, mixed freshness counts, and empty history in `backend/tests/unit/test_analytics_service.py` and `backend/tests/contract/test_analytics_api.py`
- [ ] T048 [P] [US4] Build Angular 7-day/30-day analytics views and provenance summaries in `web/src/app/features/analytics/analytics.component.ts` and `web/src/app/features/analytics/analytics.component.html`
- [ ] T049 [US4] Add Angular tests for analytics metrics, empty state, period selection, and provider/freshness summaries in `web/tests/analytics.component.spec.ts`
- [ ] T050 [P] [US4] Build Flutter 7-day/30-day analytics views and provenance summaries in `mobile/lib/features/analytics/presentation/analytics_screen.dart`
- [ ] T051 [US4] Add Flutter widget tests for analytics metrics, empty state, period selection, and provider/freshness summaries in `mobile/test/features/analytics/analytics_screen_test.dart`

**Checkpoint**: User Story 4 works from bootstrapped or continuing history and preserves source/target provenance for each pair point.

---

## Phase 7: User Story 5 - Use CurrencyHub Offline or During Source Failures (Priority: P2)

**Goal**: Retain access to the last successful data and clearly distinguish live, fallback, and locally cached states.

**Independent Test**: With fake provider/network failures, retain the last validated backend snapshot, reuse prior BNM values for weekend/holiday gaps as fallback, and show locally cached data after each client restarts offline with original timestamps and per-entry provenance.

- [ ] T052 [US5] Implement refresh orchestration that atomically accepts valid snapshots and retains the prior snapshot on provider failure, with per-entry fallback metadata, in `backend/app/application/use_cases/refresh_rates.py`
- [ ] T053 [US5] Implement `POST /api/v1/rates/refresh` response counts and refresh error semantics in `backend/app/api/schemas/refresh.py` and `backend/app/api/routers/rates.py`
- [ ] T054 [US5] Add backend tests for BNM weekend/holiday fallback, partial provider failure, cached latest snapshot, and no partial snapshot replacement in `backend/tests/integration/test_rate_refresh_resilience.py`
- [ ] T055 [P] [US5] Implement persistent Angular latest-snapshot storage and offline rehydration with original per-entry metadata in `web/src/app/core/storage/rate-snapshot-store.service.ts`
- [ ] T056 [US5] Add Angular tests for offline cache recovery and explicit cached/stale/fallback labels in `web/tests/rate-snapshot-store.service.spec.ts`
- [ ] T057 [P] [US5] Implement persistent Flutter latest-snapshot storage and offline rehydration with original per-entry metadata in `mobile/lib/core/cache/rate_snapshot_store.dart`
- [ ] T058 [US5] Add Flutter tests for cache survival after restart and explicit cached/stale/fallback labels in `mobile/test/core/cache/rate_snapshot_store_test.dart`

**Checkpoint**: User Story 5 preserves previously successful data and communicates freshness independently for each rate entry.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Complete local setup, security, and shared-contract validation after the desired stories are implemented.

- [ ] T059 Document backend, Angular, and Android Emulator startup, host URLs, migrations, and validation scenarios in `specs/001-currencyhub-platform/quickstart.md`
- [ ] T060 Review environment configuration, CORS restrictions, and secret exclusions against the project constitution in `backend/.env.example`, `backend/app/core/config/settings.py`, and `.gitignore`
- [ ] T061 Run the quickstart scenarios for web and mobile, record any remaining acceptance gaps, and reconcile the shared endpoint/metadata descriptions in `specs/001-currencyhub-platform/quickstart.md` and `specs/001-currencyhub-platform/contracts/rates-api.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies; the backend, web, and mobile scaffolds can start in parallel.
- **Foundational (Phase 2)**: Depends on setup completion and blocks every user story. Domain contracts precede ORM/repository and provider implementations; API and client foundations follow the shared models.
- **User Stories (Phases 3-7)**: Depend on the foundational phase. US1, US2, and US4 can begin independently after foundations; US3 and US5 require the latest-snapshot capability from US1.
- **Polish (Phase 8)**: Depends on all selected stories and their validation tasks.

### User Story Dependencies

- **US1 (P1)**: Starts after Phase 2. Provides current rates and snapshot retrieval; this is the suggested MVP.
- **US2 (P1)**: Starts after Phase 2; uses the shared snapshot/repository foundation but does not require US1 UI completion.
- **US3 (P1)**: Starts after Phase 2 and depends on the US1 latest-snapshot endpoint contract.
- **US4 (P2)**: Starts after Phase 2; historical adapters, bootstrap, and analytics can proceed independently of client conversion screens.
- **US5 (P2)**: Starts after Phase 2 and depends on US1 snapshot retrieval and refresh orchestration.

### Parallel Opportunities

- Setup: T001, T002, and T003 are independent project scaffolds.
- Foundation: T006 can proceed independently; T014 and T015 can proceed in parallel after T010; T018 and T019 can proceed in parallel after shared API models are agreed.
- US1: T025 and T027 can proceed in parallel after the latest-rates contract is stable.
- US2: T032 and T034 can proceed in parallel after the conversion contract is stable.
- US3: the TypeScript and Dart decimal-safe calculation tasks T036 and T039 can proceed in parallel; client screens T037 and T040 can then proceed in parallel.
- US4: historical provider tasks T042 and T043 are parallel; Angular and Flutter views T048 and T050 are parallel after the response contract is stable.
- US5: Angular and Flutter persistence tasks T055 and T057 are parallel after freshness semantics are finalized.

### Parallel Execution Examples

```text
After Phase 1: T001 + T002 + T003
After T010: T014 + T015
After the shared API contracts: T025 + T027; T032 + T034
After Phase 2 and T021/T022: T036 + T039; T042 + T043
After analytics API schema: T048 + T050
After refresh/freshness semantics: T055 + T057
```

## Implementation Strategy

### MVP First

1. Complete Phase 1 setup and Phase 2 foundations.
2. Complete Phase 3, User Story 1, as the initial useful product increment for current rates.
3. Validate US1 independently against its fake-provider criterion before expanding scope.
4. Add US2 and US3 for conversion workflows, then US4 and US5 for analytics and resilience.

### Incremental Delivery

Deliver and validate each story independently after the foundation. User Stories 1 and 2 are the first P1 increments; US3 follows the shared snapshot API; US4 and US5 add historical analytics and offline resilience. Preserve the shared API contract and per-entry provenance semantics across every increment.
