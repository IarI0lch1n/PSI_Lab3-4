"""Focused domain tests for Money and NormalizedRate value objects."""

from decimal import Decimal

import pytest

from app.domain.entities.currency import Currency
from app.domain.enums.currency_type import CurrencyType
from app.domain.value_objects.money import InvalidMoneyError, Money
from app.domain.value_objects.normalized_rate import (
    InvalidNormalizedRateError,
    NormalizedRate,
)


# ==============================================================================
# Money Tests
# ==============================================================================


def test_money_valid_decimal() -> None:
    """Verify Money creation with Decimal."""
    m = Money(Decimal("100.50"))
    assert m.amount == Decimal("100.50")
    assert isinstance(m.amount, Decimal)
    assert m.currency is None
    assert m.is_positive is True
    assert m.is_zero is False


def test_money_valid_string_and_integer() -> None:
    """Verify Money exact conversion from string and integer."""
    m_str = Money(" 250.75 ")
    assert m_str.amount == Decimal("250.75")

    m_int = Money(500)
    assert m_int.amount == Decimal("500")


def test_money_with_currency() -> None:
    """Verify Money with associated Currency entity and string code."""
    c = Currency(code="EUR", type=CurrencyType.FIAT)
    m1 = Money(Decimal("100.00"), currency=c)
    assert m1.currency == "EUR"
    assert str(m1) == "100.00 EUR"

    m2 = Money("50.00", currency="usd")
    assert m2.currency == "USD"
    assert str(m2) == "50.00 USD"


def test_money_binary_float_rejection() -> None:
    """Verify binary floating-point input is rejected."""
    with pytest.raises(InvalidMoneyError, match="Binary floating-point is not permitted"):
        Money(100.50)  # float

    with pytest.raises(InvalidMoneyError, match="Binary floating-point is not permitted"):
        Money(0.0)  # float

    with pytest.raises(InvalidMoneyError, match="Binary floating-point is not permitted"):
        Money(-5.25)  # float


def test_money_zero_rejection_by_default() -> None:
    """Verify zero amount is rejected by default for conversion validation."""
    with pytest.raises(InvalidMoneyError, match="strictly greater than zero"):
        Money(Decimal("0.00"))

    with pytest.raises(InvalidMoneyError, match="strictly greater than zero"):
        Money("0")

    with pytest.raises(InvalidMoneyError, match="strictly greater than zero"):
        Money(0)

    # When allow_zero=True, zero is accepted
    m_zero = Money(Decimal("0.00"), allow_zero=True)
    assert m_zero.amount == Decimal("0.00")
    assert m_zero.is_zero is True
    assert m_zero.is_positive is False


def test_money_negative_rejection() -> None:
    """Verify negative amounts are rejected."""
    with pytest.raises(InvalidMoneyError, match="cannot be negative"):
        Money(Decimal("-10.00"))

    with pytest.raises(InvalidMoneyError, match="cannot be negative"):
        Money("-0.01")

    with pytest.raises(InvalidMoneyError, match="cannot be negative"):
        Money(-100)


def test_money_nan_and_infinity_rejection() -> None:
    """Verify NaN and Infinity Decimal amounts are rejected."""
    with pytest.raises(InvalidMoneyError, match="must be finite, got NaN"):
        Money(Decimal("NaN"))

    with pytest.raises(InvalidMoneyError, match="must be finite, got Infinity"):
        Money(Decimal("Infinity"))

    with pytest.raises(InvalidMoneyError, match="must be finite, got Infinity"):
        Money(Decimal("-Infinity"))


def test_money_boolean_rejection() -> None:
    """Verify booleans are rejected despite being an int subclass."""
    with pytest.raises(InvalidMoneyError, match="Boolean values are not valid"):
        Money(True)

    with pytest.raises(InvalidMoneyError, match="Boolean values are not valid"):
        Money(False)


def test_money_equality_and_comparisons() -> None:
    """Verify Money equality and comparison operators."""
    m1 = Money(Decimal("100.00"), "USD")
    m2 = Money("100.00", "USD")
    m3 = Money(Decimal("100.00"), "EUR")
    m4 = Money(Decimal("200.00"), "USD")

    assert m1 == m2
    assert m1 != m3
    assert m1 != m4
    assert m1 != Decimal("100.00")
    assert m1 != 100
    assert m1 != "100.00"

    assert m1 < m4
    assert m4 > m1
    assert m1 <= m2
    assert m1 >= m2

    # Comparing different currencies raises ValueError
    with pytest.raises(ValueError, match="Cannot compare Money with different currencies"):
        _ = m1 < m3


def test_money_equality_includes_currency_and_hash_is_consistent() -> None:
    """Money equality and hashing use both amount and currency."""
    usd = Money("100", "USD")
    same_usd = Money("100", "USD")
    no_currency = Money("100", None)

    assert usd == same_usd
    assert usd != no_currency
    assert hash(usd) == hash(same_usd)


