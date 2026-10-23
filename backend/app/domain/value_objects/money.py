"""Decimal-safe Money value object."""

from decimal import Decimal, InvalidOperation
from typing import Any

from app.domain.entities.currency import Currency


class InvalidMoneyError(ValueError):
    """Raised when Money amount validation fails."""


class Money:
    """Immutable domain value object representing a monetary amount with exact Decimal precision."""

    __slots__ = ("_amount", "_currency")

    def __init__(
        self,
        amount: Decimal | str | int,
        currency: str | Currency | None = None,
        *,
        allow_zero: bool = False,
    ) -> None:
        """Initialize Money with validation.

        Args:
            amount: Exact monetary amount (Decimal, string, or int). Float is strictly rejected.
            currency: Optional currency code or Currency entity.
            allow_zero: Whether a zero amount is permitted (default False).
        """
        if isinstance(amount, bool):
            raise InvalidMoneyError("Boolean values are not valid monetary amounts.")

        if isinstance(amount, float):
            raise InvalidMoneyError(
                "Binary floating-point is not permitted for monetary amounts; use Decimal, str, or int."
            )

        if isinstance(amount, (int, str, Decimal)):
            try:
                dec_val = (
                    Decimal(str(amount).strip())
                    if isinstance(amount, (int, str))
                    else amount
                )
            except (InvalidOperation, Exception) as exc:
                raise InvalidMoneyError(f"Invalid monetary amount: {amount!r}") from exc
        else:
            raise InvalidMoneyError(f"Unsupported amount type: {type(amount).__name__}")

        if not dec_val.is_finite():
            if dec_val.is_nan():
                raise InvalidMoneyError("Monetary amount must be finite, got NaN.")
            raise InvalidMoneyError("Monetary amount must be finite, got Infinity.")

        if dec_val < Decimal(0):
            raise InvalidMoneyError(f"Monetary amount cannot be negative, got {dec_val}.")

        if not allow_zero and dec_val == Decimal(0):
            raise InvalidMoneyError("Monetary amount must be strictly greater than zero.")

        # Normalize currency if provided
        curr_code: str | None = None
        if currency is not None:
            if isinstance(currency, Currency):
                curr_code = currency.code
            elif isinstance(currency, str):
                curr_code = currency.strip().upper()
                if not curr_code:
                    raise InvalidMoneyError("Currency code cannot be empty.")
            else:
                raise InvalidMoneyError(
                    f"currency must be a Currency instance, string code, or None, got {type(currency).__name__}."
                )

        object.__setattr__(self, "_amount", dec_val)
        object.__setattr__(self, "_currency", curr_code)

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError(f"{self.__class__.__name__} instances are immutable")

    def __delattr__(self, name: str) -> None:
        raise AttributeError(f"{self.__class__.__name__} instances are immutable")

    @property
    def amount(self) -> Decimal:
        """Return the exact Decimal amount."""
        return self._amount

    @property
    def currency(self) -> str | None:
        """Return the associated currency code if set."""
        return self._currency

    @property
    def is_positive(self) -> bool:
        """Return True if amount is strictly greater than zero."""
        return self._amount > Decimal(0)

    @property
    def is_zero(self) -> bool:
        """Return True if amount is exactly zero."""
        return self._amount == Decimal(0)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Money):
            return False
        return self._amount == other._amount and self._currency == other._currency

    def __lt__(self, other: Any) -> bool:
        if isinstance(other, Money):
            if self._currency and other._currency and self._currency != other._currency:
                raise ValueError(
                    f"Cannot compare Money with different currencies: {self._currency} and {other._currency}"
                )
            return self._amount < other._amount
        return NotImplemented

    def __le__(self, other: Any) -> bool:
        if isinstance(other, Money):
            if self._currency and other._currency and self._currency != other._currency:
                raise ValueError(
                    f"Cannot compare Money with different currencies: {self._currency} and {other._currency}"
                )
            return self._amount <= other._amount
        return NotImplemented

    def __gt__(self, other: Any) -> bool:
        if isinstance(other, Money):
            if self._currency and other._currency and self._currency != other._currency:
                raise ValueError(
                    f"Cannot compare Money with different currencies: {self._currency} and {other._currency}"
                )
            return self._amount > other._amount
        return NotImplemented

    def __ge__(self, other: Any) -> bool:
        if isinstance(other, Money):
            if self._currency and other._currency and self._currency != other._currency:
                raise ValueError(
                    f"Cannot compare Money with different currencies: {self._currency} and {other._currency}"
                )
            return self._amount >= other._amount
        return NotImplemented

    def __add__(self, other: Any) -> "Money":
        if isinstance(other, Money):
            if self._currency and other._currency and self._currency != other._currency:
                raise ValueError(
                    f"Cannot add Money with different currencies: {self._currency} and {other._currency}"
                )
            curr = self._currency or other._currency
            return Money(self._amount + other._amount, currency=curr, allow_zero=True)
        if isinstance(other, (Decimal, int)):
            return Money(self._amount + Decimal(other), currency=self._currency, allow_zero=True)
        if isinstance(other, float):
            raise InvalidMoneyError("Binary floating-point is not permitted; use Decimal, str, or int.")
        return NotImplemented

    def __sub__(self, other: Any) -> "Money":
        if isinstance(other, Money):
            if self._currency and other._currency and self._currency != other._currency:
                raise ValueError(
                    f"Cannot subtract Money with different currencies: {self._currency} and {other._currency}"
                )
            curr = self._currency or other._currency
            return Money(self._amount - other._amount, currency=curr, allow_zero=True)
        if isinstance(other, (Decimal, int)):
            return Money(self._amount - Decimal(other), currency=self._currency, allow_zero=True)
        if isinstance(other, float):
            raise InvalidMoneyError("Binary floating-point is not permitted; use Decimal, str, or int.")
        return NotImplemented

    def __mul__(self, other: Any) -> "Money":
        if isinstance(other, float):
            raise InvalidMoneyError("Binary floating-point is not permitted; use Decimal, str, or int.")
        if isinstance(other, (Decimal, int)):
            return Money(self._amount * Decimal(other), currency=self._currency, allow_zero=True)
        if isinstance(other, str):
            return Money(self._amount * Decimal(other.strip()), currency=self._currency, allow_zero=True)
        return NotImplemented

    def __truediv__(self, other: Any) -> "Money":
        if isinstance(other, float):
            raise InvalidMoneyError("Binary floating-point is not permitted; use Decimal, str, or int.")
        if isinstance(other, (Decimal, int)):
            return Money(self._amount / Decimal(other), currency=self._currency, allow_zero=True)
        if isinstance(other, str):
            return Money(self._amount / Decimal(other.strip()), currency=self._currency, allow_zero=True)
        return NotImplemented

    def __hash__(self) -> int:
        return hash((self._amount, self._currency))

    def __str__(self) -> str:
        return f"{self._amount} {self._currency}" if self._currency else str(self._amount)

    def __repr__(self) -> str:
        return f"Money(amount={self._amount!r}, currency={self._currency!r})"
