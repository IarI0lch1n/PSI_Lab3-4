"""Unit tests for supported currency and latest snapshot use cases."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest

from app.application.use_cases.get_latest_snapshot import (
    GetLatestSnapshot,
    LatestSnapshotUnavailableError,
)
from app.application.use_cases.list_currencies import ListCurrencies
from app.domain.entities.currency import Currency
from app.domain.entities.rate_entry import RateEntry
from app.domain.entities.rate_snapshot import RateSnapshot
from app.domain.enums.currency_type import CurrencyType
from app.domain.enums.freshness_state import FreshnessState


_SNAPSHOT_ID = UUID("00000000-0000-0000-0000-000000000123")
_CAPTURED_AT = datetime(2026, 10, 28, 12, 0, tzinfo=UTC)
_EFFECTIVE_AT = datetime(2026, 10, 28, 9, 30, tzinfo=UTC)


class StubCurrencyRepository:
    def __init__(self, currencies: tuple[Currency, ...]) -> None:
        self.currencies = currencies

    def get_supported_currencies(self) -> tuple[Currency, ...]:
        return self.currencies


class StubRateRepository:
    def __init__(self, snapshot: RateSnapshot | None) -> None:
        self.snapshot = snapshot

    def get_latest_usable_snapshot(self) -> RateSnapshot | None:
        return self.snapshot


class StubUnitOfWork:
    def __init__(
        self,
        *,
        currencies: tuple[Currency, ...] = (),
        snapshot: RateSnapshot | None = None,
    ) -> None:
        self.currency_repository = StubCurrencyRepository(currencies)
        self.rate_repository = StubRateRepository(snapshot)
        self.enter_count = 0
        self.exit_count = 0
        self.commit_count = 0

    def __enter__(self) -> StubUnitOfWork:
        self.enter_count += 1
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.exit_count += 1

    def commit(self) -> None:
        self.commit_count += 1


def _snapshot() -> RateSnapshot:
    entries = (
        RateEntry(
            snapshot_id=_SNAPSHOT_ID,
            entry_id=UUID("00000000-0000-0000-0000-000000000201"),
            currency="RON",
            normalized_rate_to_mdl=Decimal("3.912345678901234567"),
            provider_name="BNM",
            provider_type=CurrencyType.FIAT,
            effective_at=_EFFECTIVE_AT,
            freshness_state=FreshnessState.FALLBACK,
            is_fallback=True,
            is_stale=False,
        ),
        RateEntry(
            snapshot_id=_SNAPSHOT_ID,
            entry_id=UUID("00000000-0000-0000-0000-000000000202"),
            currency="BTC",
            normalized_rate_to_mdl=Decimal("542240.10"),
            provider_name="CoinGecko",
            provider_type=CurrencyType.CRYPTO,
            effective_at=_EFFECTIVE_AT,
            freshness_state=FreshnessState.CACHED,
            is_fallback=False,
            is_stale=True,
        ),
    )
    return RateSnapshot(_SNAPSHOT_ID, _CAPTURED_AT, entries)


def test_list_currencies_preserves_repository_values_order_and_read_only_lifecycle() -> None:
    currencies = (
        Currency(code="BTC", type=CurrencyType.CRYPTO),
        Currency(code="USD", type=CurrencyType.FIAT),
    )
    unit_of_work = StubUnitOfWork(currencies=currencies)

    result = ListCurrencies(unit_of_work).execute()

    assert result == currencies
    assert result[0] is currencies[0]
    assert result[1] is currencies[1]
    assert isinstance(result, tuple)
    with pytest.raises(TypeError):
        result[0] = currencies[1]  # type: ignore[index]
    assert unit_of_work.enter_count == 1
    assert unit_of_work.exit_count == 1
    assert unit_of_work.commit_count == 0


def test_get_latest_snapshot_returns_repository_object_unchanged() -> None:
    snapshot = _snapshot()
    unit_of_work = StubUnitOfWork(snapshot=snapshot)

    result = GetLatestSnapshot(unit_of_work).execute()

    assert result is snapshot
    assert result.snapshot_id == _SNAPSHOT_ID
    assert result.captured_at == _CAPTURED_AT
    assert result.rates[0].normalized_rate_to_mdl == Decimal(
        "3.912345678901234567"
    )
    assert result.rates[0].provider_name == "BNM"
    assert result.rates[0].effective_at == _EFFECTIVE_AT
    assert result.rates[0].freshness_state is FreshnessState.FALLBACK
    assert result.rates[0].is_fallback is True
    assert result.rates[0].is_stale is False
    assert result.rates[1].provider_name == "CoinGecko"
    assert result.rates[1].effective_at == _EFFECTIVE_AT
    assert result.rates[1].freshness_state is FreshnessState.CACHED
    assert result.rates[1].is_fallback is False
    assert result.rates[1].is_stale is True
    assert unit_of_work.enter_count == 1
    assert unit_of_work.exit_count == 1
    assert unit_of_work.commit_count == 0


def test_get_latest_snapshot_raises_safe_error_when_unavailable() -> None:
    unit_of_work = StubUnitOfWork(snapshot=None)

    with pytest.raises(LatestSnapshotUnavailableError) as error:
        GetLatestSnapshot(unit_of_work).execute()

    assert str(error.value) == "No usable rate snapshot is available."
    assert unit_of_work.enter_count == 1
    assert unit_of_work.exit_count == 1
    assert unit_of_work.commit_count == 0
