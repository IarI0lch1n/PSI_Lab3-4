# Research Notes

## Decision: Use a single normalized rate snapshot as the source of truth

**Decision**: The backend will produce a normalized rate snapshot for all supported currencies, with metadata for source, timestamp, and fallback/cached state. Both clients will consume that snapshot and only display values from a single validated snapshot at a time.

**Rationale**: The product requirement explicitly states that values shown together must use one consistent exchange-rate snapshot and must not mix timestamps. This also supports offline fallback and clarity around stale data.

**Alternatives considered**: Direct per-currency updates, per-screen independent refreshes, and ad hoc caching without snapshot metadata. These alternatives increase inconsistency risk and make stale/fallback states harder to explain to users.

## Decision: Store rates in a historical table with summary-driven analytics

**Decision**: Historical analytics will be computed from persisted rate records over time, rather than from volatile in-memory state. Summary metrics will be generated from stored time-series values for sliding 7-day and 30-day windows.

**Rationale**: The product requires time-series, minimum, maximum, average, absolute change, percentage change, and trend labels. Persisted data also allows continuity when the source is temporarily unavailable.

**Alternatives considered**: Generating analytics only from live provider responses or from client-side arrays. Those approaches fail when the source is unavailable and weaken auditability.

## Decision: Use domain-driven separation between provider adapters and application use cases

**Decision**: External exchange-rate providers will be wrapped behind provider interfaces and adapter implementations. The application layer will orchestrate conversion and analytics use cases without depending on provider SDKs or infrastructure frameworks.

**Rationale**: The constitution requires Clean Architecture, dependency inversion, and abstraction for providers. This supports testability and protects business rules from provider failure modes.

**Alternatives considered**: Direct calls to provider clients inside converters and analytics logic, and coupling business logic to provider models. These would violate the constitution and would make mock replacement difficult.

## Decision: Treat fallback and cached data as explicit states, not as standard live data

**Decision**: Every rate record and displayed view will carry a status that distinguishes live, cached, and fallback data. The UI will render a clear freshness indicator and source label.

**Rationale**: The product requires that users can always identify whether displayed financial data is current or stale, and that fallback data is clearly labeled.

**Alternatives considered**: Silent fallback without status labeling, or reusing the same "current" label for all data. This would obscure data freshness and weaken trust.

## Decision: Normalize all monetary conversion through decimal arithmetic and a consistent internal representation

**Decision**: The system will hold rates and converted amounts in a decimal-safe representation and treat all conversions through a common internal rate model. Same-currency conversions will short-circuit before any arithmetic is applied.

**Rationale**: Financial correctness is a primary requirement and is explicitly non-negotiable in the constitution and specification. This also reduces risk of rounding drift and invalid calculations.

**Alternatives considered**: Binary floating-point arithmetic and ad hoc rounding logic. These are prohibited by the project constraints and increase financial correctness risk.

## Decision: Separate the shared API contract from platform-specific UI state

**Decision**: The backend API will expose canonical rate and analytics data contracts to both clients. The web and mobile applications will keep their own UI state and local cache behavior but consume the same API contracts.

**Rationale**: The product requires shared capabilities across web and mobile without requiring direct DB or provider access in either frontend.

**Alternatives considered**: Building client-specific API contracts or letting each client call data sources directly. These would break the shared product contract and violate the constitution.

## Decision: Provide empty states for missing analytics and unavailable data

**Decision**: When no historical records exist or no network or cached data is available, the UI will show a clear, explanatory empty or unavailable state instead of failing the screen or showing misleading numbers.

**Rationale**: The product explicitly requires meaningful user-facing handling for empty or unavailable data, and this reduces confusion during outages or rare data gaps.

**Alternatives considered**: Silent failures, blank screens, or stale values without explanation. These would be confusing and risky for users relying on financial data.
