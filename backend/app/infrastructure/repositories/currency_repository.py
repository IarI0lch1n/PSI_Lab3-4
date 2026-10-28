"""SQLAlchemy-backed currency repository."""

from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.entities.currency import Currency
from app.domain.interfaces.currency_repository import CurrencyRepository
from app.infrastructure.database.models import CurrencyModel


class SqlAlchemyCurrencyRepository(CurrencyRepository):
    """Read supported currency entities from the shared SQLAlchemy session."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_supported_currencies(self) -> Sequence[Currency]:
        statement = (
            select(CurrencyModel)
            .where(CurrencyModel.is_supported.is_(True))
            .order_by(CurrencyModel.code.asc())
        )
        rows = self._session.execute(statement).scalars().all()
        return tuple(self._to_domain(row) for row in rows)

    def get_currency_by_code(self, code: str) -> Currency | None:
        normalized_code = code.strip().upper()
        statement = select(CurrencyModel).where(
            CurrencyModel.is_supported.is_(True),
            func.upper(func.trim(CurrencyModel.code)) == normalized_code,
        )
        row = self._session.execute(statement).scalars().first()
        return self._to_domain(row) if row is not None else None

    @staticmethod
    def _to_domain(row: CurrencyModel) -> Currency:
        return Currency(
            code=row.code,
            name=row.name,
            type=row.type,
            is_supported=row.is_supported,
        )
