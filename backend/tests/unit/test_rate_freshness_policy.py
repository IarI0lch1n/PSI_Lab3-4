"""Provider-independent tests for the canonical current-rate freshness policy."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.application.services.snapshot_service import SnapshotAssemblyError
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


_FRIDAY = datetime(2026, 10, 30, 9, 0, tzinfo=UTC)
_MONDAY = datetime(2026, 11, 2, 9, 0, tzinfo=UTC)
_CANDIDATE_ID = UUID("00000000-0000-0000-0000-000000000054")


def _snapshot(captured_at: datetime = _FRIDAY) -> RateSnapshot:
    snapshot_id = uuid4()
    rates = []
    for index, code in enumerate(SUPPORTED_FIAT_CURRENCIES, start=1):
        rates.append(
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
        rates.append(
            RateEntry(
                snapshot_id=snapshot_id,
                currency=code,
                normalized_rate_to_mdl=Decimal(index),
                nominal_unit=1,
                provider_name="Fake CoinGecko",
                provider_type=CurrencyType.CRYPTO,
                effective_at=captured_at - timedelta(minutes=2),
                freshness_state=FreshnessState.LIVE,
            )
        )
    return RateSnapshot(snapshot_id, captured_at, rates)


def _refresh(
    now: datetime,
    *,
    fiat_error: bool = False,
    crypto_error: bool = False,
    publication_day: Callable | None = None,
) -> RefreshRates:
    return RefreshRates(
        (
            FakeBnmRateProvider(
                latest_rates=(
                    ()
                    if fiat_error
                    else make_complete_fiat_rates(effective_at=now)
                ),
                latest_error=(RuntimeError("fiat offline") if fiat_error else None),
            ),
            FakeCoinGeckoRateProvider(
                latest_rates=(
                    ()
                    if crypto_error
                    else make_complete_crypto_rates(effective_at=now)
                ),
                latest_error=(
                    RuntimeError("crypto offline") if crypto_error else None
                ),
            ),
        ),
        clock=lambda: now,
        snapshot_id_factory=lambda: _CANDIDATE_ID,
        is_bnm_publication_day=publication_day,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("now", "publication_day"),
    [
        (datetime(2026, 10, 31, 9, 0, tzinfo=UTC), None),
        (_MONDAY, lambda _: False),
    ],
)
async def test_expected_non_publishing_day_fiat_reuse_is_fallback_not_stale(
    now: datetime,
    publication_day: Callable | None,
) -> None:
    previous = _snapshot()

    candidate = await _refresh(
        now,
        fiat_error=True,
        publication_day=publication_day,
    ).assemble_candidate(previous_snapshot=previous)

    for code in tuple(SUPPORTED_FIAT_CURRENCIES)[1:]:
        rate = candidate.get_rate(code)
        assert rate is not None
        assert rate.effective_at == _FRIDAY
        assert rate.freshness_state is FreshnessState.FALLBACK
        assert rate.is_fallback
        assert not rate.is_stale


@pytest.mark.asyncio
async def test_missing_expected_newer_fiat_is_cached_stale_not_fallback() -> None:
    candidate = await _refresh(
        _MONDAY,
        fiat_error=True,
    ).assemble_candidate(previous_snapshot=_snapshot())

    usd = candidate.get_rate("USD")
    assert usd is not None
    assert usd.effective_at == _FRIDAY
    assert usd.freshness_state is FreshnessState.CACHED
    assert not usd.is_fallback
    assert usd.is_stale


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("age", "expected_state", "expected_stale"),
    [
        (timedelta(minutes=15), FreshnessState.LIVE, False),
        (timedelta(minutes=15, microseconds=1), FreshnessState.CACHED, True),
    ],
)
async def test_crypto_staleness_changes_only_after_fifteen_minutes(
    age: timedelta,
    expected_state: FreshnessState,
    expected_stale: bool,
) -> None:
    previous = _snapshot(_MONDAY - age)
    original_btc = previous.get_rate("BTC")
    assert original_btc is not None

    candidate = await _refresh(
        _MONDAY,
        crypto_error=True,
    ).assemble_candidate(previous_snapshot=previous)

    btc = candidate.get_rate("BTC")
    assert btc is not None
    assert btc.effective_at == original_btc.effective_at
    assert btc.provider_name == original_btc.provider_name
    assert btc.freshness_state is expected_state
    assert btc.is_stale is expected_stale
    assert not btc.is_fallback


def _missing_rate(snapshot: RateSnapshot) -> None:
    object.__setattr__(snapshot, "rates", snapshot.rates[:-1])


def _non_positive_rate(snapshot: RateSnapshot) -> None:
    object.__setattr__(snapshot.rates[1], "normalized_rate_to_mdl", Decimal("0"))


def _missing_provider(snapshot: RateSnapshot) -> None:
    object.__setattr__(snapshot.rates[1], "provider_name", "")


def _missing_effective_timestamp(snapshot: RateSnapshot) -> None:
    object.__setattr__(snapshot.rates[1], "effective_at", None)


def _unreadable_capture_timestamp(snapshot: RateSnapshot) -> None:
    object.__setattr__(snapshot, "captured_at", datetime(2026, 10, 30, 9, 0))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "corrupt",
    [
        _missing_rate,
        _non_positive_rate,
        _missing_provider,
        _missing_effective_timestamp,
        _unreadable_capture_timestamp,
    ],
    ids=[
        "incomplete",
        "non-positive-rate",
        "missing-provider",
        "missing-effective-at",
        "unreadable-captured-at",
    ],
)
async def test_unusable_previous_snapshot_cannot_supply_missing_entries(
    corrupt: Callable[[RateSnapshot], None],
) -> None:
    previous = _snapshot()
    corrupt(previous)

    with pytest.raises(SnapshotAssemblyError, match="previous snapshot is unusable"):
        await _refresh(
            _MONDAY,
            crypto_error=True,
        ).assemble_candidate(previous_snapshot=previous)

