"""Contract coverage for historical points and period analytics."""

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_analytics_service
from app.application.services.analytics_service import (
    AnalyticsInputError,
    AnalyticsResult,
    HistoricalPoint,
    HistoryResult,
    ProvenanceSummary,
    Trend,
)
from app.core.config.settings import Settings
from app.domain.entities.rate_entry import RateEntry
from app.domain.enums.currency_type import CurrencyType
from app.domain.enums.freshness_state import FreshnessState
from app.main import create_app


SNAPSHOT_ID = UUID("00000000-0000-0000-0000-000000000801")
SOURCE_EFFECTIVE_AT = datetime(2026, 10, 25, 9, tzinfo=UTC)
TARGET_EFFECTIVE_AT = datetime(2026, 10, 27, 11, 45, tzinfo=UTC)


def rate(
    code: str,
    value: str,
    provider: str,
    provider_type: CurrencyType,
    freshness: FreshnessState,
    effective_at: datetime,
    *,
    fallback: bool = False,
    stale: bool = False,
) -> RateEntry:
    return RateEntry(
        snapshot_id=SNAPSHOT_ID,
        currency=code,
        normalized_rate_to_mdl=Decimal(value),
        provider_name=provider,
        provider_type=provider_type,
        effective_at=effective_at,
        freshness_state=freshness,
        is_fallback=fallback,
        is_stale=stale,
    )


def populated_history(period_days: int) -> HistoryResult:
    return HistoryResult(
        "EUR",
        "BTC",
        period_days,
        (
            HistoricalPoint(
                date(2026, 10, 27),
                Decimal("0.000032100000000000001"),
                SNAPSHOT_ID,
                rate(
                    "EUR",
                    "20",
                    "BNM",
                    CurrencyType.FIAT,
                    FreshnessState.FALLBACK,
                    SOURCE_EFFECTIVE_AT,
                    fallback=True,
                ),
                rate(
                    "BTC",
                    "600000",
                    "CoinGecko",
                    CurrencyType.CRYPTO,
                    FreshnessState.CACHED,
                    TARGET_EFFECTIVE_AT,
                    stale=True,
                ),
            ),
        ),
    )


def populated_analytics(period_days: int) -> AnalyticsResult:
    return AnalyticsResult(
        history=populated_history(period_days),
        minimum=Decimal("0.000032100000000000001"),
        maximum=Decimal("0.000032100000000000001"),
        average=Decimal("0.000032100000000000001"),
        absolute_change=Decimal("0"),
        percentage_change=Decimal("0"),
        trend=Trend.UNCHANGED,
        provenance=ProvenanceSummary(
            point_count=1,
            source_providers=("BNM",),
            target_providers=("CoinGecko",),
            live_entry_count=0,
            fallback_state_entry_count=1,
            cached_entry_count=1,
            stale_entry_count=1,
            fallback_entry_count=1,
        ),
    )


class FakeAnalyticsService:
    def __init__(self, *, empty: bool = False, invalid: bool = False) -> None:
        self.empty = empty
        self.invalid = invalid
        self.calls: list[tuple[str, str, int]] = []

    def get_history(self, base: str, quote: str, days: int) -> HistoryResult:
        self.calls.append((base, quote, days))
        if self.invalid:
            raise AnalyticsInputError("private detail")
        if self.empty:
            return HistoryResult(base, quote, days, ())
        return populated_history(days)

    def get_analytics(self, base: str, quote: str, days: int) -> AnalyticsResult:
        self.calls.append((base, quote, days))
        if self.invalid:
            raise AnalyticsInputError("private detail")
        if self.empty:
            return AnalyticsResult(
                HistoryResult(base, quote, days, ()),
                None,
                None,
                None,
                None,
                None,
                None,
                ProvenanceSummary(0, (), (), 0, 0, 0, 0, 0),
            )
        return populated_analytics(days)


def client(service: FakeAnalyticsService) -> TestClient:
    application = create_app(Settings())
    application.dependency_overrides[get_analytics_service] = lambda: service
    return TestClient(application, raise_server_exceptions=False)


