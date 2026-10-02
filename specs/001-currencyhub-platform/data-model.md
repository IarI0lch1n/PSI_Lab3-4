# Data Model

## Overview

This feature centers on a small but critical set of exchange-rate and analytics entities. The data model is designed to preserve temporal accuracy, support offline usage, and separate business rules from external provider behavior.

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
| source_name | string | Provider or internal source label |
| source_type | enum | live, fallback, cached |
| rate_date | date | Effective date associated with the rates |
| is_stale | boolean | Indicates whether the snapshot is stale compared to current freshness rules |
| rates | collection | Map of currency code to exchange rate value |

**Validation rules**:
- Rates must be normalized to a single internal representation.
- Snapshot must be valid before it replaces the previous visible state.
- A refresh must not overwrite a usable snapshot unless validation succeeds.

### HistoricalRateRecord

| Field | Type | Description |
|-------|------|-------------|
| history_id | UUID | Unique record identifier |
| base_currency | string | Source currency code |
| quote_currency | string | Target currency code |
| rate_value | decimal | Conversion rate at that timestamp |
| rate_date | datetime | Recorded timestamp |
| source_name | string | The origin of the rate |
| source_type | enum | live, fallback, cached |

**Validation rules**:
- Rate value must be greater than zero.
- Historical records are required for 7-day and 30-day analytics.
- Duplicate timestamps for the same currency pair should be handled consistently.

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
- Same-currency conversion is handled as a valid direct pass-through case.

### ConversionResult

| Field | Type | Description |
|-------|------|-------------|
| result_id | UUID | Unique result identifier |
| source_amount | decimal | Original amount used |
| converted_amount | decimal | Converted value |
| source_currency | string | Source currency code |
| target_currency | string | Target currency code |
| rate_value | decimal | Rate used for the conversion |
| rate_date | datetime | Date and time of the applied rate |
| source_name | string | Data source label |
| freshness_state | enum | live, fallback, cached |

**Validation rules**:
- Result must reflect the exact snapshot used for calculation.
- Same-currency conversion returns the original amount unchanged.

### AnalyticsSummary

| Field | Type | Description |
|-------|------|-------------|
| currency_pair | string | Base and quote pair key |
| period | enum | 7d, 30d |
| time_series | list | Ordered time-based rate values |
| minimum | decimal | Lowest value in the window |
| maximum | decimal | Highest value in the window |
| average | decimal | Mean value for the window |
| absolute_change | decimal | End minus start |
| percentage_change | decimal | Relative change from start to end |
| trend | enum | growth, decline, unchanged |
| source_state | enum | live, fallback, cached |

**Validation rules**:
- Trend must be explicitly derived from the comparison of beginning and ending values.
- Empty windows must yield an empty-state response rather than a crash.

## Relationships

- A Currency participates in many RateSnapshot entries.
- A RateSnapshot contains many historical rate values for supported currencies.
- A ConversionRequest leads to exactly one ConversionResult for the request.
- HistoricalRateRecord data feeds the AnalyticsSummary for both 7-day and 30-day views.
- Cached or fallback snapshots are subsets of the same currency dataset and are labeled distinctly.

## State and lifecycle notes

- Live rates are preferred when available.
- Fallback data is used when the normal source has no published value for a weekend or holiday.
- Cached data is used when the user is offline or the provider is unavailable.
- A refreshed snapshot replaces active state only after it passes validation.
