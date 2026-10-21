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
- It is complete only when all required supported currency entries are present and valid.
- It is usable only when it can be read and each required entry has a positive valid rate, provider provenance, and effective timestamp.
- A refresh must not partially replace the active snapshot; a fully validated candidate replaces the active snapshot atomically.

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
| freshness_state | enum | Primary status: live, fallback, or cached |
| is_stale | boolean | Source-aware stale condition; derived independently at use/display time, not persisted, and may overlap cached status |
| is_fallback | boolean | Whether an explicitly permitted source fallback supplied this entry |

**Validation rules**:
- The normalized rate must be greater than zero.
- A given snapshot may contain values from multiple providers and different effective times.
- Each entry must keep source and freshness metadata independently.
- `is_stale` is not a provider or a replacement for `freshness_state`; it reflects the canonical source-specific freshness policy.
- A prior entry retained because current provider data is unavailable is cached reuse and does not by itself set `is_fallback`.
- A BNM weekend or official non-publishing-day entry uses the latest prior official rate, is labelled fallback, retains its true effective date, and is not stale solely due to age.
- If a newer official BNM rate should already be available but cannot be retrieved, an older retained entry is cached/stale, not current.
- A cryptocurrency entry is live/current for 15 minutes after successful snapshot acquisition and validation; after that it is stale until a newer successful value replaces it.
- Reusing an entry preserves its original `effective_at`, provider provenance, and correct freshness and fallback-used metadata.
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
| provenance_summary | object | Provider sets, primary freshness/fallback counts, and source-aware stale information across the selected period |

Each historical point contains a date, derived pair value, and `rate_context` with source_rate, target_rate, and snapshot_id. Each rate context entry retains currency, provider_name, effective_at, freshness_state, and is_fallback.

**Validation rules**:
- Trend is derived from the first and last available values.
- Provenance summaries must not collapse mixed providers or freshness states into a single state.
- Live/fallback/cached counts classify each rate entry by its one primary `freshness_state`; stale information is reported separately under the canonical policy, and fallback count follows `is_fallback`.
- Empty windows must yield an empty-state response instead of an exception.

## Relationships

- A Currency is represented by many RateEntry records over time.
- A RateSnapshot contains many RateEntry values for the same validation boundary.
- A ConversionRequest leads to exactly one ConversionResult.
- Historical analytics are derived from stored normalized RateEntry records rather than from duplicated pairwise history tables.
- Cached and fallback values are tracked per entry and remain distinguishable from live values.

## State and lifecycle notes

- `freshness_state` is one primary status: live, fallback, or cached. Stale is a separate source-aware condition and may overlap cached status.
- A fiat rate is current only when it represents the latest official BNM rate expected for the current Moldova calendar date. On weekends and official non-publishing days, the latest prior published BNM rate is a permitted fallback; its true effective date is retained and its older date alone does not make it stale.
- If an expected newer official BNM rate cannot be retrieved, an older retained value is cached/stale rather than current.
- Cryptocurrency rates are live/current for 15 minutes after successful acquisition and validation, and stale after that threshold without successful refresh.
- Fallback-used is set only when a permitted source fallback supplies the entry. Prior successful entries reused because of provider failure or offline access are cached, not automatically fallback.
- Web and mobile retain the last successful complete snapshot until replaced by a newer successful complete snapshot or application data is explicitly cleared. Version 1 has no automatic age-based deletion; restarting never makes cached data current.
- A candidate snapshot is usable only when readable, complete for required currencies, and all required rates are positive and valid with provider provenance and effective timestamps present.
- Missing provider data may be filled only from an explicitly permitted fallback or a previously successful usable entry. Reused entries keep their original effective timestamp and correct freshness/fallback metadata.
- A refreshed snapshot replaces the active snapshot only after the full candidate passes validation, and replacement is atomic. Failed/incomplete refresh preserves the previous complete usable snapshot. If no usable complete snapshot exists, rates are unavailable.
- Snapshot collection/validation time, each rate's effective timestamp, and a historical point's represented date remain distinct.

## Historical bootstrap and derivation rule

The historical backfill process populates the database with up to the previous 30 days of available fiat and crypto values before analytics is expected to be useful. Those historical values are stored as normalized rate entries and are not duplicated as pairwise records. When a client requests a pair or analytics window, the system derives the pair values from the two currencies' normalized rate-to-MDL values using the conversion formula.
