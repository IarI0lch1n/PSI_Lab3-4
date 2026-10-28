"""Supported currency and latest-rate API routes."""

from fastapi import APIRouter, Depends

from app.api.dependencies import (
    get_latest_snapshot_use_case,
    get_list_currencies_use_case,
)
from app.api.schemas.currency import CurrenciesResponse
from app.api.schemas.rates import RateSnapshotResponse
from app.application.use_cases.get_latest_snapshot import GetLatestSnapshot
from app.application.use_cases.list_currencies import ListCurrencies

router = APIRouter()


@router.get("/currencies", response_model=CurrenciesResponse)
def list_currencies(
    use_case: ListCurrencies = Depends(get_list_currencies_use_case),
) -> CurrenciesResponse:
    """Return supported currencies in repository-defined order."""
    return CurrenciesResponse.from_domain(use_case.execute())


@router.get("/rates/latest", response_model=RateSnapshotResponse)
def get_latest_rates(
    use_case: GetLatestSnapshot = Depends(get_latest_snapshot_use_case),
) -> RateSnapshotResponse:
    """Return the latest complete usable snapshot."""
    return RateSnapshotResponse.from_domain(use_case.execute())
