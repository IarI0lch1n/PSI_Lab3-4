"""Unit tests for first-run historical snapshot bootstrapping."""

from datetime import UTC, datetime
from decimal import Decimal
from types import TracebackType
from zoneinfo import ZoneInfo

import pytest

from app.application.services.analytics_service import AnalyticsService
from app.application.use_cases.bootstrap_history import BootstrapHistory
from app.domain.entities.currency import (
    SUPPORTED_CRYPTO_CURRENCIES,
    SUPPORTED_FIAT_CURRENCIES,
)
from app.domain.entities.rate_snapshot import RateSnapshot
from app.domain.enums.currency_type import CurrencyType
from app.domain.enums.freshness_state import FreshnessState
from app.domain.interfaces.rate_provider import (
    HistoricalProviderQuote,
    ProviderRate,
)
from tests.fixtures.fake_rate_providers import (
    FakeBnmRateProvider,
    FakeCoinGeckoRateProvider,
    FakeRateProvider,
)


_MOLDOVA_TIMEZONE = ZoneInfo("Europe/Chisinau")


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
        self.queries.append((start_at, end_at))
        snapshots = (*self.existing, *self.saved)
        filtered = []
        for snapshot in snapshots:
            if not start_at <= snapshot.captured_at <= end_at:
                continue
            if currency_codes is None:
                filtered.append(snapshot)
                continue
            rates = [
                rate
                for rate in snapshot.rates
                if rate.currency in currency_codes
            ]
            if rates:
                filtered.append(
                    RateSnapshot(snapshot.snapshot_id, snapshot.captured_at, rates)
                )
        return tuple(filtered)

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


def rates_for_date(
    effective_at: datetime,
    *,
    include_usdt: bool = True,
) -> tuple[ProviderRate | HistoricalProviderQuote, ...]:
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
        HistoricalProviderQuote(
            currency=code,
            quoted_price=Decimal(index * 100),
            quote_currency="USD",
            provider_name="Fake CoinGecko",
            provider_type=CurrencyType.CRYPTO,
            effective_at=effective_at,
        )
        for index, code in enumerate(SUPPORTED_CRYPTO_CURRENCIES, start=1)
        if include_usdt or code != "USDT"
    )
    return (*fiat, *crypto)


def rates_for_day(day: int, *, include_usdt: bool = True) -> tuple[ProviderRate, ...]:
    return rates_for_date(
        datetime(2026, 10, day, 18, tzinfo=UTC),
        include_usdt=include_usdt,
    )


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
    bitcoin = snapshots[1].get_rate("BTC")
    assert bitcoin is not None
    assert bitcoin.normalized_rate_to_mdl == Decimal("200")
    assert bitcoin.provider_name == "Fake CoinGecko"
    assert bitcoin.provider_type is CurrencyType.CRYPTO
    assert bitcoin.effective_at == datetime(2026, 10, 28, 18, tzinfo=UTC)
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
async def test_bootstrap_does_not_persist_crypto_quotes_without_usd_bridge() -> None:
    complete_day = rates_for_day(27)
    next_day_quotes = tuple(
        rate
        for rate in rates_for_day(28)
        if isinstance(rate, HistoricalProviderQuote)
    )
    rates_without_usd_bridge = tuple(
        rate
        for rate in complete_day
        if not (isinstance(rate, ProviderRate) and rate.currency == "USD")
    ) + next_day_quotes
    repository = StubRepository()

    snapshots = await BootstrapHistory(
        [FakeRateProvider(historical_rates=rates_without_usd_bridge)],
        StubUnitOfWork(repository),
        clock=lambda: datetime(2026, 10, 28, 20, tzinfo=UTC),
    ).execute()

    assert snapshots == ()
    assert repository.saved == []


