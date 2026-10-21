"""Currency domain entity with validation for supported fiat and crypto assets."""

from dataclasses import dataclass
from typing import ClassVar, Mapping

from app.domain.enums.currency_type import CurrencyType


class InvalidCurrencyError(ValueError):
    """Raised when a currency code is empty, non-string, or invalid."""


class UnsupportedCurrencyError(ValueError):
    """Raised when a currency code is not among the approved supported currencies."""


class CurrencyTypeMismatchError(ValueError):
    """Raised when a currency type does not match the approved currency definition."""


# Approved canonical supported currencies with default display names
SUPPORTED_FIAT_CURRENCIES: Mapping[str, str] = {
    "MDL": "Moldovan Leu",
    "USD": "US Dollar",
    "EUR": "Euro",
    "RUB": "Russian Ruble",
    "CNY": "Chinese Yuan",
    "GBP": "British Pound",
    "RON": "Romanian Leu",
    "UAH": "Ukrainian Hryvnia",
    "CHF": "Swiss Franc",
    "JPY": "Japanese Yen",
}

SUPPORTED_CRYPTO_CURRENCIES: Mapping[str, str] = {
    "BTC": "Bitcoin",
    "ETH": "Ethereum",
    "SOL": "Solana",
    "BNB": "Binance Coin",
    "XRP": "Ripple",
    "ADA": "Cardano",
    "DOGE": "Dogecoin",
    "USDT": "Tether",
}


@dataclass(frozen=True)
class Currency:
    """Pure domain entity representing a supported Currency in CurrencyHub."""

    code: str
    type: CurrencyType
    name: str = ""
    is_supported: bool = True

    SUPPORTED_FIAT: ClassVar[Mapping[str, str]] = SUPPORTED_FIAT_CURRENCIES
    SUPPORTED_CRYPTO: ClassVar[Mapping[str, str]] = SUPPORTED_CRYPTO_CURRENCIES

    def __post_init__(self) -> None:
        """Validate and normalize currency fields."""
        if not isinstance(self.code, str):
            raise InvalidCurrencyError("Currency code must be a string.")

        normalized_code = self.code.strip().upper()
        if not normalized_code:
            raise InvalidCurrencyError("Currency code cannot be empty.")

        if not normalized_code.isalpha():
            raise InvalidCurrencyError(
                f"Currency code must contain only alphabetic characters, got '{self.code}'."
            )

        # Validate that code belongs to the approved supported set
        is_fiat = normalized_code in SUPPORTED_FIAT_CURRENCIES
        is_crypto = normalized_code in SUPPORTED_CRYPTO_CURRENCIES

        if not (is_fiat or is_crypto):
            raise UnsupportedCurrencyError(
                f"Currency '{normalized_code}' is not supported by CurrencyHub."
            )

        # Validate and normalize CurrencyType (required, non-default)
        raw_type = self.type
        if isinstance(raw_type, CurrencyType):
            currency_type = raw_type
        elif isinstance(raw_type, str):
            try:
                currency_type = CurrencyType(raw_type.strip().lower())
            except ValueError as exc:
                raise CurrencyTypeMismatchError(
                    f"Unknown currency type '{raw_type}' for currency '{normalized_code}'."
                ) from exc
        else:
            raise CurrencyTypeMismatchError(
                f"Currency type must be CurrencyType or a valid string, got {type(raw_type).__name__} ({raw_type!r})."
            )

        if is_fiat and currency_type != CurrencyType.FIAT:
            raise CurrencyTypeMismatchError(
                f"Currency '{normalized_code}' is a fiat currency and cannot have type '{currency_type.value}'."
            )

        if is_crypto and currency_type != CurrencyType.CRYPTO:
            raise CurrencyTypeMismatchError(
                f"Currency '{normalized_code}' is a cryptocurrency and cannot have type '{currency_type.value}'."
            )

        # Determine display name
        display_name = self.name.strip() if isinstance(self.name, str) and self.name.strip() else ""
        if not display_name:
            if is_fiat:
                display_name = SUPPORTED_FIAT_CURRENCIES[normalized_code]
            else:
                display_name = SUPPORTED_CRYPTO_CURRENCIES[normalized_code]

        object.__setattr__(self, "code", normalized_code)
        object.__setattr__(self, "name", display_name)
        object.__setattr__(self, "type", currency_type)
        object.__setattr__(self, "is_supported", True)

    def __str__(self) -> str:
        return self.code
