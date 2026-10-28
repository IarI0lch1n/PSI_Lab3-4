"""Operational health route for the backend and configured providers."""

import asyncio
from collections.abc import Mapping, Sequence

from fastapi import APIRouter, Depends

from app.api.dependencies import (
    get_latest_snapshot_use_case,
    get_rate_providers,
)
from app.api.schemas.health import HealthResponse
from app.application.use_cases.get_latest_snapshot import (
    GetLatestSnapshot,
    LatestSnapshotUnavailableError,
)
from app.domain.interfaces.rate_provider import RateProvider

router = APIRouter()


async def _probe_provider(
    provider: RateProvider,
    index: int,
) -> tuple[str, str]:
    """Probe one provider while keeping all internal failures out of the response."""
    provider_name = f"Provider {index + 1}"
    try:
        metadata = await provider.get_metadata()
        if not isinstance(metadata, Mapping):
            raise TypeError("Provider metadata must be a mapping.")
        raw_provider_name = metadata.get("provider_name")
        if not isinstance(raw_provider_name, str) or not raw_provider_name.strip():
            raise ValueError("Provider metadata must contain a provider name.")
        provider_name = raw_provider_name.strip()
        await provider.fetch_latest_rates()
    except Exception:
        return provider_name, "unhealthy"
    return provider_name, "healthy"


@router.get("/health", response_model=HealthResponse)
async def get_health(
    providers: Sequence[RateProvider] = Depends(get_rate_providers),
    snapshot_use_case: GetLatestSnapshot = Depends(get_latest_snapshot_use_case),
) -> HealthResponse:
    """Report backend, provider probes, and the last successful snapshot time."""
    probe_results = await asyncio.gather(
        *(_probe_provider(provider, index) for index, provider in enumerate(providers))
    )
    provider_statuses = dict(probe_results)

    try:
        snapshot = snapshot_use_case.execute()
    except LatestSnapshotUnavailableError:
        last_successful_snapshot = None
    else:
        last_successful_snapshot = snapshot.captured_at

    return HealthResponse(
        status=(
            "degraded"
            if any(status == "unhealthy" for status in provider_statuses.values())
            else "ok"
        ),
        backend="healthy",
        providers=provider_statuses,
        last_successful_snapshot=last_successful_snapshot,
    )
