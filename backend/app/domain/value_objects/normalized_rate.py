"""NormalizedRate domain value object representing a rate normalized to MDL."""

from decimal import Decimal, InvalidOperation
from typing import Any


class InvalidNormalizedRateError(ValueError):
    """Raised when NormalizedRate validation fails."""


class NormalizedRate:
    """Immutable domain value object representing an exchange rate normalized to MDL (1 unit = X MDL)."""

    __slots__ = ("_rate",)

    def __init__(self, rate: Decimal | str | int) -> None:
        """Initialize NormalizedRate.

        Args:
            rate: Rate value expressed as 1 unit = X MDL (Decimal, string, or int).
        """
        if isinstance(rate, bool):
            raise InvalidNormalizedRateError("Boolean values are not valid rates.")

        if isinstance(rate, float):
            raise InvalidNormalizedRateError(
                "Binary floating-point is not permitted for normalized rates; use Decimal, str, or int."
            )

        if isinstance(rate, (int, str, Decimal)):
            try:
                dec_val = (
                    Decimal(str(rate).strip())
                    if isinstance(rate, (int, str))
                    else rate
                )
            except (InvalidOperation, Exception) as exc:
                raise InvalidNormalizedRateError(f"Invalid rate value: {rate!r}") from exc
        else:
            raise InvalidNormalizedRateError(f"Unsupported rate type: {type(rate).__name__}")

        if not dec_val.is_finite():
            if dec_val.is_nan():
                raise InvalidNormalizedRateError("Normalized rate must be finite, got NaN.")
            raise InvalidNormalizedRateError("Normalized rate must be finite, got Infinity.")

        if dec_val <= Decimal(0):
            raise InvalidNormalizedRateError(
                f"Normalized rate must be strictly greater than zero, got {dec_val}."
            )

        object.__setattr__(self, "_rate", dec_val)

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError(f"{self.__class__.__name__} instances are immutable")

    def __delattr__(self, name: str) -> None:
        raise AttributeError(f"{self.__class__.__name__} instances are immutable")

    @property
    def rate(self) -> Decimal:
        """Return the normalized rate to MDL."""
        return self._rate

    @property
    def value(self) -> Decimal:
        """Alias for rate."""
        return self._rate

    @property
    def rate_to_mdl(self) -> Decimal:
        """Explicit alias indicating 1 unit = X MDL basis."""
        return self._rate

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, NormalizedRate):
            return False
        return self._rate == other._rate

    def __lt__(self, other: Any) -> bool:
        if isinstance(other, NormalizedRate):
            return self._rate < other._rate
        if isinstance(other, (Decimal, int)):
            return self._rate < Decimal(other)
        return NotImplemented

    def __le__(self, other: Any) -> bool:
        if isinstance(other, NormalizedRate):
            return self._rate <= other._rate
        if isinstance(other, (Decimal, int)):
            return self._rate <= Decimal(other)
        return NotImplemented

    def __gt__(self, other: Any) -> bool:
        if isinstance(other, NormalizedRate):
            return self._rate > other._rate
        if isinstance(other, (Decimal, int)):
            return self._rate > Decimal(other)
        return NotImplemented

    def __ge__(self, other: Any) -> bool:
        if isinstance(other, NormalizedRate):
            return self._rate >= other._rate
        if isinstance(other, (Decimal, int)):
            return self._rate >= Decimal(other)
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._rate)

    def __str__(self) -> str:
        return str(self._rate)

    def __repr__(self) -> str:
        return f"NormalizedRate({self._rate!r})"
