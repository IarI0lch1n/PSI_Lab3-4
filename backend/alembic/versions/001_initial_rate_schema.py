"""Create the initial CurrencyHub rate schema.

Revision ID: 001_initial_rate_schema
Revises:
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mssql


revision: str = "001_initial_rate_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "currencies",
        sa.Column("id", mssql.UNIQUEIDENTIFIER(as_uuid=True), nullable=False),
        sa.Column("code", sa.Unicode(length=8), nullable=False),
        sa.Column("name", sa.Unicode(length=100), nullable=False),
        sa.Column("type", sa.String(length=16), nullable=False),
        sa.Column("is_supported", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_table(
        "provider_sources",
        sa.Column("id", mssql.UNIQUEIDENTIFIER(as_uuid=True), nullable=False),
        sa.Column("provider_name", sa.Unicode(length=100), nullable=False),
        sa.Column("provider_type", sa.String(length=16), nullable=False),
        sa.Column("config_reference", sa.Unicode(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "rate_snapshots",
        sa.Column("id", mssql.UNIQUEIDENTIFIER(as_uuid=True), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "rate_entries",
        sa.Column("id", mssql.UNIQUEIDENTIFIER(as_uuid=True), nullable=False),
        sa.Column("snapshot_id", mssql.UNIQUEIDENTIFIER(as_uuid=True), nullable=False),
        sa.Column("currency_code", sa.Unicode(length=8), nullable=False),
        sa.Column("normalized_rate_to_mdl", sa.Numeric(precision=38, scale=18), nullable=False),
        sa.Column("nominal_unit", sa.Integer(), nullable=True),
        sa.Column("provider_name", sa.Unicode(length=100), nullable=False),
        sa.Column("provider_type", sa.String(length=16), nullable=False),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("freshness_state", sa.String(length=16), nullable=False),
        sa.Column("is_fallback", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["currency_code"],
            ["currencies.code"],
        ),
        sa.ForeignKeyConstraint(
            ["snapshot_id"],
            ["rate_snapshots.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "snapshot_id",
            "currency_code",
            name="uq_rate_entries_snapshot_currency",
        ),
    )


def downgrade() -> None:
    op.drop_table("rate_entries")
    op.drop_table("rate_snapshots")
    op.drop_table("provider_sources")
    op.drop_table("currencies")
