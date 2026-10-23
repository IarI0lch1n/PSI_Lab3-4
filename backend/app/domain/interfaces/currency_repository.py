"""Repository contract for supported currency entities."""

from abc import ABC, abstractmethod
from collections.abc import Sequence

from app.domain.entities.currency import Currency


class CurrencyRepository(ABC):
    """Read access to supported currencies, independent of persistence details."""

    @abstractmethod
    def get_supported_currencies(self) -> Sequence[Currency]:
        """Return the currencies currently supported by the domain."""

    @abstractmethod
    def get_currency_by_code(self, code: str) -> Currency | None:
        """Return a supported currency by code, or ``None`` when it is unknown."""
