"""Use case for listing supported currencies."""

from app.domain.entities.currency import Currency
from app.domain.interfaces.unit_of_work import UnitOfWork


class ListCurrencies:
    """Return supported currencies in repository-defined order."""

    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    def execute(self) -> tuple[Currency, ...]:
        """Load supported currencies without committing a write transaction."""
        with self._unit_of_work as uow:
            currencies = uow.currency_repository.get_supported_currencies()
            return tuple(currencies)
