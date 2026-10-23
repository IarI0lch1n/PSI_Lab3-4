"""Focused domain tests for the Currency entity."""

import pytest

from app.domain.entities.currency import (
    Currency,
    CurrencyTypeMismatchError,
    InvalidCurrencyError,
    UnsupportedCurrencyError,
)
from app.domain.enums.currency_type import CurrencyType


def test_valid_fiat_currency() -> None:
    """Verify valid fiat currencies instantiate with correct properties."""
    c = Currency(code="EUR", name="Euro", type=CurrencyType.FIAT)
    assert c.code == "EUR"
    assert c.name == "Euro"
    assert c.type == CurrencyType.FIAT
    assert c.is_supported is True
    assert str(c) == "EUR"

    # Default name fallback
    c2 = Currency(code="MDL", type=CurrencyType.FIAT)
    assert c2.code == "MDL"
    assert c2.name == "Moldovan Leu"
    assert c2.type == CurrencyType.FIAT


def test_valid_crypto_currency() -> None:
    """Verify valid cryptocurrencies instantiate with correct properties."""
    c = Currency(code="BTC", name="Bitcoin", type=CurrencyType.CRYPTO)
    assert c.code == "BTC"
    assert c.name == "Bitcoin"
    assert c.type == CurrencyType.CRYPTO
    assert c.is_supported is True

    # Default name fallback
    c2 = Currency(code="ETH", type=CurrencyType.CRYPTO)
    assert c2.code == "ETH"
    assert c2.name == "Ethereum"
    assert c2.type == CurrencyType.CRYPTO


def test_normalization_of_code() -> None:
    """Verify code is stripped of whitespace and converted to uppercase."""
    c1 = Currency(code=" usd ", type=CurrencyType.FIAT)
    assert c1.code == "USD"

    c2 = Currency(code="sol", type=CurrencyType.CRYPTO)
    assert c2.code == "SOL"

    c3 = Currency(code="\tbtc\n", type=CurrencyType.CRYPTO)
    assert c3.code == "BTC"


def test_currency_type_required() -> None:
    """Verify Currency.type is a required argument with no default."""
    with pytest.raises(TypeError):
        Currency(code="USD")  # type: ignore[call-arg]

    with pytest.raises(TypeError):
        Currency("USD")  # type: ignore[call-arg]


def test_currency_type_from_valid_string() -> None:
    """Verify Currency.type accepts valid strings convertible to CurrencyType."""
    c1 = Currency(code="USD", type="fiat")
    assert c1.type == CurrencyType.FIAT

    c2 = Currency(code="BTC", type="crypto")
    assert c2.type == CurrencyType.CRYPTO

    c3 = Currency(code="EUR", type="FIAT")
    assert c3.type == CurrencyType.FIAT

    c4 = Currency(code="ETH", type=" CRYPTO ")
    assert c4.type == CurrencyType.CRYPTO


def test_invalid_non_string_type_rejection() -> None:
    """Verify invalid non-string types raise CurrencyTypeMismatchError rather than AttributeError."""
    with pytest.raises(CurrencyTypeMismatchError, match="must be CurrencyType or a valid string"):
        Currency(code="USD", type=None)  # type: ignore[arg-type]

    with pytest.raises(CurrencyTypeMismatchError, match="must be CurrencyType or a valid string"):
        Currency(code="USD", type=123)  # type: ignore[arg-type]

    with pytest.raises(CurrencyTypeMismatchError, match="must be CurrencyType or a valid string"):
        Currency(code="USD", type=object())  # type: ignore[arg-type]

    with pytest.raises(CurrencyTypeMismatchError, match="must be CurrencyType or a valid string"):
        Currency(code="USD", type=["fiat"])  # type: ignore[arg-type]


def test_invalid_string_type_rejection() -> None:
    """Verify invalid string types raise CurrencyTypeMismatchError."""
    with pytest.raises(CurrencyTypeMismatchError, match="Unknown currency type"):
        Currency(code="USD", type="invalid_type")


def test_unsupported_currency_rejection() -> None:
    """Verify unsupported currency codes are rejected with UnsupportedCurrencyError."""
    with pytest.raises(UnsupportedCurrencyError, match="not supported"):
        Currency(code="CAD", type=CurrencyType.FIAT)

    with pytest.raises(UnsupportedCurrencyError, match="not supported"):
        Currency(code="XAU", type=CurrencyType.FIAT)

    with pytest.raises(UnsupportedCurrencyError, match="not supported"):
        Currency(code="LTC", type=CurrencyType.CRYPTO)


def test_invalid_empty_code_rejection() -> None:
    """Verify empty or non-alphabetic codes are rejected with InvalidCurrencyError."""
    with pytest.raises(InvalidCurrencyError, match="cannot be empty"):
        Currency(code="", type=CurrencyType.FIAT)

    with pytest.raises(InvalidCurrencyError, match="cannot be empty"):
        Currency(code="   ", type=CurrencyType.FIAT)

    with pytest.raises(InvalidCurrencyError, match="must contain only alphabetic"):
        Currency(code="US1", type=CurrencyType.FIAT)

    with pytest.raises(InvalidCurrencyError, match="must contain only alphabetic"):
        Currency(code="US$", type=CurrencyType.FIAT)

    with pytest.raises(InvalidCurrencyError, match="must be a string"):
        Currency(code=123, type=CurrencyType.FIAT)  # type: ignore[arg-type]


def test_mismatched_currency_type_rejection() -> None:
    """Verify error when CurrencyType does not match the approved currency definition."""
    # Fiat marked as crypto
    with pytest.raises(CurrencyTypeMismatchError, match="fiat currency and cannot have type 'crypto'"):
        Currency(code="USD", type=CurrencyType.CRYPTO)

    # Crypto marked as fiat
    with pytest.raises(CurrencyTypeMismatchError, match="cryptocurrency and cannot have type 'fiat'"):
        Currency(code="BTC", type=CurrencyType.FIAT)


def test_all_18_approved_currencies() -> None:
    """Verify all 10 fiat and 8 crypto currencies defined in the spec can be instantiated."""
    fiat_codes = ["MDL", "USD", "EUR", "RUB", "CNY", "GBP", "RON", "UAH", "CHF", "JPY"]
    crypto_codes = ["BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE", "USDT"]

    assert len(fiat_codes) == 10
    assert len(crypto_codes) == 8

    for code in fiat_codes:
        c = Currency(code=code, type=CurrencyType.FIAT)
        assert c.code == code
        assert c.type == CurrencyType.FIAT
        assert c.is_supported is True
        assert len(c.name) > 0

    for code in crypto_codes:
        c = Currency(code=code, type=CurrencyType.CRYPTO)
        assert c.code == code
        assert c.type == CurrencyType.CRYPTO
        assert c.is_supported is True
        assert len(c.name) > 0