def test_money_is_immutable_after_construction() -> None:
    """Money's internal amount and currency cannot be reassigned."""
    money = Money("100", "USD")

    with pytest.raises(AttributeError, match="immutable"):
        money._amount = Decimal("200")

    with pytest.raises(AttributeError, match="immutable"):
        money._currency = "EUR"

    assert money.amount == Decimal("100")
    assert money.currency == "USD"


def test_money_arithmetic() -> None:
    """Verify exact Decimal arithmetic on Money."""
    m1 = Money(Decimal("100.50"), "USD")
    m2 = Money(Decimal("50.25"), "USD")

    # Addition
    res_add = m1 + m2
    assert res_add.amount == Decimal("150.75")
    assert res_add.currency == "USD"

    # Subtraction
    res_sub = m1 - m2
    assert res_sub.amount == Decimal("50.25")
    assert res_sub.currency == "USD"

    # Multiplication by scalar
    res_mul = m1 * 2
    assert res_mul.amount == Decimal("201.00")

    # Division by scalar
    res_div = m1 / 2
    assert res_div.amount == Decimal("50.25")

    # Binary float operand rejection in arithmetic
    with pytest.raises(InvalidMoneyError, match="Binary floating-point is not permitted"):
        _ = m1 * 1.5

    with pytest.raises(InvalidMoneyError, match="Binary floating-point is not permitted"):
        _ = m1 / 2.0


# ==============================================================================
# NormalizedRate Tests
# ==============================================================================


def test_normalized_rate_valid_decimal() -> None:
    """Verify NormalizedRate creation with Decimal."""
    nr = NormalizedRate(Decimal("17.40"))
    assert nr.rate == Decimal("17.40")
    assert nr.value == Decimal("17.40")
    assert nr.rate_to_mdl == Decimal("17.40")
    assert str(nr) == "17.40"


def test_normalized_rate_valid_string_and_integer() -> None:
    """Verify NormalizedRate conversion from string and integer."""
    nr_str = NormalizedRate("542240.10")
    assert nr_str.rate == Decimal("542240.10")

    nr_int = NormalizedRate(1)
    assert nr_int.rate == Decimal("1")


def test_normalized_rate_binary_float_rejection() -> None:
    """Verify binary floating-point input is rejected."""
    with pytest.raises(InvalidNormalizedRateError, match="Binary floating-point is not permitted"):
        NormalizedRate(17.40)  # float

    with pytest.raises(InvalidNormalizedRateError, match="Binary floating-point is not permitted"):
        NormalizedRate(1.0)


def test_normalized_rate_zero_rejection() -> None:
    """Verify zero normalized rate is strictly rejected."""
    with pytest.raises(InvalidNormalizedRateError, match="strictly greater than zero"):
        NormalizedRate(Decimal("0.00"))

    with pytest.raises(InvalidNormalizedRateError, match="strictly greater than zero"):
        NormalizedRate("0")

    with pytest.raises(InvalidNormalizedRateError, match="strictly greater than zero"):
        NormalizedRate(0)


def test_normalized_rate_negative_rejection() -> None:
    """Verify negative normalized rate is strictly rejected."""
    with pytest.raises(InvalidNormalizedRateError, match="strictly greater than zero"):
        NormalizedRate(Decimal("-17.40"))

    with pytest.raises(InvalidNormalizedRateError, match="strictly greater than zero"):
        NormalizedRate("-0.0001")


def test_normalized_rate_nan_and_infinity_rejection() -> None:
    """Verify NaN and Infinity normalized rates are rejected."""
    with pytest.raises(InvalidNormalizedRateError, match="must be finite, got NaN"):
        NormalizedRate(Decimal("NaN"))

    with pytest.raises(InvalidNormalizedRateError, match="must be finite, got Infinity"):
        NormalizedRate(Decimal("Infinity"))

    with pytest.raises(InvalidNormalizedRateError, match="must be finite, got Infinity"):
        NormalizedRate(Decimal("-Infinity"))


def test_normalized_rate_boolean_rejection() -> None:
    """Verify booleans are rejected."""
    with pytest.raises(InvalidNormalizedRateError, match="Boolean values are not valid"):
        NormalizedRate(True)

    with pytest.raises(InvalidNormalizedRateError, match="Boolean values are not valid"):
        NormalizedRate(False)


def test_normalized_rate_equality_and_comparison() -> None:
    """Verify NormalizedRate comparison and equality semantics."""
    nr1 = NormalizedRate(Decimal("17.40"))
    nr2 = NormalizedRate("17.40")
    nr3 = NormalizedRate(Decimal("19.20"))

    assert nr1 == nr2
    assert nr1 != nr3
    assert nr1 != Decimal("17.40")
    assert nr1 < nr3
    assert nr3 > nr1
    assert nr1 <= nr2
    assert nr1 >= nr2


def test_normalized_rate_is_immutable_after_construction() -> None:
    """NormalizedRate's internal rate cannot be reassigned."""
    rate = NormalizedRate("17.40")

    with pytest.raises(AttributeError, match="immutable"):
        rate._rate = Decimal("19.20")

    assert rate.rate == Decimal("17.40")
