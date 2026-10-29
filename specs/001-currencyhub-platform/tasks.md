---
description: "Task list for CurrencyHub implementation"
---

# Tasks: CurrencyHub

**Input**: Design documents from `/specs/001-currencyhub-platform/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: Required by the project constitution and feature specification. All backend tests MUST use fake or mocked BNM and CoinGecko-compatible providers; automated tests MUST NOT call live providers.

**Organization**: Tasks are grouped by the five user stories in priority order. Implementation tasks are specific to their story; shared domain, persistence, provider, and client foundations are established first.

## Format

Every task follows `- [ ] T### [P?] [Story?] Description with file path`. `[P]` marks tasks that can proceed independently in different files. User-story tasks carry the corresponding `[US#]` label. Requirement and success-criterion IDs in task descriptions provide traceability.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the three project workspaces and safe local configuration foundations.

- [x] T001 [P] Initialize the FastAPI backend package, pytest configuration, Alembic environment, and application entry point in `backend/requirements.txt`, `backend/pytest.ini`, `backend/alembic/env.py`, and `backend/app/main.py`
- [x] T002 [P] Scaffold the Angular application and its test/build configuration in `web/package.json`, `web/angular.json`, and `web/src/app/app-routing.module.ts`
- [x] T003 [P] Scaffold the Flutter application and analyzer/test configuration in `mobile/pubspec.yaml`, `mobile/analysis_options.yaml`, and `mobile/lib/main.dart`
- [x] T004 Add placeholder-only SQL Server, BNM, CoinGecko-compatible provider, and CORS settings plus secret exclusions in `backend/.env.example` and `.gitignore`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish domain, persistence, provider, API, and shared-client foundations required by all stories.

- [x] T005 Implement environment-backed backend settings, structured logging, and local CORS configuration in `backend/app/core/config/settings.py` and `backend/app/core/logging/logger.py`
- [x] T006 [P] Define currency-type and primary freshness-state enums; `freshness_state` MUST allow only `live`, `fallback`, or `cached`, with stale represented separately, in `backend/app/domain/enums/currency_type.py` and `backend/app/domain/enums/freshness_state.py`
- [x] T007 Create the Currency domain entity with unique code and supported-currency validation in `backend/app/domain/entities/currency.py`
- [x] T008 Create RateSnapshot and RateEntry domain entities with normalized MDL values, provider provenance, original effective timestamps, primary freshness state, separate `is_fallback`, and separate source-aware `is_stale` in `backend/app/domain/entities/rate_snapshot.py` and `backend/app/domain/entities/rate_entry.py`
- [x] T009 Create Decimal-safe money and normalized-rate value objects with positive-rate and finite-amount validation in `backend/app/domain/value_objects/money.py` and `backend/app/domain/value_objects/normalized_rate.py`
- [x] T010 Define currency/rate repository, rate-provider, and unit-of-work interfaces in `backend/app/domain/interfaces/currency_repository.py`, `backend/app/domain/interfaces/rate_repository.py`, `backend/app/domain/interfaces/rate_provider.py`, and `backend/app/domain/interfaces/unit_of_work.py`
- [x] T011 Map currencies, snapshots, rate entries, and provider sources to SQLAlchemy models without adding pairwise historical-rate storage or persisting derived `is_stale` in `backend/app/infrastructure/database/models.py`
- [x] T012 Create the initial Alembic migration for currencies, rate_snapshots, rate_entries, and provider_sources and seed the 18 supported currencies in `backend/alembic/versions/001_initial_rate_schema.py` and `backend/app/infrastructure/database/seed_currencies.py`
- [x] T013 Implement SQL Server repositories and transactional unit-of-work behavior that can atomically persist and activate complete snapshots in `backend/app/infrastructure/repositories/currency_repository.py`, `backend/app/infrastructure/repositories/rate_repository.py`, and `backend/app/infrastructure/database/unit_of_work.py`
- [x] T014 [P] Implement BNM XML parsing, nominal-unit normalization, and per-entry fiat provider metadata in `backend/app/infrastructure/providers/bnm_rate_provider.py`
- [x] T015 [P] Implement CoinGecko-compatible current-rate JSON parsing, normalization, and per-entry crypto provider metadata in `backend/app/infrastructure/providers/coingecko_rate_provider.py`
- [x] T016 Implement provider construction and snapshot assembly that validates readability, positive valid rates, all required currencies, provider provenance, and effective timestamps; accept missing data only from permitted fallback or a previously successful usable entry, preserving reused-entry timestamps and metadata, in `backend/app/infrastructure/providers/provider_factory.py` and `backend/app/application/services/snapshot_service.py`
- [x] T017 Configure FastAPI dependency injection, common error handling, startup, and provider/repository wiring in `backend/app/api/dependencies.py`, `backend/app/api/exception_handlers.py`, and `backend/app/main.py`
- [x] T018 [P] Define shared typed rate, snapshot, and provenance models, including `freshness_state`, `is_fallback`, and `is_stale`, plus an Angular HTTP client in `web/src/app/core/models/rate.models.ts` and `web/src/app/core/api/rates-api.service.ts`
- [x] T019 [P] Define shared rate, snapshot, and provenance models, including `freshness_state`, `is_fallback`, and `is_stale`, plus a Flutter HTTP client in `mobile/lib/core/models/rate_models.dart` and `mobile/lib/core/api/rates_api_client.dart`
- [x] T020 Create reusable fake BNM/CoinGecko-compatible providers and isolated SQL Server repository test fixtures; configure tests so no automated test contacts live providers, in `backend/tests/conftest.py` and `backend/tests/fixtures/fake_rate_providers.py`

