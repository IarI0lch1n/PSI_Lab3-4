# Research Notes

## Decision: Model a snapshot as a consistency boundary with per-currency rate entries

**Decision**: The backend will expose and persist a RateSnapshot object that contains many individual RateEntry objects. Each entry independently captures currency, normalized rate-to-MDL, nominal-unit information, provider/source, effective timestamp, and freshness state.

**Rationale**: Fiat and crypto values come from different providers, may have different effective timestamps, and may need independent fallback labeling. Treating the entire snapshot as a single global source value would conflate different data origins and violate the product requirement that each entry must maintain its own provenance.

**Alternatives considered**: A single global source_name/source_type for the full snapshot, or a rate map without per-entry metadata. Both would hide source provenance and make multi-provider snapshots ambiguous.

## Decision: Store normalized per-currency rate records and derive pair values when needed

**Decision**: The database will store normalized rate entries for each currency at each timestamp rather than storing an N×N historical pair table. Pairwise values are derived at query time from the normalized rate-to-MDL values using the standard formula $amount \times source\_rate\_to\_mdl / target\_rate\_to\_mdl$.

**Rationale**: This preserves one source of truth while avoiding redundant pairwise storage. It also aligns directly with the financial calculation rules and keeps historical analytics consistent with the stored normalized data.

**Alternatives considered**: Persisting a duplicate table for every possible currency pair. That design creates data duplication, more write complexity, and a greater risk of inconsistent historical values.

## Decision: Include an initial 30-day historical bootstrap step

**Decision**: On first install or first required synchronization, the backend will backfill up to the prior 30 days of fiat and crypto history, normalize the values, and persist them into SQL Server before the analytics screens are expected to be useful.

**Rationale**: The product requires the 30-day analytics screen to be useful soon after installation; waiting for a month of runtime accumulation would fail the UX requirement. Backfilling at startup ensures the analytics pipeline has data immediately available.

**Alternatives considered**: Waiting for normal runtime accumulation or requiring a 30-day warm-up period. These alternatives do not satisfy the product requirement and would make onboarding experience worse.

## Decision: Use domain-driven separation between provider adapters and application use cases

**Decision**: External exchange-rate providers are wrapped behind interfaces and adapter implementations. The application layer orchestrates conversion, snapshot assembly, fallback rules, and analytics without depending on provider SDKs or infrastructure details.

**Rationale**: The constitution requires Clean Architecture, dependency inversion, and provider abstraction for testability and maintainability. This supports mocking and keeps business rules independent from external HTTP and XML/JSON parsing specifics.

**Alternatives considered**: Direct API calls from services and use cases. That approach would couple business logic to external providers and make it harder to test and maintain.

## Decision: Treat fallback and cached data as explicit states on each rate entry

**Decision**: Every rate entry tracks a freshness_state and an is_fallback flag, while the UI describes the cached state separately when backend data is unavailable locally.

**Rationale**: The product requires users to know when data is live, cached, or fallback-derived, and those states can differ by currency within a single snapshot. Per-entry metadata is the clearest and most accurate approach.

**Alternatives considered**: A single snapshot-level fallback flag or global stale status. This would hide important source and provenance differences across currencies and would make partial fallback scenarios confusing.

## Decision: Normalize all monetary conversion through decimal arithmetic and a common internal representation

**Decision**: The system stores rates as normalized values expressed relative to MDL and performs all conversions with Decimal arithmetic. Nominal-unit metadata is preserved so quoted values based on 10, 100, or 1000 units are converted correctly.

**Rationale**: Financial correctness is a non-negotiable project constraint, and the project explicitly forbids binary floating-point logic for money calculations. The normalized-to-MDL model provides a consistent and correct arithmetic basis for all currency pairs.

**Alternatives considered**: Pairwise stored conversion rates and binary floating-point math. These are error-prone and do not satisfy the constitution or the required conversion semantics.

## Decision: Keep the shared API contract stable across web and mobile clients

**Decision**: The backend API exposes canonical rate and analytics responses with consistent endpoint names and response schema semantics for both the web and mobile clients.

**Rationale**: Shared behavior across platforms is required, and the clients must not diverge in routing, freshness semantics, or empty-state handling. A common contract reduces bugs and keeps the client implementations aligned.

**Alternatives considered**: Client-specific endpoints or custom response shapes. Those would increase maintenance overhead and create inconsistent UX across web and mobile experiences.

## Decision: Provide explicit empty states for missing analytics and unavailable data

**Decision**: The API and UI will return or display empty-state responses when a selected pair has no available history or when no current data is available locally.

**Rationale**: Empty states are required for understanding missing or incomplete data and avoid misleading results or exceptions during outages or sparse histories.

**Alternatives considered**: Failing screens or blank placeholders without explanation. These would frustrate users and reduce trust in the product during incomplete data conditions.
