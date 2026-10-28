"""User-story conversion matrix and domain-provenance tests."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import NAMESPACE_OID, UUID, uuid5

import pytest

from app.application.use_cases.convert_currency import (
    ConversionRateUnavailableError,
    ConversionSnapshotUnavailableError,
    ConvertCurrency,
    InvalidConversionInputError,
)
from app.domain.entities.rate_entry import RateEntry
from app.domain.entities.rate_snapshot import RateSnapshot
from app.domain.enums.currency_type import CurrencyType
from app.domain.enums.freshness_state import FreshnessState

SNAPSHOT_ID = UUID("00000000-0000-0000-0000-000000000501")
CAPTURED_AT = datetime(2026, 10, 28, 12, 0, tzinfo=UTC)
FIAT_EFFECTIVE_AT = datetime(2026, 10, 27, 9, 0, tzinfo=UTC)
CRYPTO_EFFECTIVE_AT = datetime(2026, 10, 28, 11, 45, tzinfo=UTC)


class FakeRateRepository:
    def __init__(self, snapshot: RateSnapshot | None) -> None:
        self.snapshot = snapshot
        self.latest_snapshot_calls = 0

    def get_latest_usable_snapshot(self) -> RateSnapshot | None:
        self.latest_snapshot_calls += 1
        return self.snapshot


class FakeUnitOfWork:
    def __init__(self, snapshot: RateSnapshot | None) -> None:
        self.rate_repository = FakeRateRepository(snapshot)
        self.enter_count = 0
        self.exit_count = 0
        self.commit_count = 0

    def __enter__(self) -> "FakeUnitOfWork":
        self.enter_count += 1
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.exit_count += 1

    def commit(self) -> None:
        self.commit_count += 1


def _rate(
    currency: str,
    normalized_rate: str,
    provider_name: str,
    provider_type: CurrencyType,
    effective_at: datetime,
    freshness_state: FreshnessState = FreshnessState.LIVE,
    *,
    is_fallback: bool = False,
    is_stale: bool = False,
) -> RateEntry:
    return RateEntry(
        snapshot_id=SNAPSHOT_ID,
        entry_id=uuid5(NAMESPACE_OID, f"{SNAPSHOT_ID}:{currency}"),
        currency=currency,
        normalized_rate_to_mdl=Decimal(normalized_rate),
        provider_name=provider_name,
        provider_type=provider_type,
        effective_at=effective_at,
        freshness_state=freshness_state,
        is_fallback=is_fallback,
        is_stale=is_stale,
    )


def _snapshot(
    rates: tuple[RateEntry, ...] | None = None,
) -> RateSnapshot:
    return RateSnapshot(
        SNAPSHOT_ID,
        CAPTURED_AT,
        rates
        if rates is not None
        else (
            _rate(
                "EUR",
                "20.176000000000000001",
                "BNM",
                CurrencyType.FIAT,
                FIAT_EFFECTIVE_AT,
                FreshnessState.FALLBACK,
                is_fallback=True,
            ),
            _rate(
                "USD",
                "17.400000000000000001",
                "BNM",
                CurrencyType.FIAT,
                FIAT_EFFECTIVE_AT,
            ),
            _rate(
                "BTC",
                "1465834.123456789012345678",
                "CoinGecko",
                CurrencyType.CRYPTO,
                CRYPTO_EFFECTIVE_AT,
                FreshnessState.CACHED,
                is_stale=True,
            ),
            _rate(
                "ETH",
                "75000.250000000000000001",
                "CoinGecko",
                CurrencyType.CRYPTO,
                CRYPTO_EFFECTIVE_AT,
            ),
        ),
    )


@pytest.mark.parametrize(
    ("source", "target", "amount"),
    [
        ("EUR", "USD", Decimal("12.34")),
        ("EUR", "BTC", Decimal("123.456789012345678901")),
        ("BTC", "EUR", Decimal("0.001234567890123456789")),
        ("BTC", "ETH", Decimal("2.50")),
        ("EUR", "BTC", Decimal("123.456789012345678901")),
        ("BTC", "EUR", Decimal("0.001234567890123456789")),
    ],
)
def test_conversion_matrix_uses_source_rate_over_target_rate(
    source: str,
    target: str,
    amount: Decimal,
) -> None:
    snapshot = _snapshot()
    unit_of_work = FakeUnitOfWork(snapshot)

    result = ConvertCurrency(unit_of_work).execute(amount, source, target)

    source_rate = snapshot.get_rate(source)
    target_rate = snapshot.get_rate(target)
    assert source_rate is not None
    assert target_rate is not None
    expected_rate = (
        source_rate.normalized_rate_to_mdl / target_rate.normalized_rate_to_mdl
    )
    assert result.rate_value == expected_rate
    assert result.converted_amount == amount * expected_rate
    assert result.source_currency == source
    assert result.target_currency == target
    assert result.snapshot_id == SNAPSHOT_ID
    assert result.source_rate is source_rate
    assert result.target_rate is target_rate
    assert unit_of_work.enter_count == 1
    assert unit_of_work.exit_count == 1
    assert unit_of_work.rate_repository.latest_snapshot_calls == 1
    assert unit_of_work.commit_count == 0


def test_high_precision_decimal_conversion_preserves_all_decimal_input_digits() -> None:
    amount = Decimal("123.456789012345678901")
    snapshot = _snapshot()
    unit_of_work = FakeUnitOfWork(snapshot)

    result = ConvertCurrency(unit_of_work).execute(amount, "EUR", "BTC")

    expected_rate = (
        Decimal("20.176000000000000001")
        / Decimal("1465834.123456789012345678")
    )
    assert result.source_amount is amount
    assert result.rate_value == expected_rate
    assert result.converted_amount == amount * expected_rate


def test_same_currency_preserves_amount_and_uses_same_rate_object() -> None:
    amount = Decimal("123.4500")
    snapshot = _snapshot()
    unit_of_work = FakeUnitOfWork(snapshot)

    result = ConvertCurrency(unit_of_work).execute(amount, "USD", "USD")

    assert result.source_amount is amount
    assert result.converted_amount is amount
    assert result.rate_value == Decimal("1")
    assert result.source_rate is snapshot.get_rate("USD")
    assert result.target_rate is result.source_rate
    assert unit_of_work.rate_repository.latest_snapshot_calls == 1
    assert unit_of_work.commit_count == 0


def test_same_currency_requires_its_rate_entry() -> None:
    unit_of_work = FakeUnitOfWork(_snapshot((_rate(
        "EUR",
        "20.176000000000000001",
        "BNM",
        CurrencyType.FIAT,
        FIAT_EFFECTIVE_AT,
    ),)))

    with pytest.raises(ConversionRateUnavailableError) as error:
        ConvertCurrency(unit_of_work).execute(Decimal("1"), "USD", "USD")

    assert error.value.currency == "USD"
    assert unit_of_work.rate_repository.latest_snapshot_calls == 1
    assert unit_of_work.commit_count == 0


def test_result_preserves_independent_source_and_target_provenance() -> None:
    snapshot = _snapshot()
    source = snapshot.get_rate("EUR")
    target = snapshot.get_rate("BTC")
    assert source is not None
    assert target is not None
    result = ConvertCurrency(FakeUnitOfWork(snapshot)).execute(
        Decimal("1"),
        "EUR",
        "BTC",
    )

    assert result.source_rate is source
    assert result.target_rate is target
    assert (
        result.source_rate.currency,
        result.source_rate.provider_name,
        result.source_rate.effective_at,
        result.source_rate.freshness_state,
        result.source_rate.is_fallback,
        result.source_rate.is_stale,
    ) == (
        "EUR",
        "BNM",
        FIAT_EFFECTIVE_AT,
        FreshnessState.FALLBACK,
        True,
        False,
    )
    assert (
        result.target_rate.currency,
        result.target_rate.provider_name,
        result.target_rate.effective_at,
        result.target_rate.freshness_state,
        result.target_rate.is_fallback,
        result.target_rate.is_stale,
    ) == (
        "BTC",
        "CoinGecko",
        CRYPTO_EFFECTIVE_AT,
        FreshnessState.CACHED,
        False,
        True,
    )


@pytest.mark.parametrize(
    ("source", "target", "missing_currency"),
    [
        ("ETH", "EUR", "ETH"),
        ("EUR", "ETH", "ETH"),
    ],
)
def test_missing_source_or_target_rate_identifies_missing_currency(
    source: str,
    target: str,
    missing_currency: str,
) -> None:
    snapshot = _snapshot(
        (
            _rate(
                "EUR",
                "20.176000000000000001",
                "BNM",
                CurrencyType.FIAT,
                FIAT_EFFECTIVE_AT,
            ),
            _rate(
                "BTC",
                "1465834.123456789012345678",
                "CoinGecko",
                CurrencyType.CRYPTO,
                CRYPTO_EFFECTIVE_AT,
            ),
        )
    )
    unit_of_work = FakeUnitOfWork(snapshot)

    with pytest.raises(ConversionRateUnavailableError) as error:
        ConvertCurrency(unit_of_work).execute(Decimal("1"), source, target)

    assert error.value.currency == missing_currency
    assert str(error.value) == f"No usable rate is available for {missing_currency}."
    assert unit_of_work.rate_repository.latest_snapshot_calls == 1
    assert unit_of_work.exit_count == 1
    assert unit_of_work.commit_count == 0


def test_missing_snapshot_is_controlled_and_read_only() -> None:
    unit_of_work = FakeUnitOfWork(None)

    with pytest.raises(ConversionSnapshotUnavailableError):
        ConvertCurrency(unit_of_work).execute(Decimal("1"), "EUR", "BTC")

    assert unit_of_work.enter_count == 1
    assert unit_of_work.exit_count == 1
    assert unit_of_work.rate_repository.latest_snapshot_calls == 1
    assert unit_of_work.commit_count == 0


@pytest.mark.parametrize(
    "amount",
    [
        "",
        "   ",
        "0",
        Decimal("0"),
        "-1",
        Decimal("-0.001"),
        "not-a-number",
        "NaN",
        "Infinity",
        Decimal("sNaN"),
        True,
        False,
        1.25,
    ],
)
def test_invalid_amount_is_rejected_before_unit_of_work_access(
    amount: object,
) -> None:
    unit_of_work = FakeUnitOfWork(_snapshot())

    with pytest.raises(InvalidConversionInputError):
        ConvertCurrency(unit_of_work).execute(amount, "EUR", "BTC")

    assert unit_of_work.enter_count == 0
    assert unit_of_work.exit_count == 0
    assert unit_of_work.rate_repository.latest_snapshot_calls == 0
    assert unit_of_work.commit_count == 0


@pytest.mark.parametrize(
    ("source", "target"),
    [
        ("", "EUR"),
        ("   ", "EUR"),
        ("ZZZ", "EUR"),
        ("EUR", ""),
        ("EUR", "   "),
        ("EUR", "ZZZ"),
    ],
)
def test_invalid_currency_is_rejected_before_unit_of_work_access(
    source: str,
    target: str,
) -> None:
    unit_of_work = FakeUnitOfWork(_snapshot())

    with pytest.raises(InvalidConversionInputError):
        ConvertCurrency(unit_of_work).execute(Decimal("1"), source, target)

    assert unit_of_work.enter_count == 0
    assert unit_of_work.rate_repository.latest_snapshot_calls == 0


def test_supported_currency_input_is_trimmed_and_uppercased() -> None:
    unit_of_work = FakeUnitOfWork(_snapshot())

    result = ConvertCurrency(unit_of_work).execute(
        Decimal("1.00"),
        " eur ",
        " btc ",
    )

    assert result.source_currency == "EUR"
    assert result.target_currency == "BTC"
    assert unit_of_work.enter_count == 1
    assert unit_of_work.exit_count == 1
    assert unit_of_work.rate_repository.latest_snapshot_calls == 1
    assert unit_of_work.commit_count == 0
