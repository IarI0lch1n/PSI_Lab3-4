# Shared API Contracts

## Overview

This contract defines the shared API responsibilities for the CurrencyHub backend. The web and mobile clients consume the same contract so they expose the same core features and behavior.

## Endpoints

### GET /api/v1/rates

**Purpose**: Retrieve the current snapshot of supported rates.

**Response**:

```json
{
  "snapshot_id": "uuid",
  "captured_at": "2026-10-02T12:00:00Z",
  "rate_date": "2026-10-02",
  "source_name": "BNM",
  "source_type": "live",
  "rates": {
    "MDL": 1.0,
    "USD": 17.4,
    "EUR": 18.8,
    "BTC": 0.00012
  },
  "is_stale": false
}
```

**Business rules**:
- Response must include a timestamp and source.
- Cached or fallback data must carry a distinct source_type or freshness marker.
- Users must be able to tell whether the values are current, cached, or fallback-derived.

### POST /api/v1/convert

**Purpose**: Convert an amount between supported currencies.

**Request**:

```json
{
  "amount": "100.00",
  "source_currency": "USD",
  "target_currency": "EUR"
}
```

**Response**:

```json
{
  "source_amount": "100.00",
  "converted_amount": "92.35",
  "source_currency": "USD",
  "target_currency": "EUR",
  "rate_value": "0.9235",
  "rate_date": "2026-10-02T12:00:00Z",
  "source_name": "BNM",
  "freshness_state": "live"
}
```

**Business rules**:
- Invalid input must be rejected before conversion.
- Same-currency conversion must return the original amount.
- Conversion must use a single validated snapshot.

### GET /api/v1/analytics?pair=USD-EUR&range=7d

**Purpose**: Return analytics summary for a selected currency pair over the chosen period.

**Response**:

```json
{
  "pair": "USD-EUR",
  "period": "7d",
  "time_series": [
    { "date": "2026-09-26", "value": "17.25" },
    { "date": "2026-09-27", "value": "17.32" }
  ],
  "minimum": "17.20",
  "maximum": "17.45",
  "average": "17.31",
  "absolute_change": "0.18",
  "percentage_change": "1.04",
  "trend": "growth",
  "source_state": "live"
}
```

**Business rules**:
- Summary values must include minimum, maximum, average, absolute change, percentage change, and trend.
- Empty datasets must return a clear empty-state response rather than failure.
- Trend must be explicit: growth, decline, or unchanged.

### GET /api/v1/health

**Purpose**: Check whether the backend and upstream dependencies are in a healthy state.

**Business rules**:
- Health checks must distinguish between service health and rate-freshness status.
- A provider outage must not crash the application or hide cached data from the user.
