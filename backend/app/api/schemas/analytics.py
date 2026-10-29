"""History and analytics response schemas with exact Decimal serialization."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import Enum
from uuid import UUID

from pydantic import AwareDatetime, BaseModel

from app.application.services.analytics_service import (
    AnalyticsResult,
    HistoricalPoint,
    HistoryResult,
    Trend,
)
from app.domain.entities.rate_entry import RateEntry
from app.domain.enums.freshness_state import FreshnessState


class AnalyticsPeriod(str, Enum):
    """Supported public history windows."""

    SEVEN_DAYS = "7d"
    THIRTY_DAYS = "30d"

    @property
    def days(self) -> int:
        return 7 if self is AnalyticsPeriod.SEVEN_DAYS else 30

    @classmethod
    def from_days(cls, days: int) -> AnalyticsPeriod:
        if days == 7:
            return cls.SEVEN_DAYS
        if days == 30:
            return cls.THIRTY_DAYS
        raise ValueError("Analytics period must contain 7 or 30 days.")


class HistoricalRateLegResponse(BaseModel):
    """Independent provenance for one leg of a historical pair point."""

    currency: str
    provider_name: str
    effective_at: AwareDatetime
    freshness_state: FreshnessState
    is_fallback: bool
    is_stale: bool

    @classmethod
    def from_domain(cls, rate: RateEntry) -> HistoricalRateLegResponse:
        return cls(
            currency=rate.currency,
            provider_name=rate.provider_name,
            effective_at=rate.effective_at,
            freshness_state=rate.freshness_state,
            is_fallback=rate.is_fallback,
            is_stale=rate.is_stale,
        )


class HistoricalRateContextResponse(BaseModel):
    """Both rate legs and the snapshot consistency boundary used."""

    source_rate: HistoricalRateLegResponse
    target_rate: HistoricalRateLegResponse
    snapshot_id: UUID


class HistoryPointResponse(BaseModel):
    """One represented date, derived value, and complete provenance."""

    date: date
    value: str
    rate_context: HistoricalRateContextResponse

    @classmethod
    def from_domain(cls, point: HistoricalPoint) -> HistoryPointResponse:
        return cls(
            date=point.date,
            value=_decimal_string(point.value),
            rate_context=HistoricalRateContextResponse(
                source_rate=HistoricalRateLegResponse.from_domain(
                    point.source_rate
                ),
                target_rate=HistoricalRateLegResponse.from_domain(
                    point.target_rate
                ),
                snapshot_id=point.snapshot_id,
            ),
        )


class HistoryResponse(BaseModel):
    """Public historical-pair response with an explicit empty state."""

    base_currency: str
    quote_currency: str
    period: AnalyticsPeriod
    points: list[HistoryPointResponse]
    empty: bool
    message: str | None = None

    @classmethod
    def from_domain(cls, result: HistoryResult) -> HistoryResponse:
        return cls(
            base_currency=result.base_currency,
            quote_currency=result.quote_currency,
            period=AnalyticsPeriod.from_days(result.period_days),
            points=[HistoryPointResponse.from_domain(point) for point in result.points],
            empty=result.empty,
            message=(
                "No historical data available for this pair in the selected period."
                if result.empty
                else None
            ),
        )


class AnalyticsPointResponse(BaseModel):
    """Compact point included alongside period statistics."""

    date: date
    value: str


class FreshnessCountsResponse(BaseModel):
    """Mutually exclusive primary freshness-state counts."""

    live: int
    fallback: int
    cached: int


class ProvenanceSummaryResponse(BaseModel):
    """Provider sets and independent freshness/fallback/stale aggregates."""

    point_count: int
    source_providers: list[str]
    target_providers: list[str]
    rate_entry_freshness_counts: FreshnessCountsResponse
    stale_entry_count: int
    fallback_entry_count: int


class AnalyticsResponse(BaseModel):
    """Public period statistics with exact decimal strings."""

    base_currency: str
    quote_currency: str
    period: AnalyticsPeriod
    points: list[AnalyticsPointResponse]
    minimum: str | None
    maximum: str | None
    average: str | None
    absolute_change: str | None
    percentage_change: str | None
    trend: Trend | None
    provenance_summary: ProvenanceSummaryResponse
    empty: bool
    message: str | None = None

    @classmethod
    def from_domain(cls, result: AnalyticsResult) -> AnalyticsResponse:
        provenance = result.provenance
        return cls(
            base_currency=result.history.base_currency,
            quote_currency=result.history.quote_currency,
            period=AnalyticsPeriod.from_days(result.history.period_days),
            points=[
                AnalyticsPointResponse(
                    date=point.date,
                    value=_decimal_string(point.value),
                )
                for point in result.history.points
            ],
            minimum=_optional_decimal_string(result.minimum),
            maximum=_optional_decimal_string(result.maximum),
            average=_optional_decimal_string(result.average),
            absolute_change=_optional_decimal_string(result.absolute_change),
            percentage_change=_optional_decimal_string(
                result.percentage_change
            ),
            trend=result.trend,
            provenance_summary=ProvenanceSummaryResponse(
                point_count=provenance.point_count,
                source_providers=list(provenance.source_providers),
                target_providers=list(provenance.target_providers),
                rate_entry_freshness_counts=FreshnessCountsResponse(
                    live=provenance.live_entry_count,
                    fallback=provenance.fallback_state_entry_count,
                    cached=provenance.cached_entry_count,
                ),
                stale_entry_count=provenance.stale_entry_count,
                fallback_entry_count=provenance.fallback_entry_count,
            ),
            empty=result.empty,
            message=(
                "No historical data available for this pair in the selected period."
                if result.empty
                else None
            ),
        )


def _decimal_string(value: Decimal) -> str:
    if not isinstance(value, Decimal):
        raise TypeError("Analytics values must be Decimal instances.")
    return format(value, "f")


def _optional_decimal_string(value: Decimal | None) -> str | None:
    return None if value is None else _decimal_string(value)
