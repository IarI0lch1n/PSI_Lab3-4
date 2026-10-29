"""Historical pair and analytics API routes."""

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_analytics_service
from app.api.schemas.analytics import (
    AnalyticsPeriod,
    AnalyticsResponse,
    HistoryResponse,
)
from app.application.services.analytics_service import AnalyticsService


router = APIRouter()


@router.get(
    "/history",
    response_model=HistoryResponse,
    response_model_exclude_none=True,
)
def get_history(
    base_currency: str = Query(min_length=1),
    quote_currency: str = Query(min_length=1),
    period: AnalyticsPeriod = Query(),
    service: AnalyticsService = Depends(get_analytics_service),
) -> HistoryResponse:
    """Return complete historical pair points for a supported period."""
    return HistoryResponse.from_domain(
        service.get_history(
            base_currency,
            quote_currency,
            period.days,
        )
    )


@router.get(
    "/analytics",
    response_model=AnalyticsResponse,
    response_model_exclude_none=True,
)
def get_analytics(
    base_currency: str = Query(min_length=1),
    quote_currency: str = Query(min_length=1),
    period: AnalyticsPeriod = Query(),
    service: AnalyticsService = Depends(get_analytics_service),
) -> AnalyticsResponse:
    """Return Decimal statistics and provenance summaries for a pair."""
    return AnalyticsResponse.from_domain(
        service.get_analytics(
            base_currency,
            quote_currency,
            period.days,
        )
    )