**Checkpoint**: Shared infrastructure is ready; story phases can begin. Canonical freshness, fallback, and snapshot-usability rules are represented in shared domain types and provider-independent test fixtures.

---

## Phase 3: User Story 1 - View Current Market Data (Priority: P1)

**Goal**: Open either client without sign-in and inspect supported currencies, latest validated rates, per-entry provenance, and freshness.

**Independent Test**: With fake provider data, retrieve a complete latest snapshot and show each currency's identity, value, provider, effective time, primary freshness state, `is_fallback`, and `is_stale` in web and mobile. Confirm snapshot collection/validation time is distinct from individual rate effective times.

- [x] T021 [US1] Implement supported-currency listing and latest complete usable snapshot retrieval use cases in `backend/app/application/use_cases/list_currencies.py` and `backend/app/application/use_cases/get_latest_snapshot.py`
- [x] T022 [US1] Define currency/latest-rate response schemas and implement `GET /api/v1/currencies` and `GET /api/v1/rates/latest`; each rate entry MUST expose `provider_name`, `effective_at`, `freshness_state`, `is_fallback`, and `is_stale` in `backend/app/api/schemas/currency.py`, `backend/app/api/schemas/rates.py`, and `backend/app/api/routers/rates.py`
- [x] T023 [US1] Implement provider and backend health reporting for `GET /api/v1/health`, keeping service health distinct from rate freshness, in `backend/app/api/schemas/health.py` and `backend/app/api/routers/health.py`
- [x] T024 [US1] Add provider-independent backend unit and latest-rates API contract tests for BNM XML/CoinGecko-compatible JSON parsing, nominal normalization, empty/malformed responses, supported currencies, snapshot/effective-time distinction, and all three per-entry freshness fields in `backend/tests/unit/test_rate_provider_parsing.py` and `backend/tests/contract/test_latest_rates_api.py`
- [x] T025 [P] [US1] Build the Angular current-rates view with currency identity, value, provider, effective time, and distinct live/fallback/cached plus stale presentation in `web/src/app/features/rates/current-rates.component.ts` and `web/src/app/features/rates/current-rates.component.html`
- [x] T026 [US1] Add Angular presentation tests for current-rate values, `freshness_state`, `is_fallback`, `is_stale`, original effective dates, and snapshot collection time in `web/tests/current-rates.component.spec.ts`
- [x] T027 [P] [US1] Build the Flutter current-rates screen with currency identity, value, provider, effective time, and distinct live/fallback/cached plus stale presentation in `mobile/lib/features/rates/presentation/current_rates_screen.dart`
- [x] T028 [US1] Add Flutter widget tests for current-rate values, `freshness_state`, `is_fallback`, `is_stale`, original effective dates, and snapshot collection time in `mobile/test/features/rates/current_rates_screen_test.dart`

**Checkpoint**: User Story 1 is independently usable in both clients and exposes per-currency provenance and freshness without account creation.

---

## Phase 4: User Story 2 - Convert One Amount (Priority: P1)

**Goal**: Convert a valid amount between supported currencies and expose the exact source and target rate provenance used.

