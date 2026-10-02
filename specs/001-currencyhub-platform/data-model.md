# Data Model

## Overview

This feature centers on a small but critical set of exchange-rate and analytics entities. The data model preserves per-currency provenance, supports offline usage, and separates business logic from external provider behavior.

## Core Entities

### Currency

| Field | Type | Description |
|-------|------|-------------|
| code | string | ISO-like currency code such as USD, MDL, BTC, ETH |
| name | string | Friendly display name |
| type | enum | fiat or crypto |
| is_supported | boolean | Indicates eligibility for conversion and analytics |

**Validation rules**:
- Code must be unique.
- Type must be explicitly set as fiat or crypto.
- Supported currencies are constrained to the required product set.

### RateSnapshot

| Field | Type | Description |
|-------|------|-------------|
| snapshot_id | UUID | Unique identifier for the snapshot |
| captured_at | datetime | Time when the snapshot was validated and recorded |
| rates | collection | Collection of per-currency rate entries for the snapshot |

**Validation rules**:
- The snapshot acts as a consistency boundary for one validated set of rates.
- It must not be treated as a single global source or global effective date.
- A refresh must not partially replace the active snapshot.

### RateEntry

| Field | Type | Description |
|-------|------|-------------|
| entry_id | UUID | Unique identifier for the rate entry |
| snapshot_id | UUID | Parent snapshot identifier |
| currency | string | Currency code for the entry |
| normalized_rate_to_mdl | decimal | Rate normalized to 1 unit = X MDL |
| nominal_unit | integer or null | Nominal unit used by the source, if applicable |
| provider_name | string | Provider or source label |
| provider_type | enum | fiat or crypto |
| effective_at | datetime | Effective timestamp of the rate entry |
| freshness_state | enum | live, fallback, cached |
| is_fallback | boolean | Whether the rate was reused because of missing or invalid source data |

**Validation rules**:
- The normalized rate must be greater than zero.
- A given snapshot may contain values from multiple providers and different effective times.
- Each entry must keep source and freshness metadata independently.
- Same-currency and invalid amounts are handled in conversion logic, not in the stored rate metadata.

### ConversionRequest

| Field | Type | Description |
|-------|------|-------------|
| amount | decimal | User-entered amount |
| source_currency | string | Source currency code |
| target_currency | string | Target currency code |
| request_time | datetime | Time of conversion request |
| validation_state | enum | valid, invalid, missing |

**Validation rules**:
- Amount must be present, numeric, greater than zero, and finite.
- Source and target currency must be supported.
- Same-currency conversion is handled as a valid pass-through case.

### ConversionResult

| Field | Type | Description |
|-------|------|-------------|
| result_id | UUID | Unique result identifier |
| source_amount | decimal | Original amount used |
| converted_amount | decimal | Converted value |
| source_currency | string | Source currency code |
| target_currency | string | Target currency code |
| rate_value | decimal | Evaluated conversion rate |
| rate_context | object | Both rate entries used and the snapshot identifier |

`rate_context` contains `source_rate` and `target_rate`, each with currency, provider_name, effective_at, freshness_state, and is_fallback, plus `snapshot_id` for the validated snapshot.

**Validation rules**:
- Result must use a single validated snapshot.
- Pair-level provenance must retain the independent source and target rate metadata; do not represent a mixed-provider conversion with one provider, timestamp, or freshness value.
- Same-currency conversion returns the original amount unchanged.

### AnalyticsSummary

| Field | Type | Description |
|-------|------|-------------|
| base_currency | string | Base currency for the pair |
| quote_currency | string | Quote currency for the pair |
| period | enum | 7d, 30d |
| points | list | Ordered time-based values |
| minimum | decimal | Lowest value in the window |
| maximum | decimal | Highest value in the window |
| average | decimal | Mean value in the window |
| absolute_change | decimal | End minus start |
| percentage_change | decimal | Relative change from the first point |
| trend | enum | GROWTH, DECLINE, UNCHANGED |
| provenance_summary | object | Provider sets and freshness/fallback counts across the selected period |

Each historical point contains a date, derived pair value, and `rate_context` with source_rate, target_rate, and snapshot_id. Each rate context entry retains currency, provider_name, effective_at, freshness_state, and is_fallback.

**Validation rules**:
- Trend is derived from the first and last available values.
- Provenance summaries must not collapse mixed providers or freshness states into a single state.
- Empty windows must yield an empty-state response instead of an exception.

## Relationships

- A Currency is represented by many RateEntry records over time.
- A RateSnapshot contains many RateEntry values for the same validation boundary.
- A ConversionRequest leads to exactly one ConversionResult.
- Historical analytics are derived from stored normalized RateEntry records rather than from duplicated pairwise history tables.
- Cached and fallback values are tracked per entry and remain distinguishable from live values.

## State and lifecycle notes

- Live entries are preferred when available.
- Fallback entries are used when the source is missing for a weekend or holiday or when the source response is incomplete.
- Cached entries are used when offline or when the backend cannot refresh successfully.
- A refreshed snapshot replaces the active state only after the full snapshot passes validation.

## Historical bootstrap and derivation rule

The historical backfill process populates the database with up to the previous 30 days of available fiat and crypto values before analytics is expected to be useful. Those historical values are stored as normalized rate entries and are not duplicated as pairwise records. When a client requests a pair or analytics window, the system derives the pair values from the two currencies' normalized rate-to-MDL values using the conversion formula.
