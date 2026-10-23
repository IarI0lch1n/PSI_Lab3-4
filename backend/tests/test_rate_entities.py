"""Focused domain tests for RateEntry and RateSnapshot entities."""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.domain.entities.currency import Currency, UnsupportedCurrencyError
from app.domain.entities.rate_entry import RateEntry, RateEntryError
from app.domain.entities.rate_snapshot import RateSnapshot, RateSnapshotError
from app.domain.enums.currency_type import CurrencyType
from app.domain.enums.freshness_state import FreshnessState


def test_valid_rate_entry_creation() -> None:
    """Verify valid RateEntry instantiation with both Currency entity and string code."""
    snap_id = uuid4()
    entry_id = uuid4()
    now = datetime.now(timezone.utc)

    # 1. With string currency code
    entry = RateEntry(
        entry_id=entry_id,
        snapshot_id=snap_id,
        currency="USD",
        normalized_rate_to_mdl=Decimal("17.40"),
        nominal_unit=1,
        provider_name="BNM",
        provider_type=CurrencyType.FIAT,
        effective_at=now,
        freshness_state=FreshnessState.LIVE,
        is_fallback=False,
        is_stale=False,
    )
    assert entry.entry_id == entry_id
    assert entry.snapshot_id == snap_id
    assert entry.currency == "USD"
    assert entry.normalized_rate_to_mdl == Decimal("17.40")
    assert entry.nominal_unit == 1
    assert entry.provider_name == "BNM"
    assert entry.provider_type == CurrencyType.FIAT
    assert entry.effective_at == now
    assert entry.freshness_state == FreshnessState.LIVE
    assert entry.is_fallback is False
    assert entry.is_stale is False

    # 2. With Currency entity
    btc_currency = Currency(code="BTC", type=CurrencyType.CRYPTO)
    entry_crypto = RateEntry(
        snapshot_id=snap_id,
        currency=btc_currency,
        normalized_rate_to_mdl="542240.10",
        provider_name="CoinGecko",
        provider_type=CurrencyType.CRYPTO,
        effective_at=now,
        freshness_state=FreshnessState.CACHED,
        is_fallback=False,
        is_stale=True,
    )
    assert entry_crypto.currency == "BTC"
    assert entry_crypto.provider_type == CurrencyType.CRYPTO
    assert entry_crypto.normalized_rate_to_mdl == Decimal("542240.10")
    assert isinstance(entry_crypto.entry_id, UUID)
    assert entry_crypto.is_stale is True


def test_non_positive_normalized_rate_rejection() -> None:
    """Verify zero, negative, and invalid rates are rejected."""
    snap_id = uuid4()
    now = datetime.now(timezone.utc)

    # Zero rate
    with pytest.raises(RateEntryError, match="must be positive"):
        RateEntry(
            snapshot_id=snap_id,
            currency="EUR",
            normalized_rate_to_mdl=Decimal("0.00"),
            provider_name="BNM",
            provider_type=CurrencyType.FIAT,
            effective_at=now,
            freshness_state=FreshnessState.LIVE,
        )

    # Negative rate
    with pytest.raises(RateEntryError, match="must be positive"):
        RateEntry(
            snapshot_id=snap_id,
            currency="EUR",
            normalized_rate_to_mdl=Decimal("-1.50"),
            provider_name="BNM",
            provider_type=CurrencyType.FIAT,
            effective_at=now,
            freshness_state=FreshnessState.LIVE,
        )

    # Binary float rejection (financial correctness principle)
    with pytest.raises(RateEntryError, match="Binary floating-point is not permitted"):
        RateEntry(
            snapshot_id=snap_id,
            currency="EUR",
            normalized_rate_to_mdl=19.25,  # float
            provider_name="BNM",
            provider_type=CurrencyType.FIAT,
            effective_at=now,
            freshness_state=FreshnessState.LIVE,
        )


def test_invalid_freshness_state_rejection() -> None:
    """Verify invalid freshness state values are rejected."""
    snap_id = uuid4()
    now = datetime.now(timezone.utc)

    with pytest.raises(RateEntryError, match="Invalid freshness_state"):
        RateEntry(
            snapshot_id=snap_id,
            currency="USD",
            normalized_rate_to_mdl=Decimal("17.40"),
            provider_name="BNM",
            provider_type=CurrencyType.FIAT,
            effective_at=now,
            freshness_state="stale",  # stale is NOT a FreshnessState
        )

    with pytest.raises(RateEntryError, match="Invalid freshness_state"):
        RateEntry(
            snapshot_id=snap_id,
            currency="USD",
            normalized_rate_to_mdl=Decimal("17.40"),
            provider_name="BNM",
            provider_type=CurrencyType.FIAT,
            effective_at=now,
            freshness_state="invalid_state",
        )