**Independent Test**: With a fake validated snapshot containing EUR from BNM and BTC from a crypto provider, convert EUR to BTC and inspect the result, snapshot reference, and both independent rate contexts, including `freshness_state`, `is_fallback`, and `is_stale`.

- [x] T029 [US2] Implement input validation and Decimal-based normalized-rate conversion, including same-currency pass-through and rejection of unavailable required entries, in `backend/app/application/use_cases/convert_currency.py`
- [x] T030 [US2] Define conversion request/result schemas and implement `POST /api/v1/convert`; both rate-context legs MUST expose `provider_name`, `effective_at`, `freshness_state`, `is_fallback`, and `is_stale` in `backend/app/api/schemas/conversion.py` and `backend/app/api/routers/conversion.py`
- [x] T031 [US2] Add fake-provider backend unit and API contract tests for fiat/fiat, fiat/crypto, crypto/fiat, crypto/crypto, reverse, same-currency, invalid input, missing-rate errors, both-leg provenance fields, and mixed-provider attribution in `backend/tests/unit/test_conversion.py` and `backend/tests/contract/test_conversion_api.py`
- [x] T032 [P] [US2] Build the Angular classic converter with validation feedback and separate source/target provider, effective-time, primary-state, fallback, and stale labels in `web/src/app/features/converter/converter.component.ts` and `web/src/app/features/converter/converter.component.html`
- [x] T033 [US2] Add Angular converter tests for invalid input, result formatting, same-currency behavior, unavailable rates, and both-leg freshness/provenance labels in `web/tests/converter.component.spec.ts`
- [x] T034 [P] [US2] Build the Flutter classic converter with validation feedback and separate source/target provider, effective-time, primary-state, fallback, and stale labels in `mobile/lib/features/converter/presentation/converter_screen.dart`
- [x] T035 [US2] Add Flutter converter widget tests for invalid input, same-currency behavior, unavailable rates, and both-leg freshness/provenance labels in `mobile/test/features/converter/converter_screen_test.dart`

**Checkpoint**: User Story 2 is independently usable in both clients and never collapses mixed-provider or mixed-freshness pair provenance.

---

## Phase 5: User Story 3 - Compare Many Currencies (Priority: P1)

**Goal**: Recalculate all visible currencies from one complete validated snapshot when the user enters an amount in any currency.

**Independent Test**: From one fake complete snapshot, enter an amount in different currency fields and verify values use that snapshot while each displayed currency retains its own provider, effective time, `freshness_state`, `is_fallback`, and `is_stale`.

- [x] T036 [P] [US3] Add a decimal-safe TypeScript calculation service for normalized rate entries and include its decimal dependency in `web/package.json` and `web/src/app/features/rates/all-currencies.service.ts`
- [x] T037 [P] [US3] Build the Angular all-currencies comparison screen using one complete snapshot and showing per-currency provider, effective time, primary freshness, fallback, and stale status in `web/src/app/features/rates/all-currencies.component.ts` and `web/src/app/features/rates/all-currencies.component.html`
- [x] T038 [US3] Add Angular tests for source-currency switching, decimal-safe recalculation, one-snapshot consistency, and independent live/fallback/cached/stale display in `web/tests/all-currencies.component.spec.ts`
- [x] T039 [P] [US3] Add a decimal package and decimal-safe normalized-rate comparison service in `mobile/pubspec.yaml` and `mobile/lib/features/rates/domain/all_currencies_calculator.dart`
- [x] T040 [P] [US3] Build the Flutter all-currencies comparison screen using one complete snapshot and showing per-currency provider, effective time, primary freshness, fallback, and stale status in `mobile/lib/features/rates/presentation/all_currencies_screen.dart`
- [x] T041 [US3] Add Flutter widget tests for source-currency switching, one-snapshot consistency, and independent live/fallback/cached/stale display in `mobile/test/features/rates/all_currencies_screen_test.dart`

**Checkpoint**: User Story 3 recalculates the visible comparison from one snapshot on both clients without misrepresenting per-entry freshness.

---

## Phase 6: User Story 4 - Review Historical Performance (Priority: P2)

**Goal**: Show 7-day and 30-day pair history and analytics derived from normalized per-currency entries, including mixed-provider and stale provenance.

