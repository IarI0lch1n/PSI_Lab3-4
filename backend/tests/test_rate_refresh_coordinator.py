"""Tests for background current-rate refresh coordination."""

import asyncio

import pytest

from app.application.services.rate_refresh_coordinator import RateRefreshCoordinator
from app.core.config.settings import Settings


@pytest.mark.asyncio
async def test_startup_refresh_runs_once_when_enabled() -> None:
    calls: list[str] = []

    coordinator = RateRefreshCoordinator(
        Settings(
            rate_auto_refresh_enabled=True,
            rate_auto_refresh_interval_seconds=600,
        ),
        refresh_callable=lambda: _record_call(calls),
    )

    await coordinator.start()
    await asyncio.sleep(0.05)
    await coordinator.stop()

    assert calls == ["startup"]


@pytest.mark.asyncio
async def test_startup_does_not_refresh_when_disabled() -> None:
    calls: list[str] = []
    coordinator = RateRefreshCoordinator(
        Settings(rate_auto_refresh_enabled=False, rate_auto_refresh_interval_seconds=600),
        refresh_callable=lambda: _record_call(calls),
    )

    await coordinator.start()
    await asyncio.sleep(0.05)
    await coordinator.stop()

    assert calls == []


@pytest.mark.asyncio
async def test_periodic_loop_retries_after_interval() -> None:
    calls: list[str] = []
    coordinator = RateRefreshCoordinator(
        Settings(rate_auto_refresh_enabled=True, rate_auto_refresh_interval_seconds=60),
        refresh_callable=lambda: _record_call(calls),
    )
    coordinator.settings.rate_auto_refresh_interval_seconds = 0

    await coordinator.start()
    await asyncio.sleep(0.08)
    await coordinator.stop()

    assert len(calls) >= 2


@pytest.mark.asyncio
async def test_concurrency_guard_serializes_parallel_refreshes() -> None:
    active = 0
    max_active = 0

    async def refresh_callable() -> object:
        nonlocal active, max_active
        active += 1
        max_active = max(max_active, active)
        await asyncio.sleep(0.05)
        active -= 1
        return object()

    coordinator = RateRefreshCoordinator(
        Settings(rate_auto_refresh_enabled=True, rate_auto_refresh_interval_seconds=600),
        refresh_callable=refresh_callable,
    )

    await asyncio.gather(
        coordinator.refresh(),
        coordinator.refresh(),
    )

    assert max_active == 1


async def _record_call(calls: list[str]) -> object:
    calls.append("startup")
    await asyncio.sleep(0)
    return object()
