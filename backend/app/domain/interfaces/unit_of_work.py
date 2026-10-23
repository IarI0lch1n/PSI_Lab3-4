"""Transactional repository access contract."""

from abc import ABC, abstractmethod
from types import TracebackType
from typing import Self

from app.domain.interfaces.currency_repository import CurrencyRepository
from app.domain.interfaces.rate_repository import RateRepository


class UnitOfWork(ABC):
    """Coordinate repository access and transaction lifecycle."""

    @property
    @abstractmethod
    def currency_repository(self) -> CurrencyRepository:
        """Repository participating in this unit of work."""

    @property
    @abstractmethod
    def rate_repository(self) -> RateRepository:
        """Repository participating in this unit of work."""

    @abstractmethod
    def commit(self) -> None:
        """Commit all changes in the current transaction."""

    @abstractmethod
    def rollback(self) -> None:
        """Roll back all changes in the current transaction."""

    @abstractmethod
    def __enter__(self) -> Self:
        """Enter the transaction scope."""

    @abstractmethod
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Exit the transaction scope, committing or rolling back as appropriate."""