def test_independent_fallback_and_stale_values() -> None:
    """Verify is_fallback and is_stale are independent of freshness_state."""
    snap_id = uuid4()
    now = datetime.now(timezone.utc)

    # Cached rate that is NOT fallback and NOT stale
    e1 = RateEntry(
        snapshot_id=snap_id,
        currency="USD",
        normalized_rate_to_mdl=Decimal("17.40"),
        provider_name="BNM",
        provider_type=CurrencyType.FIAT,
        effective_at=now,
        freshness_state=FreshnessState.CACHED,
        is_fallback=False,
        is_stale=False,
    )
    assert e1.freshness_state == FreshnessState.CACHED
    assert e1.is_fallback is False
    assert e1.is_stale is False

    # Fallback rate that is also marked stale (overlap allowed by policy)
    e2 = RateEntry(
        snapshot_id=snap_id,
        currency="USD",
        normalized_rate_to_mdl=Decimal("17.40"),
        provider_name="BNM",
        provider_type=CurrencyType.FIAT,
        effective_at=now,
        freshness_state=FreshnessState.FALLBACK,
        is_fallback=True,
        is_stale=True,
    )
    assert e2.freshness_state == FreshnessState.FALLBACK
    assert e2.is_fallback is True
    assert e2.is_stale is True

    # Live rate with is_fallback=False, is_stale=False
    e3 = RateEntry(
        snapshot_id=snap_id,
        currency="ETH",
        normalized_rate_to_mdl=Decimal("45000.00"),
        provider_name="CoinGecko",
        provider_type=CurrencyType.CRYPTO,
        effective_at=now,
        freshness_state=FreshnessState.LIVE,
        is_fallback=False,
        is_stale=False,
    )
    assert e3.freshness_state == FreshnessState.LIVE
    assert e3.is_fallback is False
    assert e3.is_stale is False


def test_timezone_aware_effective_at_validation() -> None:
    """Verify naive datetime for effective_at is rejected."""
    snap_id = uuid4()
    naive_dt = datetime.now()  # no tzinfo

    with pytest.raises(RateEntryError, match="timezone-aware"):
        RateEntry(
            snapshot_id=snap_id,
            currency="USD",
            normalized_rate_to_mdl=Decimal("17.40"),
            provider_name="BNM",
            provider_type=CurrencyType.FIAT,
            effective_at=naive_dt,
            freshness_state=FreshnessState.LIVE,
        )


def test_provider_type_consistency() -> None:
    """Verify provider_type must match currency asset class (fiat vs crypto)."""
    snap_id = uuid4()
    now = datetime.now(timezone.utc)

    # Fiat currency with crypto provider_type
    with pytest.raises(RateEntryError, match="inconsistent with currency"):
        RateEntry(
            snapshot_id=snap_id,
            currency="USD",
            normalized_rate_to_mdl=Decimal("17.40"),
            provider_name="BNM",
            provider_type=CurrencyType.CRYPTO,
            effective_at=now,
            freshness_state=FreshnessState.LIVE,
        )

    # Crypto currency with fiat provider_type
    with pytest.raises(RateEntryError, match="inconsistent with currency"):
        RateEntry(
            snapshot_id=snap_id,
            currency="BTC",
            normalized_rate_to_mdl=Decimal("540000.00"),
            provider_name="CoinGecko",
            provider_type=CurrencyType.FIAT,
            effective_at=now,
            freshness_state=FreshnessState.LIVE,
        )


def test_unsupported_currency_rejected_in_rate_entry() -> None:
    """Verify rate entry rejects unsupported currencies."""
    snap_id = uuid4()
    now = datetime.now(timezone.utc)

    with pytest.raises(UnsupportedCurrencyError):
        RateEntry(
            snapshot_id=snap_id,
            currency="CAD",
            normalized_rate_to_mdl=Decimal("13.00"),
            provider_name="BNM",
            provider_type=CurrencyType.FIAT,
            effective_at=now,
            freshness_state=FreshnessState.LIVE,
        )