**Independent Test**: Seed a fake normalized history for both legs, request both periods, and verify complete ordered points include represented dates, both rate contexts with all freshness fields and snapshot references, and accurate statistics/provenance summaries; incomplete points are excluded and empty history returns the documented empty state.

- [x] T042 [P] [US4] Add BNM historical-rate fetching and XML/date normalization for the 30-day bootstrap in `backend/app/infrastructure/providers/bnm_rate_provider.py`
- [x] T043 [P] [US4] Add crypto-provider historical-rate fetching and timestamp normalization for the 30-day bootstrap in `backend/app/infrastructure/providers/coingecko_rate_provider.py`
- [x] T044 [US4] Implement first-run historical bootstrap for up to 30 available days and persist normalized per-currency entries under snapshots in `backend/app/application/use_cases/bootstrap_history.py`
- [x] T045 [US4] Implement historical entry queries and derive complete pair points and provenance from normalized rates without pairwise storage in `backend/app/infrastructure/repositories/rate_repository.py` and `backend/app/application/services/analytics_service.py`
- [x] T046 [US4] Define history/analytics schemas and implement `GET /api/v1/history` and `GET /api/v1/analytics`; each history leg MUST expose `provider_name`, `effective_at`, `freshness_state`, `is_fallback`, and `is_stale`, while analytics reports `rate_entry_freshness_counts`, separate `stale_entry_count`, and separate `fallback_entry_count` in `backend/app/api/schemas/analytics.py` and `backend/app/api/routers/analytics.py`
- [x] T047 [US4] Add fake-provider backend unit and API contract tests for historical bootstrap, point derivation, both-leg fields, snapshot/date distinction, incomplete-point exclusion, 7-day/30-day statistics, mixed providers, primary freshness counts, overlapping stale counts, fallback counts, and empty history in `backend/tests/unit/test_analytics_service.py` and `backend/tests/contract/test_analytics_api.py`
- [x] T048 [P] [US4] Build Angular 7-day/30-day analytics views showing both per-point rate contexts and mixed-provider, primary freshness, stale, and fallback summaries in `web/src/app/features/analytics/analytics.component.ts` and `web/src/app/features/analytics/analytics.component.html`
- [ ] T049 [US4] Add Angular analytics tests for metrics, empty state, period selection, per-point live/fallback/cached/stale status, and aggregate stale/fallback counts in `web/tests/analytics.component.spec.ts`
- [ ] T050 [P] [US4] Build Flutter 7-day/30-day analytics views showing both per-point rate contexts and mixed-provider, primary freshness, stale, and fallback summaries in `mobile/lib/features/analytics/presentation/analytics_screen.dart`
- [ ] T051 [US4] Add Flutter analytics widget tests for metrics, empty state, period selection, per-point live/fallback/cached/stale status, and aggregate stale/fallback counts in `mobile/test/features/analytics/analytics_screen_test.dart`

**Checkpoint**: User Story 4 works from bootstrapped or continuing history and preserves both rate legs' provenance on every complete point.

---

## Phase 7: User Story 5 - Use CurrencyHub Offline or During Source Failures (Priority: P2)

**Goal**: Retain access to the last successful complete data and accurately distinguish current, fallback, cached, and stale rates through refreshes and restarts.

**Independent Test**: With fake provider/network failures, validate the BNM publication-day rules and crypto 15-minute boundary, retain a readable complete snapshot across restart with no age-based deletion, atomically replace it after a successful refresh, preserve it after failed/incomplete refreshes, and show unavailable when no usable complete snapshot exists.

