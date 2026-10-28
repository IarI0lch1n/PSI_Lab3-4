"""Focused tests for the application currency-conversion use case."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import NAMESPACE_OID, UUID, uuid5

import pytest

from app.application.use_cases.convert_currency import (
    ConversionRateUnavailableError,
    ConversionSnapshotUnavailableError,
    ConversionResult,
    ConvertCurrency,
    InvalidConversionInputError,
)
from app.domain.entities.rate_entry import RateEntry
from app.domain.entities.rate_snapshot import RateSnapshot
from app.domain.enums.currency_type import CurrencyType
from app.domain.enums.freshness_state import FreshnessState


_SNAPSHOT_ID = UUID("00000000-0000-0000-0000-000000000301")
_CAPTURED_AT = datetime(2026, 10, 28, 12, 0, tzinfo=UTC)
_EFFECTIVE_AT = datetime(2026, 10, 28, 9, 0, tzinfo=UTC)


class StubRateRepository:
    def __init__(self, snapshot: RateSnapshot | None) -> None:
        self.snapshot = snapshot
        self.latest_snapshot_calls = 0

    def get_latest_usable_snapshot(self) -> RateSnapshot | None:
        self.latest_snapshot_calls += 1
        return self.snapshot


class StubUnitOfWork:
    def __init__(self, snapshot: RateSnapshot | None) -> None:
        self.rate_repository = StubRateRepository(snapshot)
        self.enter_count = 0
        self.exit_count = 0
        self.commit_count = 0

    def __enter__(self) -> "StubUnitOfWork":
        self.enter_count += 1
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.exit_count += 1

    def commit(self) -> None:
        self.commit_count += 1


def _rate(
    currency: str,
    rate: str,
    provider_name: str,
    provider_type: CurrencyType,
    freshness_state: FreshnessState = FreshnessState.LIVE,
    is_fallback: bool = False,
    is_stale: bool = False,
) -> RateEntry:
    return RateEntry(
        snapshot_id=_SNAPSHOT_ID,
        entry_id=uuid5(NAMESPACE_OID, currency),
        currency=currency,
        normalized_rate_to_mdl=Decimal(rate),
        provider_name=provider_name,
        provider_type=provider_type,
        effective_at=_EFFECTIVE_AT,
        freshness_state=freshness_state,
        is_fallback=is_fallback,
        is_stale=is_stale,
    )


def _snapshot(
    rates: tuple[RateEntry, ...] | None = None,
) -> RateSnapshot:
    return RateSnapshot(
        _SNAPSHOT_ID,
        _CAPTURED_AT,
        rates
        or (
            _rate(
                "USD",
                "20.176000000000000001",
                "BNM",
                CurrencyType.FIAT,
                FreshnessState.FALLBACK,
                is_fallback=True,
            ),
            _rate("EUR", "21.4", "BNM", CurrencyType.FIAT),
            _rate(
                "BTC",
                "1465834.123456789012345678",
                "CoinGecko",
                CurrencyType.CRYPTO,
                FreshnessState.CACHED,
                is_stale=True,
            ),
            _rate("ETH", "75000.25", "CoinGecko", CurrencyType.CRYPTO),
        ),
    )


def _execute(
    amount: Decimal | str | int | None,
    source: str = "USD",
    target: str = "EUR",
    *,
    snapshot: RateSnapshot | None = None,
) -> tuple[ConversionResult, StubUnitOfWork]:
    unit_of_work = StubUnitOfWork(snapshot if snapshot is not None else _snapshot())
    return ConvertCurrency(unit_of_work).execute(amount, source, target), unit_of_work


def test_fiat_to_fiat_conversion_uses_normalized_decimal_rates() -> None:
    result, _ = _execute(Decimal("100"), "USD", "EUR")
    expected_rate = Decimal("20.176000000000000001") / Decimal("21.4")

    assert result.rate_value == expected_rate
    assert result.converted_amount == Decimal("100") * expected_rate
    assert result.source_currency == "USD"
    assert result.target_currency == "EUR"


def test_fiat_to_crypto_uses_exact_decimal_formula_and_preserves_provenance() -> None:
    amount = Decimal("123.456789012345678901")
    source_rate = Decimal("20.176000000000000001")
    target_rate = Decimal("1465834.123456789012345678")
    expected_rate = source_rate / target_rate
    expected_amount = amount * expected_rate
    snapshot = _snapshot()
    result, _ = _execute(amount, "USD", "BTC", snapshot=snapshot)

    assert result.source_amount is amount
    assert result.rate_value == expected_rate
    assert result.converted_amount == expected_amount
    assert result.source_rate is snapshot.get_rate("USD")
    assert result.target_rate is snapshot.get_rate("BTC")
    assert result.source_rate.provider_name == "BNM"
    assert result.target_rate.provider_name == "CoinGecko"
    assert result.source_rate.freshness_state is FreshnessState.FALLBACK
    assert result.source_rate.is_fallback is True
    assert result.source_rate.is_stale is False
    assert result.target_rate.freshness_state is FreshnessState.CACHED
    assert result.target_rate.is_fallback is False
    assert result.target_rate.is_stale is True


def test_crypto_to_fiat_conversion() -> None:
    result, _ = _execute(Decimal("0.125"), "BTC", "USD")
    expected_rate = (
        Decimal("1465834.123456789012345678")
        / Decimal("20.176000000000000001")
    )

    assert result.rate_value == expected_rate
    assert result.converted_amount == Decimal("0.125") * expected_rate


def test_crypto_to_crypto_conversion() -> None:
    result, _ = _execute(Decimal("2"), "BTC", "ETH")
    expected_rate = (
        Decimal("1465834.123456789012345678") / Decimal("75000.25")
    )

    assert result.rate_value == expected_rate
    assert result.converted_amount == Decimal("2") * expected_rate


def test_same_currency_returns_original_decimal_and_one_rate_entry() -> None:
    amount = Decimal("123.4500")
    result, _ = _execute(amount, "USD", "USD")

    assert result.source_amount is amount
    assert result.converted_amount is amount
    assert result.converted_amount == Decimal("123.4500")
    assert result.rate_value == Decimal(1)
    assert result.source_rate is result.target_rate
    assert result.source_rate.currency == "USD"


def test_conversion_retrieves_one_snapshot_once_and_never_commits() -> None:
    result, unit_of_work = _execute(Decimal("10"), "USD", "BTC")

    assert result.snapshot_id == _SNAPSHOT_ID
    assert unit_of_work.rate_repository.latest_snapshot_calls == 1
    assert unit_of_work.enter_count == 1
    assert unit_of_work.exit_count == 1
    assert unit_of_work.commit_count == 0


def test_unit_of_work_exits_when_snapshot_is_unavailable() -> None:
    unit_of_work = StubUnitOfWork(None)

    with pytest.raises(ConversionSnapshotUnavailableError) as error:
        ConvertCurrency(unit_of_work).execute(Decimal("1"), "USD", "BTC")

    assert str(error.value) == "No usable rate snapshot is available for conversion."
    assert unit_of_work.rate_repository.latest_snapshot_calls == 1
    assert unit_of_work.enter_count == 1
    assert unit_of_work.exit_count == 1
    assert unit_of_work.commit_count == 0


@pytest.mark.parametrize(
    ("source", "target", "missing_currency"),
    [
        ("ETH", "USD", "ETH"),
        ("USD", "ETH", "ETH"),
    ],
)
def test_missing_required_rate_is_identified(
    source: str,
    target: str,
    missing_currency: str,
) -> None:
    snapshot = _snapshot(
        rates=(
            _rate("USD", "20.176000000000000001", "BNM", CurrencyType.FIAT),
            _rate(
                "BTC",
                "1465834.123456789012345678",
                "CoinGecko",
                CurrencyType.CRYPTO,
            ),
        )
    )
    unit_of_work = StubUnitOfWork(snapshot)

    with pytest.raises(ConversionRateUnavailableError) as error:
        ConvertCurrency(unit_of_work).execute(Decimal("1"), source, target)

    assert error.value.currency == missing_currency
    assert str(error.value) == f"No usable rate is available for {missing_currency}."
    assert unit_of_work.rate_repository.latest_snapshot_calls == 1
    assert unit_of_work.enter_count == 1
    assert unit_of_work.exit_count == 1
    assert unit_of_work.commit_count == 0


@pytest.mark.parametrize(
    "amount",
    [
        None,
        "",
        "   ",
        "not-a-number",
        "0",
        Decimal("0"),
        "-1",
        Decimal("-0.01"),
        "NaN",
        Decimal("sNaN"),
        "Infinity",
        Decimal("-Infinity"),
        True,
        False,
        1.5,
    ],
)
def test_invalid_amount_is_rejected(amount: object) -> None:
    unit_of_work = StubUnitOfWork(_snapshot())

    with pytest.raises(InvalidConversionInputError) as error:
        ConvertCurrency(unit_of_work).execute(amount, "USD", "BTC")

    assert str(error.value) == "Amount must be a finite number greater than zero."
    assert unit_of_work.enter_count == 0
    assert unit_of_work.rate_repository.latest_snapshot_calls == 0
    assert unit_of_work.commit_count == 0


@pytest.mark.parametrize(
    ("source", "target", "message"),
    [
        ("", "USD", "Source"),
        ("   ", "USD", "Source"),
        ("ZZZ", "USD", "Source"),
        (None, "USD", "Source"),
        (123, "USD", "Source"),
        ("USD", "", "Target"),
        ("USD", "ZZZ", "Target"),
        ("USD", None, "Target"),
        ("USD", 123, "Target"),
    ],
)
def test_invalid_currency_is_rejected_before_snapshot_access(
    source: object,
    target: object,
    message: str,
) -> None:
    unit_of_work = StubUnitOfWork(_snapshot())

    with pytest.raises(InvalidConversionInputError) as error:
        ConvertCurrency(unit_of_work).execute(Decimal("1"), source, target)

    assert str(error.value) == f"{message} currency must be a supported currency code."
    assert unit_of_work.enter_count == 0
    assert unit_of_work.rate_repository.latest_snapshot_calls == 0
    assert unit_of_work.commit_count == 0


def test_supported_currency_inputs_are_trimmed_and_uppercased() -> None:
    result, _ = _execute(Decimal("1.00"), " usd ", " btc ")

    assert result.source_currency == "USD"
    assert result.target_currency == "BTC"
