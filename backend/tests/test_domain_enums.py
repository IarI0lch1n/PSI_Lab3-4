"""Tests for domain enums: CurrencyType and FreshnessState."""

import pytest
from app.domain.enums.currency_type import CurrencyType
from app.domain.enums.freshness_state import FreshnessState


def test_currency_type_members_and_values() -> None:
    """Verify CurrencyType values and count."""
    assert len(CurrencyType) == 2
    assert set(CurrencyType) == {CurrencyType.FIAT, CurrencyType.CRYPTO}
    assert CurrencyType.FIAT.value == "fiat"
    assert CurrencyType.CRYPTO.value == "crypto"
    assert CurrencyType.FIAT == "fiat"
    assert CurrencyType.CRYPTO == "crypto"


def test_freshness_state_members_and_values() -> None:
    """Verify FreshnessState primary statuses."""
    assert len(FreshnessState) == 3
    assert set(FreshnessState) == {
        FreshnessState.LIVE,
        FreshnessState.FALLBACK,
        FreshnessState.CACHED,
    }
    assert FreshnessState.LIVE.value == "live"
    assert FreshnessState.FALLBACK.value == "fallback"
    assert FreshnessState.CACHED.value == "cached"
    assert FreshnessState.LIVE == "live"
    assert FreshnessState.FALLBACK == "fallback"
    assert FreshnessState.CACHED == "cached"


def test_stale_is_not_a_freshness_state() -> None:
    """Verify stale is strictly NOT included in FreshnessState."""
    values = [state.value for state in FreshnessState]
    assert "stale" not in values
    assert not hasattr(FreshnessState, "STALE")

    with pytest.raises(ValueError):
        FreshnessState("stale")
