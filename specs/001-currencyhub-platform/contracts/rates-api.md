# Shared API Contracts

## Overview

This contract defines the shared API responsibility for the CurrencyHub backend. The Angular web client and Flutter mobile client both consume the same contract so that rate displays, conversion logic, and analytics semantics stay aligned.

## Endpoints

### GET /api/v1/currencies

**Purpose**: Return the supported currencies and their metadata.

**Request**: none

**Response**:

```json
{
  "currencies": [
    {
      "code": "USD",
      "name": "US Dollar",
      "type": "fiat",
      "is_supported": true
    },
    {
      "code": "BTC",
      "name": "Bitcoin",
      "type": "crypto",
      "is_supported": true
    }
  ]
}
```

**Business rules**:
- The response must contain the supported currency list and metadata.
- Type values must distinguish fiat from crypto.

### GET /api/v1/rates/latest

**Purpose**: Retrieve the latest validated rate snapshot and all contained rate entries.

**Request**: none

**Response**:

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
      "effective_at": "2026-10-02T09:30:00Z",
      "freshness_state": "live",
      "is_fallback": false
    }
  ]
}
```

**Business rules**:
- There is no single global source_name or source_type for the snapshot.
- Each rate entry maintains its own provider, effective timestamp, freshness state, and fallback indicator.
- The snapshot acts as the consistency boundary for all returned values.

### POST /api/v1/convert

**Purpose**: Convert an amount from a source currency to a target currency using a single validated rate snapshot.

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
  "rate_date": "2026-10-02T09:00:00Z",
  "source_name": "BNM",
  "freshness_state": "live"
}
```

**Business rules**:
- Invalid input must be rejected before conversion.
- Same-currency conversion must return the original amount.
- The conversion must use one consistent snapshot and the exact rate entries used for the request.

### GET /api/v1/history

**Purpose**: Return historical values for a selected pair over a requested period.

**Request**:

Query parameters:
- `base_currency` required
- `quote_currency` required
- `period` required; allowed values: `7d`, `30d`

**Response**:

```json
{
  "base_currency": "USD",
  "quote_currency": "EUR",
  "period": "7d",
  "points": [
    { "date": "2026-09-26", "value": "17.25", "source": "BNM", "freshness_state": "live", "is_fallback": false },
    { "date": "2026-09-27", "value": "17.32", "source": "BNM", "freshness_state": "fallback", "is_fallback": true }
  ],
  "empty": false
}
```

**Empty state**:

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

**Business rules**:
- Historical values are derived from normalized rate entries, not from duplicated pairwise storage.
- The response must include source and freshness metadata when points exist.
- Empty historical datasets must return an explicit empty state.

### GET /api/v1/analytics

**Purpose**: Return summary statistics for a selected pair and period.

**Request**:

Query parameters:
- `base_currency` required
- `quote_currency` required
- `period` required; allowed values: `7d`, `30d`

**Response**:

```json
{
  "base_currency": "USD",
  "quote_currency": "EUR",
  "period": "7d",
  "points": [
    { "date": "2026-09-26", "value": "17.25" },
    { "date": "2026-09-27", "value": "17.32" }
  ],
  "minimum": "17.20",
  "maximum": "17.45",
  "average": "17.31",
  "absolute_change": "0.18",
  "percentage_change": "1.04",
  "trend": "GROWTH",
  "source_state": "live",
  "empty": false
}
```

**Business rules**:
- Trend is derived from the first and last available values.
- Summary values must include minimum, maximum, average, absolute change, percentage change, and trend.
- Empty historical datasets must return a clear empty-state response instead of failing.

### POST /api/v1/rates/refresh

**Purpose**: Trigger a synchronization cycle and update the latest snapshot if the provider data is valid.

**Request**: optional scope or provider filter; defaults to full refresh.

**Response**:

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

**Business rules**:
- A refresh must not partially replace the active snapshot.
- The response must explicitly summarize how many entries were live, fallback, or cached.

### GET /api/v1/health

**Purpose**: Check the service and upstream provider health.

**Request**: none

**Response**:

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

**Business rules**:
- Health checks must distinguish between service health and rate freshness status.
- Provider outages must not crash the application or hide the last successful cached data.

## Shared notes

- All UI screens must show source and freshness metadata from the API or from the local cached snapshot, never from hidden internal state.
- The latest-rate response supports different providers and effective dates within the same snapshot because each rate entry carries independent metadata.
- Empty-state responses are explicit for both history and analytics when the requested pair has no data in the selected window.