def test_valid_rate_snapshot() -> None:
    """Verify valid RateSnapshot construction and query properties."""
    snap_id = uuid4()
    now = datetime.now(timezone.utc)

    r1 = RateEntry(
        snapshot_id=snap_id,
        currency="USD",
        normalized_rate_to_mdl=Decimal("17.40"),
        provider_name="BNM",
        provider_type=CurrencyType.FIAT,
        effective_at=now,
        freshness_state=FreshnessState.LIVE,
    )
    r2 = RateEntry(
        snapshot_id=snap_id,
        currency="BTC",
        normalized_rate_to_mdl=Decimal("540000.00"),
        provider_name="CoinGecko",
        provider_type=CurrencyType.CRYPTO,
        effective_at=now,
        freshness_state=FreshnessState.LIVE,
    )

    snapshot = RateSnapshot(
        snapshot_id=snap_id,
        captured_at=now,
        rates=[r1, r2],
    )

    assert snapshot.snapshot_id == snap_id
    assert snapshot.captured_at == now
    assert len(snapshot) == 2
    assert snapshot.currencies == {"USD", "BTC"}
    assert snapshot.get_rate("usd") == r1
    assert snapshot.get_rate("BTC") == r2
    assert snapshot.get_rate("EUR") is None


def test_snapshot_empty_rates_rejection() -> None:
    """Verify RateSnapshot cannot have an empty rates collection."""
    snap_id = uuid4()
    now = datetime.now(timezone.utc)

    with pytest.raises(RateSnapshotError, match="at least one rate entry"):
        RateSnapshot(snapshot_id=snap_id, captured_at=now, rates=[])


def test_duplicate_currency_rejection() -> None:
    """Verify duplicate currency entries in the same snapshot are rejected."""
    snap_id = uuid4()
    now = datetime.now(timezone.utc)

    r1 = RateEntry(
        snapshot_id=snap_id,
        currency="USD",
        normalized_rate_to_mdl=Decimal("17.40"),
        provider_name="BNM",
        provider_type=CurrencyType.FIAT,
        effective_at=now,
        freshness_state=FreshnessState.LIVE,
    )
    r2 = RateEntry(
        snapshot_id=snap_id,
        currency="USD",
        normalized_rate_to_mdl=Decimal("17.45"),
        provider_name="BNM_Alt",
        provider_type=CurrencyType.FIAT,
        effective_at=now,
        freshness_state=FreshnessState.CACHED,
    )

    with pytest.raises(RateSnapshotError, match="Duplicate currency entry 'USD'"):
        RateSnapshot(snapshot_id=snap_id, captured_at=now, rates=[r1, r2])


def test_mismatched_snapshot_id_rejection() -> None:
    """Verify rates belonging to a different snapshot_id are rejected."""
    snap_id1 = uuid4()
    snap_id2 = uuid4()
    now = datetime.now(timezone.utc)

    r1 = RateEntry(
        snapshot_id=snap_id1,
        currency="USD",
        normalized_rate_to_mdl=Decimal("17.40"),
        provider_name="BNM",
        provider_type=CurrencyType.FIAT,
        effective_at=now,
        freshness_state=FreshnessState.LIVE,
    )
    r2 = RateEntry(
        snapshot_id=snap_id2,  # different snapshot_id!
        currency="EUR",
        normalized_rate_to_mdl=Decimal("19.20"),
        provider_name="BNM",
        provider_type=CurrencyType.FIAT,
        effective_at=now,
        freshness_state=FreshnessState.LIVE,
    )

    with pytest.raises(RateSnapshotError, match="does not match RateSnapshot id"):
        RateSnapshot(snapshot_id=snap_id1, captured_at=now, rates=[r1, r2])


def test_timezone_aware_captured_at_validation() -> None:
    """Verify naive datetime for captured_at is rejected."""
    snap_id = uuid4()
    now = datetime.now(timezone.utc)
    naive_captured = datetime.now()  # no tzinfo

    r1 = RateEntry(
        snapshot_id=snap_id,
        currency="USD",
        normalized_rate_to_mdl=Decimal("17.40"),
        provider_name="BNM",
        provider_type=CurrencyType.FIAT,
        effective_at=now,
        freshness_state=FreshnessState.LIVE,
    )

    with pytest.raises(RateSnapshotError, match="timezone-aware"):
        RateSnapshot(snapshot_id=snap_id, captured_at=naive_captured, rates=[r1])