- [ ] T052 [US5] Implement refresh orchestration that classifies BNM expected weekend/official non-publishing-day reuse as `freshness_state=fallback`, `is_fallback=true`, and not stale solely due to date age; classify older retained BNM data as cached/stale when a newer official rate should exist; apply the crypto 15-minute current/stale boundary; and assemble complete candidates in `backend/app/application/use_cases/refresh_rates.py`
- [ ] T053 [US5] Implement `POST /api/v1/rates/refresh` response schemas and route with atomic replacement, preservation of the previous complete usable snapshot on failed/incomplete refresh, and separate primary freshness, stale, and fallback counts in `backend/app/api/schemas/refresh.py` and `backend/app/api/routers/rates.py`
- [ ] T054 [US5] Add provider-independent backend unit/integration tests for BNM weekend and official non-publishing-day fallback (`fallback=true`, `stale=false` where appropriate), missing expected newer BNM data (`cached/stale`), crypto remaining current at exactly 15 minutes and becoming stale only after more than 15 minutes without successful refresh, cached reuse not implying fallback, all snapshot usability checks, preserved original timestamps, atomic successful replacement, failed/incomplete refresh preservation, and unavailable state without a usable snapshot in `backend/tests/unit/test_rate_freshness_policy.py` and `backend/tests/integration/test_rate_refresh_resilience.py`
- [ ] T055 [P] [US5] Implement persistent Angular snapshot storage that retains the last successful complete snapshot until replaced or explicitly cleared, has no automatic age-based deletion in v1, validates readability and required positive rates/provenance/effective timestamps, and rehydrates without relabelling cached data current in `web/src/app/core/storage/rate-snapshot-store.service.ts`
- [ ] T056 [US5] Add Angular tests for cache readability/structural validation, restart persistence without age deletion, cached-not-fallback behavior, freshness recalculation without timestamp reset, successful atomic replacement, failed/incomplete refresh preservation, and unavailable state when no usable cache exists in `web/tests/rate-snapshot-store.service.spec.ts`
- [ ] T057 [P] [US5] Implement persistent Flutter snapshot storage with the same retain-until-replaced-or-cleared policy, no automatic age-based deletion in v1, complete-snapshot usability validation, and restart rehydration that never relabels cached data current in `mobile/lib/core/cache/rate_snapshot_store.dart`
- [ ] T058 [US5] Add Flutter tests for cache readability/structural validation, restart persistence without age deletion, cached-not-fallback behavior, freshness recalculation without timestamp reset, successful atomic replacement, failed/incomplete refresh preservation, and unavailable state when no usable cache exists in `mobile/test/core/cache/rate_snapshot_store_test.dart`
- [ ] T059 [US5] Add explicit user-facing offline/unavailable handling in both clients: show the original effective time and provider for usable cached entries, identify unavailable required currencies, and never display a complete conversion or pair from missing entries in `web/src/app/core/storage/rate-snapshot-store.service.ts` and `mobile/lib/core/cache/rate_snapshot_store.dart`
- [ ] T060 [US5] Add cross-client state/presentation tests confirming web and mobile use identical meanings for live, fallback, cached, stale, and fallback-used metadata after outages and restarts in `web/tests/rate-snapshot-store.service.spec.ts` and `mobile/test/core/cache/rate_snapshot_store_test.dart`

**Checkpoint**: User Story 5 preserves and reports complete-snapshot state correctly through outages, stale rates, refresh failures, and application restarts.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Complete setup documentation, configuration checks, and traceable end-to-end validation.

- [ ] T061 Document backend, Angular, and Android Emulator prerequisites/startup, host URLs, migrations, and runnable scenarios; explicitly map the access and shared-client steps to FR-001, FR-022, FR-023 and SC-001, SC-012 in `specs/001-currencyhub-platform/quickstart.md`
- [ ] T062 Review environment configuration, CORS restrictions, and secret exclusions against the constitution and FR-026 scope/security boundaries; verify sample values are placeholders and frontend files contain no database credentials or provider secrets in `backend/.env.example`, `backend/app/core/config/settings.py`, and `.gitignore`
- [ ] T063 Execute the quickstart conversion, validation, comparison, analytics, offline, and restart scenarios against fake/mock providers; for SC-001, time the standard conversion flow on Angular web and Flutter mobile from when the converter screen is fully ready for user input until both the conversion result and its rate context are visible, record each measurement and pass/fail against the under-30-second threshold, and record results in `specs/001-currencyhub-platform/quickstart.md`; record pass/fail outcomes for FR-003-FR-025 and SC-002-SC-018 and confirm no automated scenario contacts live BNM or crypto providers
- [ ] T064 Verify every published rate-entry contract includes `freshness_state`, `is_fallback`, and `is_stale`; verify analytics and refresh summaries separate primary freshness counts, `stale_entry_count`, and `fallback_entry_count`; record contract-check outcomes against FR-003, FR-013, FR-014, FR-019-FR-025 and SC-005-SC-009, SC-012-SC-018 in `specs/001-currencyhub-platform/contracts/rates-api.md` and `specs/001-currencyhub-platform/quickstart.md`
- [ ] T065 Prepare five representative conversion/analytics scenarios and have one person unfamiliar with currency data review them without technical explanation before answering; for each scenario, require the participant to identify the provider and freshness meaning/status of the first rate leg and the provider and freshness meaning/status of the second rate leg. Count a scenario as correctly interpreted only when all four identifications are correct; SC-010 passes only when at least 4 of 5 scenarios are correctly interpreted. Record each individual scenario result and the final pass/fail in `specs/001-currencyhub-platform/quickstart.md`; automated tests do not substitute for this usability review. Record final acceptance results and any remaining gaps with explicit FR/SC references and confirm all five user-story independent tests pass in `specs/001-currencyhub-platform/quickstart.md`
- [ ] T066 Complete and record the documented review in `specs/001-currencyhub-platform/quickstart.md` or another existing project review section. If this is a solo project, perform and record the documented self-review; if more than one project contributor exists, the review MUST be performed by another contributor, and self-review MUST NOT substitute for that review. Cover specification/implementation consistency, acceptance criteria, automated test results, correctness, safety, maintainability, scope compliance, and unresolved `/speckit-analyze` findings. Resolve all CRITICAL findings before merge or handoff

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies; backend, web, and mobile scaffolds can start in parallel.
- **Foundational (Phase 2)**: Depends on setup completion and blocks every user story. Domain contracts precede ORM/repository and provider implementations; shared client models follow the API data definitions.
- **User Stories (Phases 3-7)**: Depend on the foundational phase. US1, US2, and US4 can begin independently after foundations; US3 depends on the latest-snapshot contract; US5 depends on snapshot retrieval and refresh foundations.
- **Polish (Phase 8)**: Depends on the selected stories and their acceptance tests.