@pytest.mark.asyncio
async def test_bootstrap_incrementally_fills_missing_days_and_is_idempotent() -> None:
    repository = StubRepository()
    unit_of_work = StubUnitOfWork(repository)

    original_provider = FakeRateProvider(
        historical_rates=rates_for_day(28)
    )
    original_snapshots = await BootstrapHistory(
        [original_provider],
        unit_of_work,
        clock=lambda: datetime(2026, 10, 28, 20, tzinfo=UTC),
    ).execute()
    assert len(original_snapshots) == 1
    original_snapshot = original_snapshots[0]

    friday_rates = rates_for_date(datetime(2026, 10, 30, 18, tzinfo=UTC))
    later_fiat = tuple(
        rate
        for day in (2, 3, 4)
        for rate in rates_for_date(
            datetime(2026, 11, day, 18, tzinfo=UTC)
        )
        if isinstance(rate, ProviderRate)
    )
    later_crypto = tuple(
        rate
        for day in (2, 3, 4)
        for rate in rates_for_date(
            datetime(2026, 11, day, 18, tzinfo=UTC)
        )
        if isinstance(rate, HistoricalProviderQuote)
    )
    later_rates = [
        *rates_for_day(28),
        *(
            rate
            for rate in friday_rates
            if isinstance(rate, ProviderRate)
        ),
        *later_fiat,
        *later_crypto,
        *(
            rate
            for rate in rates_for_date(
                datetime(2026, 11, 1, 18, tzinfo=UTC)
            )
            if isinstance(rate, HistoricalProviderQuote)
        ),
    ]
    bnm_rates = tuple(
        rate for rate in later_rates if isinstance(rate, ProviderRate)
    )
    coingecko_quotes = tuple(
        rate
        for rate in later_rates
        if isinstance(rate, HistoricalProviderQuote)
    )
    later_bnm_provider = FakeBnmRateProvider(historical_rates=bnm_rates)
    later_coingecko_provider = FakeCoinGeckoRateProvider(
        historical_rates=coingecko_quotes
    )
    later_clock = lambda: datetime(2026, 11, 4, 20, tzinfo=UTC)
    later_snapshots = await BootstrapHistory(
        [later_bnm_provider, later_coingecko_provider],
        unit_of_work,
        clock=later_clock,
    ).execute()

    assert [
        snapshot.captured_at.astimezone(_MOLDOVA_TIMEZONE).date().isoformat()
        for snapshot in later_snapshots
    ] == ["2026-11-01", "2026-11-02", "2026-11-03", "2026-11-04"]
    assert all(len(snapshot.rates) == 18 for snapshot in later_snapshots)
    assert later_bnm_provider.historical_call_count == 1
    assert later_coingecko_provider.historical_call_count == 1
    assert later_bnm_provider.historical_requests[0].end_at == later_clock()
    assert later_coingecko_provider.historical_requests[0].end_at == later_clock()
    assert repository.saved[0] is original_snapshot
    assert len(repository.saved) == 5
    persisted_dates = [
        snapshot.captured_at.astimezone(_MOLDOVA_TIMEZONE).date()
        for snapshot in repository.saved
    ]
    assert len(persisted_dates) == len(set(persisted_dates))

    reused_usd = next(
        snapshot.get_rate("USD")
        for snapshot in later_snapshots
        if snapshot.captured_at.astimezone(_MOLDOVA_TIMEZONE).day == 1
    )
    assert reused_usd is not None
    assert reused_usd.provider_name == "Fake BNM"
    assert reused_usd.effective_at == datetime(2026, 10, 30, 18, tzinfo=UTC)
    assert reused_usd.freshness_state is FreshnessState.FALLBACK
    assert reused_usd.is_fallback is True
    assert reused_usd.is_stale is False
    normalized_bitcoin = next(
        snapshot.get_rate("BTC")
        for snapshot in later_snapshots
        if snapshot.captured_at.astimezone(_MOLDOVA_TIMEZONE).day == 1
    )
    assert normalized_bitcoin is not None
    assert normalized_bitcoin.normalized_rate_to_mdl == Decimal("200")
    assert normalized_bitcoin.provider_name == "Fake CoinGecko"
    assert normalized_bitcoin.provider_type is CurrencyType.CRYPTO
    assert normalized_bitcoin.effective_at == datetime(
        2026, 11, 1, 18, tzinfo=UTC
    )

    analytics = AnalyticsService(
        unit_of_work,
        clock=later_clock,
    )
    seven_day_analytics = analytics.get_analytics("EUR", "USD", 7)
    thirty_day_analytics = analytics.get_analytics("EUR", "USD", 30)
    seven_day_history = seven_day_analytics.history
    thirty_day_history = thirty_day_analytics.history
    assert not seven_day_analytics.empty
    assert seven_day_analytics.provenance.point_count == 4
    assert not thirty_day_analytics.empty
    assert thirty_day_analytics.provenance.point_count == 5
    assert [point.date.isoformat() for point in seven_day_history.points] == [
        "2026-11-01",
        "2026-11-02",
        "2026-11-03",
        "2026-11-04",
    ]
    assert [point.date.isoformat() for point in thirty_day_history.points] == [
        "2026-10-28",
        "2026-11-01",
        "2026-11-02",
        "2026-11-03",
        "2026-11-04",
    ]

    commit_count = unit_of_work.commit_calls
    idempotent_bnm_provider = FakeBnmRateProvider(historical_rates=bnm_rates)
    idempotent_coingecko_provider = FakeCoinGeckoRateProvider(
        historical_rates=coingecko_quotes
    )
    repeated = await BootstrapHistory(
        [idempotent_bnm_provider, idempotent_coingecko_provider],
        unit_of_work,
        clock=later_clock,
    ).execute()
    assert repeated == ()
    assert idempotent_bnm_provider.historical_call_count == 1
    assert idempotent_coingecko_provider.historical_call_count == 1
    assert repository.saved[0] is original_snapshot
    assert len(repository.saved) == 5
    assert unit_of_work.commit_calls == commit_count
