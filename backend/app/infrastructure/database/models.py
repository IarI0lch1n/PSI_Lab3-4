"""SQLAlchemy mappings for CurrencyHub persistence."""

from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum as PythonEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    Unicode,
)
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.domain.enums.currency_type import CurrencyType
from app.domain.enums.freshness_state import FreshnessState


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _enum_values(enum_type: type[PythonEnum]) -> list[str]:
    return [member.value for member in enum_type]


class Base(DeclarativeBase):
    """Base class for infrastructure ORM mappings."""


class CurrencyModel(Base):
    """Persisted supported currency metadata."""

    __tablename__ = "currencies"

    id: Mapped[UUID] = mapped_column(UNIQUEIDENTIFIER(as_uuid=True), primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(Unicode(8), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(Unicode(100), nullable=False)
    type: Mapped[CurrencyType] = mapped_column(
        Enum(
            CurrencyType,
            name="currency_type",
            native_enum=False,
            length=16,
            values_callable=_enum_values,
        ),
        nullable=False,
    )
    is_supported: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utc_now)

    rate_entries: Mapped[list["RateEntryModel"]] = relationship(
        back_populates="currency",
        passive_deletes=True,
    )


class RateSnapshotModel(Base):
    """Persisted snapshot consistency boundary."""

    __tablename__ = "rate_snapshots"

    id: Mapped[UUID] = mapped_column(UNIQUEIDENTIFIER(as_uuid=True), primary_key=True, default=uuid4)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utc_now)

    entries: Mapped[list["RateEntryModel"]] = relationship(
        back_populates="snapshot",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class RateEntryModel(Base):
    """Persisted normalized rate for one currency in one snapshot."""

    __tablename__ = "rate_entries"
    __table_args__ = (
        UniqueConstraint("snapshot_id", "currency_code", name="uq_rate_entries_snapshot_currency"),
    )

    id: Mapped[UUID] = mapped_column(UNIQUEIDENTIFIER(as_uuid=True), primary_key=True, default=uuid4)
    snapshot_id: Mapped[UUID] = mapped_column(
        UNIQUEIDENTIFIER(as_uuid=True),
        ForeignKey("rate_snapshots.id", ondelete="CASCADE"),
        nullable=False,
    )
    currency_code: Mapped[str] = mapped_column(
        Unicode(8),
        ForeignKey("currencies.code"),
        nullable=False,
    )
    normalized_rate_to_mdl: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    nominal_unit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    provider_name: Mapped[str] = mapped_column(Unicode(100), nullable=False)
    provider_type: Mapped[CurrencyType] = mapped_column(
        Enum(
            CurrencyType,
            name="provider_type",
            native_enum=False,
            length=16,
            values_callable=_enum_values,
        ),
        nullable=False,
    )
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    freshness_state: Mapped[FreshnessState] = mapped_column(
        Enum(
            FreshnessState,
            name="freshness_state",
            native_enum=False,
            length=16,
            values_callable=_enum_values,
        ),
        nullable=False,
    )
    is_fallback: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utc_now)

    snapshot: Mapped[RateSnapshotModel] = relationship(back_populates="entries")
    currency: Mapped[CurrencyModel] = relationship(back_populates="rate_entries")


class ProviderSourceModel(Base):
    """Persisted provider identity and non-secret configuration reference."""

    __tablename__ = "provider_sources"

    id: Mapped[UUID] = mapped_column(UNIQUEIDENTIFIER(as_uuid=True), primary_key=True, default=uuid4)
    provider_name: Mapped[str] = mapped_column(Unicode(100), nullable=False)
    provider_type: Mapped[CurrencyType] = mapped_column(
        Enum(
            CurrencyType,
            name="provider_source_type",
            native_enum=False,
            length=16,
            values_callable=_enum_values,
        ),
        nullable=False,
    )
    config_reference: Mapped[str] = mapped_column(Unicode(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utc_now)