### User Story Dependencies

- **US1 (P1)**: Starts after Phase 2. Provides current rates and latest-snapshot retrieval; suggested MVP.
- **US2 (P1)**: Starts after Phase 2 and uses shared snapshot/repository foundations; its UI does not depend on US1 completion.
- **US3 (P1)**: Starts after Phase 2 and needs the complete latest-snapshot contract from US1.
- **US4 (P2)**: Starts after Phase 2; historical provider adapters, bootstrap, and analytics can proceed independently of converter screens.
- **US5 (P2)**: Starts after Phase 2 and depends on latest-snapshot retrieval from US1 plus refresh orchestration.

### Parallel Opportunities

- Setup: T001, T002, and T003 are independent scaffolds.
- Foundation: T006 and T009 can proceed independently; T014 and T015 can proceed in parallel after T010; T018 and T019 can proceed in parallel after shared field names are agreed.
- US1: T025 and T027 can proceed in parallel after T022; their tests can proceed after their corresponding UI contracts are stable.
- US2: T032 and T034 can proceed in parallel after T030.
- US3: T036 and T039 can proceed in parallel; then T037 and T040 can proceed in parallel.
- US4: T042 and T043 can proceed in parallel; T048 and T050 can proceed in parallel after T046.
- US5: T055 and T057 can proceed in parallel after freshness semantics in T052/T053 are finalized; T056 and T058 can proceed in parallel with their respective storage implementations.
- Polish: T061 and T062 can proceed in parallel; T063-T065 follow implemented stories and available outcomes; T066 is the final review gate after acceptance verification.

### Parallel Execution Examples

```text
After Phase 1: T001 + T002 + T003
After T010: T014 + T015
After shared API fields: T018 + T019
After latest-rate contract: T025 + T027
After conversion contract: T032 + T034
After Phase 2: T036 + T039; T042 + T043
After analytics contract: T048 + T050
After refresh policy: T055 + T057
After implementation: T061 + T062, then T063 + T064, then T065, then T066
```

## Implementation Strategy

### MVP First

1. Complete Phase 1 setup and Phase 2 foundations.
2. Complete Phase 3, User Story 1, as the first usable product increment for current rates and explicit per-entry freshness.
3. Validate US1 independently using fake providers and verify all three freshness/provenance API fields before expanding scope.
4. Add US2 and US3 for conversion workflows, then US4 and US5 for analytics and resilience.

### Incremental Delivery

Deliver and validate each story independently after the foundations. US1 and US2 are the first P1 increments; US3 follows the shared snapshot API; US4 and US5 add historical analytics and offline resilience. Finish with documented, FR/SC-traceable quickstart/configuration/contract verification. Preserve provider-independent automated tests and the canonical per-entry freshness semantics across every increment.