def get(test_client: TestClient, path: str, period: str = "7d"):
    return test_client.get(
        path,
        params={
            "base_currency": "EUR",
            "quote_currency": "BTC",
            "period": period,
        },
    )


def test_history_contract_preserves_both_legs_date_and_snapshot_identity() -> None:
    service = FakeAnalyticsService()
    with client(service) as test_client:
        response = get(test_client, "/api/v1/history")

    assert response.status_code == 200
    payload = response.json()
    assert payload["base_currency"] == "EUR"
    assert payload["quote_currency"] == "BTC"
    assert payload["period"] == "7d"
    assert payload["empty"] is False
    assert "message" not in payload
    point = payload["points"][0]
    assert point["date"] == "2026-10-27"
    assert point["value"] == "0.000032100000000000001"
    assert point["rate_context"]["snapshot_id"] == str(SNAPSHOT_ID)
    assert point["rate_context"]["source_rate"] == {
        "currency": "EUR",
        "provider_name": "BNM",
        "effective_at": "2026-10-25T09:00:00Z",
        "freshness_state": "fallback",
        "is_fallback": True,
        "is_stale": False,
    }
    assert point["rate_context"]["target_rate"] == {
        "currency": "BTC",
        "provider_name": "CoinGecko",
        "effective_at": "2026-10-27T11:45:00Z",
        "freshness_state": "cached",
        "is_fallback": False,
        "is_stale": True,
    }
    assert point["date"] != SOURCE_EFFECTIVE_AT.date().isoformat()
    assert point["rate_context"]["snapshot_id"] != point["date"]
    assert service.calls == [("EUR", "BTC", 7)]


def test_analytics_contract_preserves_exact_statistics_and_separate_counts() -> None:
    service = FakeAnalyticsService()
    with client(service) as test_client:
        response = get(test_client, "/api/v1/analytics", "30d")

    assert response.status_code == 200
    payload = response.json()
    for field in ("minimum", "maximum", "average"):
        assert payload[field] == "0.000032100000000000001"
        assert isinstance(payload[field], str)
    assert payload["absolute_change"] == "0"
    assert payload["percentage_change"] == "0"
    assert payload["trend"] == "UNCHANGED"
    assert payload["provenance_summary"] == {
        "point_count": 1,
        "source_providers": ["BNM"],
        "target_providers": ["CoinGecko"],
        "rate_entry_freshness_counts": {
            "live": 0,
            "fallback": 1,
            "cached": 1,
        },
        "stale_entry_count": 1,
        "fallback_entry_count": 1,
    }
    assert service.calls == [("EUR", "BTC", 30)]


@pytest.mark.parametrize("path", ["/api/v1/history", "/api/v1/analytics"])
def test_empty_contract_is_explicit(path: str) -> None:
    with client(FakeAnalyticsService(empty=True)) as test_client:
        response = get(test_client, path)

    assert response.status_code == 200
    payload = response.json()
    assert payload["points"] == []
    assert payload["empty"] is True
    assert payload["message"] == (
        "No historical data available for this pair in the selected period."
    )
    if path.endswith("analytics"):
        assert "minimum" not in payload
        assert payload["provenance_summary"]["point_count"] == 0


def test_invalid_application_input_is_sanitized() -> None:
    with client(FakeAnalyticsService(invalid=True)) as test_client:
        response = get(test_client, "/api/v1/history")

    assert response.status_code == 422
    assert response.json() == {
        "error": {
            "code": "invalid_analytics_input",
            "message": "Currencies and period must be valid and supported.",
        }
    }
    assert "private detail" not in response.text


def test_openapi_documents_history_legs_and_analytics_freshness_summary() -> None:
    schemas = create_app().openapi()["components"]["schemas"]
    leg = schemas["HistoricalRateLegResponse"]["properties"]
    assert set(leg) == {
        "currency",
        "provider_name",
        "effective_at",
        "freshness_state",
        "is_fallback",
        "is_stale",
    }
    summary = schemas["ProvenanceSummaryResponse"]["properties"]
    assert {
        "rate_entry_freshness_counts",
        "stale_entry_count",
        "fallback_entry_count",
    }.issubset(summary)
    assert schemas["AnalyticsPeriod"]["enum"] == ["7d", "30d"]
