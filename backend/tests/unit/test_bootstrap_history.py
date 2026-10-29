"""Unit tests for first-run historical snapshot bootstrapping."""

from datetime import UTC, datetime
from decimal import Decimal
from types import TracebackType

import pytest

from app.application.use_cases.bootstrap_history import BootstrapHistory
from app.domain.entities.currency import (
    SUPPORTED_CRYPTO_CURRENCIES,
    SUPPORTED_FIAT_CURRENCIES,
)
from app.domain.entities.rate_snapshot import RateSnapshot
from app.domain.enums.currency_type import CurrencyType
from app.domain.enums.freshness_state import FreshnessState
from app.domain.interfaces.rate_provider import ProviderRate
from tests.fixtures.fake_rate_providers import FakeRateProvider


class StubRepository:
    def __init__(self, existing: tuple[RateSnapshot, ...] = ()) -> None:
        self.existing = existing
        self.queries: list[tuple[datetime, datetime]] = []
        self.saved: list[RateSnapshot] = []

    def get_historical_snapshots(
        self,
        start_at: datetime,
        end_at: datetime,
        currency_codes=None,
    ) -> tuple[RateSnapshot, ...]:
        del currency_codes
        self.queries.append((start_at, end_at))
        return self.existing

    def save_complete_snapshot(self, snapshot: RateSnapshot) -> None:
        self.saved.append(snapshot)


class StubUnitOfWork:
    def __init__(self, repository: StubRepository) -> None:
        self.rate_repository = repository
        self.commit_calls = 0
        self.exit_error: type[BaseException] | None = None

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exc_value, traceback
        self.exit_error = exc_type

    def commit(self) -> None:
        self.commit_calls += 1


def rates_for_day(day: int, *, include_usdt: bool = True) -> tuple[ProviderRate, ...]:
    effective_at = datetime(2026, 10, day, 18, tzinfo=UTC)
    fiat = tuple(
        ProviderRate(
            code,
            Decimal(index),
            1,
            "Fake BNM",
            CurrencyType.FIAT,
            effective_at,
        )
        for index, code in enumerate(SUPPORTED_FIAT_CURRENCIES, start=1)
        if code != "MDL"
    )
    crypto = tuple(
        ProviderRate(
            code,
            Decimal(index * 100),
            1,
            "Fake CoinGecko",
            CurrencyType.CRYPTO,
            effective_at,
        )
        for index, code in enumerate(SUPPORTED_CRYPTO_CURRENCIES, start=1)
        if include_usdt or code != "USDT"
    )
    return (*fiat, *crypto)


@pytest.mark.asyncio
async def test_bootstrap_persists_complete_daily_normalized_snapshots() -> None:
    day_one = rates_for_day(27)
    day_two_crypto = tuple(
        rate
        for rate in rates_for_day(28)
        if rate.provider_type is CurrencyType.CRYPTO
    )
    provider = FakeRateProvider(historical_rates=(*day_one, *day_two_crypto))
    repository = StubRepository()
    unit_of_work = StubUnitOfWork(repository)

    snapshots = await BootstrapHistory(
        [provider],
        unit_of_work,
        clock=lambda: datetime(2026, 10, 28, 20, tzinfo=UTC),
    ).execute()

    assert snapshots == tuple(repository.saved)
    assert len(snapshots) == 2
    assert all(len(snapshot.rates) == 18 for snapshot in snapshots)
    assert all(
        snapshot.currencies
        == set(SUPPORTED_FIAT_CURRENCIES) | set(SUPPORTED_CRYPTO_CURRENCIES)
        for snapshot in snapshots
    )
    first_usd = snapshots[0].get_rate("USD")
    second_usd = snapshots[1].get_rate("USD")
    assert first_usd is not None and second_usd is not None
    assert first_usd.freshness_state is FreshnessState.LIVE
    assert first_usd.is_fallback is False
    assert second_usd.freshness_state is FreshnessState.FALLBACK
    assert second_usd.is_fallback is True
    assert second_usd.is_stale is False
    assert second_usd.effective_at == first_usd.effective_at
    mdl = snapshots[1].get_rate("MDL")
    assert mdl is not None
    assert mdl.normalized_rate_to_mdl == Decimal("1")
    assert mdl.provider_name == "CurrencyHub Reference"
    assert unit_of_work.commit_calls == 1
    assert provider.historical_call_count == 1
    request = provider.historical_requests[0]
    assert len(request.currency_codes) == 17
    assert request.start_at.date().isoformat() == "2026-09-29"
    assert request.end_at == datetime(2026, 10, 28, 20, tzinfo=UTC)


@pytest.mark.asyncio
async def test_bootstrap_excludes_incomplete_days() -> None:
    complete = rates_for_day(27)
    incomplete_crypto = tuple(
        rate
        for rate in rates_for_day(28, include_usdt=False)
        if rate.provider_type is CurrencyType.CRYPTO
    )
    provider = FakeRateProvider(
        historical_rates=(*complete, *incomplete_crypto)
    )
    repository = StubRepository()

    snapshots = await BootstrapHistory(
        [provider],
        StubUnitOfWork(repository),
        clock=lambda: datetime(2026, 10, 28, 20, tzinfo=UTC),
    ).execute()

    assert len(snapshots) == 1
    assert snapshots[0].captured_at.date().isoformat() == "2026-10-27"


@pytest.mark.asyncio
async def test_bootstrap_is_first_run_only_and_avoids_provider_calls() -> None:
    existing = object()
    repository = StubRepository(existing=(existing,))  # type: ignore[arg-type]
    provider = FakeRateProvider(historical_error=AssertionError("must not fetch"))
    unit_of_work = StubUnitOfWork(repository)

    snapshots = await BootstrapHistory(
        [provider],
        unit_of_work,
        clock=lambda: datetime(2026, 10, 28, 20, tzinfo=UTC),
    ).execute()

    assert snapshots == ()
    assert provider.historical_call_count == 0
    assert repository.saved == []
    assert unit_of_work.commit_calls == 0
