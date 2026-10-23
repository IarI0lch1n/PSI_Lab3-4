"""Metadata-only checks for CurrencyHub SQLAlchemy mappings."""

from sqlalchemy import Numeric
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER

from app.infrastructure.database.models import Base, RateEntryModel, RateSnapshotModel


def test_required_tables_exist_without_pairwise_history() -> None:
    assert set(Base.metadata.tables) == {
        "currencies",
        "rate_snapshots",
        "rate_entries",
        "provider_sources",
    }


def test_models_map_required_columns() -> None:
    expected_columns = {
        "currencies": {"id", "code", "name", "type", "is_supported", "created_at"},
        "rate_snapshots": {"id", "captured_at", "created_at"},
        "rate_entries": {
            "id",
            "snapshot_id",
            "currency_code",
            "normalized_rate_to_mdl",
            "nominal_unit",
            "provider_name",
            "provider_type",
            "effective_at",
            "freshness_state",
            "is_fallback",
            "created_at",
        },
        "provider_sources": {
            "id",
            "provider_name",
            "provider_type",
            "config_reference",
            "is_active",
            "created_at",
        },
    }

    for table_name, column_names in expected_columns.items():
        assert set(Base.metadata.tables[table_name].columns.keys()) == column_names


def test_rate_entries_do_not_persist_derived_staleness() -> None:
    assert "is_stale" not in RateEntryModel.__table__.columns


def test_rate_precision_and_uuid_mapping_are_sql_server_compatible() -> None:
    rate_type = RateEntryModel.__table__.c.normalized_rate_to_mdl.type
    assert isinstance(rate_type, Numeric)
    assert (rate_type.precision, rate_type.scale) == (38, 18)
    assert isinstance(RateEntryModel.__table__.c.id.type, UNIQUEIDENTIFIER)


def test_snapshot_entries_relationship_and_foreign_key() -> None:
    snapshot_id = RateEntryModel.__table__.c.snapshot_id
    assert {foreign_key.target_fullname for foreign_key in snapshot_id.foreign_keys} == {
        "rate_snapshots.id"
    }
    assert RateSnapshotModel.entries.property.back_populates == "snapshot"
    assert RateEntryModel.snapshot.property.back_populates == "entries"
