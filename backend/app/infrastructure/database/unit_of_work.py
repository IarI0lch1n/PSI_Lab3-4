"""SQLAlchemy Unit of Work coordinating shared repositories and transactions."""

from types import TracebackType
from typing import Self

from sqlalchemy.orm import Session, sessionmaker

from app.domain.interfaces.currency_repository import CurrencyRepository
from app.domain.interfaces.rate_repository import RateRepository
from app.domain.interfaces.unit_of_work import UnitOfWork
from app.infrastructure.database.session import get_session_factory
from app.infrastructure.repositories.currency_repository import (
    SqlAlchemyCurrencyRepository,
)
from app.infrastructure.repositories.rate_repository import (
    SqlAlchemyRateRepository,
    StalenessResolver,
)


class SqlAlchemyUnitOfWork(UnitOfWork):
    """Own one session and coordinate all participating repository operations."""

    def __init__(
        self,
        session_factory: sessionmaker[Session] | None = None,
        staleness_resolver: StalenessResolver | None = None,
    ) -> None:
        factory = session_factory or get_session_factory()
        self._session = factory()
        self._currency_repository = SqlAlchemyCurrencyRepository(self._session)
        self._rate_repository = SqlAlchemyRateRepository(
            self._session,
            staleness_resolver=staleness_resolver,
        )

    @property
    def currency_repository(self) -> CurrencyRepository:
        return self._currency_repository

    @property
    def rate_repository(self) -> RateRepository:
        return self._rate_repository

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exc_value, traceback
        try:
            self.rollback()
        finally:
            self._session.close()
