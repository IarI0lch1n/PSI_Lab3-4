"""Focused route tests for history and analytics response mapping."""

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from fastapi.testclient import TestClient

from app.api.dependencies import get_analytics_service
from app.application.services.analytics_service import (
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


SNAPSHOT_ID = UUID("00000000-0000-0000-0000-000000000701")


def rate(
    code: str,
    value: str,
    provider: str,
    provider_type: CurrencyType,
    freshness: FreshnessState,
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
        effective_at=datetime(2026, 10, 27, 9, tzinfo=UTC),
        freshness_state=freshness,
        is_fallback=fallback,
        is_stale=stale,
    )


def history_result() -> HistoryResult:
    return HistoryResult(
        "EUR",
        "BTC",
        7,
        (
            HistoricalPoint(
                date(2026, 10, 27),
                Decimal("0.0000321"),
                SNAPSHOT_ID,
                rate(
                    "EUR",
                    "20",
                    "BNM",
                    CurrencyType.FIAT,
                    FreshnessState.FALLBACK,
                    fallback=True,
                ),
                rate(
                    "BTC",
                    "600000",
                    "CoinGecko",
                    CurrencyType.CRYPTO,
                    FreshnessState.CACHED,
                    stale=True,
                ),
            ),
        ),
    )


class FakeAnalyticsService:
    def get_history(self, base, quote, days):
        assert (base, quote, days) == ("EUR", "BTC", 7)
        return history_result()

    def get_analytics(self, base, quote, days):
        assert (base, quote, days) == ("EUR", "BTC", 30)
        history = history_result()
        history = HistoryResult(
            history.base_currency,
            history.quote_currency,
            30,
            history.points,
        )
        return AnalyticsResult(
            history,
            Decimal("0.0000321"),
            Decimal("0.0000321"),
            Decimal("0.0000321"),
            Decimal("0"),
            Decimal("0"),
            Trend.UNCHANGED,
            ProvenanceSummary(
                1,
                ("BNM",),
                ("CoinGecko",),
                0,
                1,
                1,
                1,
                1,
            ),
        )


def client() -> TestClient:
    application = create_app(Settings())
    application.dependency_overrides[get_analytics_service] = (
        FakeAnalyticsService
    )
    return TestClient(application, raise_server_exceptions=False)


def test_history_route_exposes_both_independent_rate_legs() -> None:
    with client() as test_client:
        response = test_client.get(
            "/api/v1/history",
            params={
                "base_currency": "EUR",
                "quote_currency": "BTC",
                "period": "7d",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["points"][0]["value"] == "0.0000321"
    assert payload["points"][0]["rate_context"]["snapshot_id"] == str(
        SNAPSHOT_ID
    )
    assert payload["points"][0]["rate_context"]["source_rate"] == {
        "currency": "EUR",
        "provider_name": "BNM",
        "effective_at": "2026-10-27T09:00:00Z",
        "freshness_state": "fallback",
        "is_fallback": True,
        "is_stale": False,
    }
    assert payload["points"][0]["rate_context"]["target_rate"][
        "freshness_state"
    ] == "cached"
    assert payload["points"][0]["rate_context"]["target_rate"]["is_stale"] is True


def test_analytics_route_keeps_primary_and_overlapping_counts_separate() -> None:
    with client() as test_client:
        response = test_client.get(
            "/api/v1/analytics",
            params={
                "base_currency": "EUR",
                "quote_currency": "BTC",
                "period": "30d",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["minimum"] == "0.0000321"
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


def test_routes_require_supported_period_and_all_query_parameters() -> None:
    with client() as test_client:
        invalid_period = test_client.get(
            "/api/v1/history",
            params={
                "base_currency": "EUR",
                "quote_currency": "BTC",
                "period": "14d",
            },
        )
        missing = test_client.get("/api/v1/analytics")

    assert invalid_period.status_code == 422
    assert missing.status_code == 422
