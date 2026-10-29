"""Focused tests for source-aware refresh candidate assembly."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.application.use_cases.refresh_rates import RefreshRates
from app.domain.entities.currency import (
    SUPPORTED_CRYPTO_CURRENCIES,
    SUPPORTED_FIAT_CURRENCIES,
)
from app.domain.entities.rate_entry import RateEntry
from app.domain.entities.rate_snapshot import RateSnapshot
from app.domain.enums.currency_type import CurrencyType
from app.domain.enums.freshness_state import FreshnessState
from tests.fixtures.fake_rate_providers import (
    FakeBnmRateProvider,
    FakeCoinGeckoRateProvider,
    make_complete_crypto_rates,
    make_complete_fiat_rates,
)


_MONDAY = datetime(2026, 11, 2, 10, 0, tzinfo=UTC)
_FRIDAY = datetime(2026, 10, 30, 10, 0, tzinfo=UTC)
_SNAPSHOT_ID = UUID("00000000-0000-0000-0000-000000000052")


def _previous_snapshot(captured_at: datetime) -> RateSnapshot:
    snapshot_id = uuid4()
    entries = []
    for index, code in enumerate(SUPPORTED_FIAT_CURRENCIES, start=1):
        entries.append(
            RateEntry(
                snapshot_id=snapshot_id,
                currency=code,
                normalized_rate_to_mdl=(
                    Decimal("1") if code == "MDL" else Decimal(index)
                ),
                nominal_unit=1,
                provider_name=(
                    "CurrencyHub Reference" if code == "MDL" else "Fake BNM"
                ),
                provider_type=CurrencyType.FIAT,
                effective_at=_FRIDAY,
                freshness_state=FreshnessState.LIVE,
            )
        )
    for index, code in enumerate(SUPPORTED_CRYPTO_CURRENCIES, start=1):
        entries.append(
            RateEntry(
                snapshot_id=snapshot_id,
                currency=code,
                normalized_rate_to_mdl=Decimal(index),
                nominal_unit=1,
                provider_name="Fake CoinGecko",
                provider_type=CurrencyType.CRYPTO,
                effective_at=captured_at - timedelta(minutes=1),
                freshness_state=FreshnessState.LIVE,
            )
        )
    return RateSnapshot(snapshot_id, captured_at, entries)


def _use_case(now: datetime, *providers, publication_day=None) -> RefreshRates:
    return RefreshRates(
        providers,
        clock=lambda: now,
        snapshot_id_factory=lambda: _SNAPSHOT_ID,
        is_bnm_publication_day=publication_day,
    )


@pytest.mark.asyncio
async def test_weekend_and_official_holiday_previous_bnm_rates_are_fallback() -> None:
    previous = _previous_snapshot(_FRIDAY)
    crypto = FakeCoinGeckoRateProvider(
        latest_rates=make_complete_crypto_rates(effective_at=_FRIDAY)
    )
    saturday = datetime(2026, 10, 31, 10, 0, tzinfo=UTC)

    weekend = await _use_case(
        saturday,
        FakeBnmRateProvider(latest_error=RuntimeError("closed")),
        crypto,
    ).execute(previous_snapshot=previous)
    holiday = await _use_case(
        _MONDAY,
        FakeBnmRateProvider(latest_error=RuntimeError("holiday")),
        crypto,
        publication_day=lambda _: False,
    ).execute(previous_snapshot=previous)

    for snapshot in (weekend, holiday):
        usd = snapshot.get_rate("USD")
        assert usd is not None
        assert usd.effective_at == _FRIDAY
        assert usd.freshness_state is FreshnessState.FALLBACK
        assert usd.is_fallback
        assert not usd.is_stale


@pytest.mark.asyncio
async def test_expected_newer_bnm_rate_is_cached_stale_without_fallback() -> None:
    previous = _previous_snapshot(_FRIDAY)

    snapshot = await _use_case(
        _MONDAY,
        FakeBnmRateProvider(latest_error=RuntimeError("unavailable")),
        FakeCoinGeckoRateProvider(
            latest_rates=make_complete_crypto_rates(effective_at=_MONDAY)
        ),
    ).execute(previous_snapshot=previous)

    usd = snapshot.get_rate("USD")
    assert usd is not None
    assert usd.effective_at == _FRIDAY
    assert usd.freshness_state is FreshnessState.CACHED
    assert not usd.is_fallback
    assert usd.is_stale


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("age", "state", "is_stale"),
    [
        (timedelta(minutes=15), FreshnessState.LIVE, False),
        (timedelta(minutes=15, microseconds=1), FreshnessState.CACHED, True),
    ],
)
async def test_crypto_boundary_uses_last_successful_snapshot_time(
    age: timedelta,
    state: FreshnessState,
    is_stale: bool,
) -> None:
    previous = _previous_snapshot(_MONDAY - age)

    snapshot = await _use_case(
        _MONDAY,
        FakeBnmRateProvider(
            latest_rates=make_complete_fiat_rates(effective_at=_MONDAY)
        ),
        FakeCoinGeckoRateProvider(latest_error=RuntimeError("offline")),
    ).execute(previous_snapshot=previous)

    btc = snapshot.get_rate("BTC")
    assert btc is not None
    assert btc.effective_at == previous.get_rate("BTC").effective_at
    assert btc.freshness_state is state
    assert not btc.is_fallback
    assert btc.is_stale is is_stale


@pytest.mark.asyncio
async def test_complete_current_candidate_keeps_independent_provider_context() -> None:
    snapshot = await _use_case(
        _MONDAY,
        FakeBnmRateProvider(
            latest_rates=make_complete_fiat_rates(effective_at=_MONDAY)
        ),
        FakeCoinGeckoRateProvider(
            latest_rates=make_complete_crypto_rates(
                effective_at=_MONDAY - timedelta(hours=2)
            )
        ),
    ).execute()

    assert len(snapshot.rates) == 18
    assert snapshot.get_rate("USD").provider_name == "Fake BNM"
    assert snapshot.get_rate("BTC").provider_name == "Fake CoinGecko"
    assert snapshot.get_rate("BTC").effective_at == _MONDAY - timedelta(hours=2)
    assert snapshot.get_rate("BTC").freshness_state is FreshnessState.LIVE
