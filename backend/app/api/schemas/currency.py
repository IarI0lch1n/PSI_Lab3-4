"""Currency response schemas and domain mappings."""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import BaseModel

from app.domain.entities.currency import Currency
from app.domain.enums.currency_type import CurrencyType


class CurrencyResponse(BaseModel):
    """Public representation of a supported currency."""

    code: str
    name: str
    type: CurrencyType
    is_supported: bool

    @classmethod
    def from_domain(cls, currency: Currency) -> CurrencyResponse:
        """Map a domain currency to its API representation."""
        return cls(
            code=currency.code,
            name=currency.name,
            type=currency.type,
            is_supported=currency.is_supported,
        )


class CurrenciesResponse(BaseModel):
    """Response containing supported currencies in repository order."""

    currencies: list[CurrencyResponse]

    @classmethod
    def from_domain(cls, currencies: Sequence[Currency]) -> CurrenciesResponse:
        """Map a sequence of domain currencies without changing its order."""
        return cls(currencies=[CurrencyResponse.from_domain(currency) for currency in currencies])
