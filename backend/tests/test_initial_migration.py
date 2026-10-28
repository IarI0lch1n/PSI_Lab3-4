"""Offline SQL Server migration checks for the initial schema."""

import importlib.util
from io import StringIO
from pathlib import Path
from types import ModuleType

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy.dialects import mssql


MIGRATION_PATH = (
    Path(__file__).parents[1]
    / "alembic"
    / "versions"
    / "001_initial_rate_schema.py"
)


def _load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("initial_rate_schema", MIGRATION_PATH)
    assert spec is not None
    assert spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration


def _render_migration(operation_name: str) -> str:
    output = StringIO()
    context = MigrationContext.configure(
        dialect=mssql.dialect(),
        opts={"as_sql": True, "output_buffer": output},
    )
    migration = _load_migration()
    with Operations.context(context):
        getattr(migration, operation_name)()
    return output.getvalue()


def test_revision_identifiers_are_valid() -> None:
    migration = _load_migration()
    assert migration.revision == "001_initial_rate_schema"
    assert migration.down_revision is None


def test_upgrade_compiles_expected_sql_server_tables_and_constraints() -> None:
    sql = _render_migration("upgrade")

    for table in ("currencies", "provider_sources", "rate_snapshots", "rate_entries"):
        assert f"CREATE TABLE {table}" in sql
    assert sql.count("CREATE TABLE") == 4
    assert "is_stale" not in sql
    assert "NUMERIC(38, 18)" in sql
    assert "DATETIMEOFFSET" in sql
    assert "UNIQUEIDENTIFIER" in sql
    assert "FOREIGN KEY(currency_code) REFERENCES currencies (code)" in sql
    assert "FOREIGN KEY(snapshot_id) REFERENCES rate_snapshots (id) ON DELETE CASCADE" in sql
    assert "uq_rate_entries_snapshot_currency" in sql


def test_downgrade_compiles_in_reverse_foreign_key_order() -> None:
    sql = _render_migration("downgrade")
    drop_statements = [
        line.strip()
        for line in sql.splitlines()
        if line.strip().startswith("DROP TABLE ")
    ]
    assert drop_statements == [
        "DROP TABLE rate_entries;",
        "DROP TABLE rate_snapshots;",
        "DROP TABLE provider_sources;",
        "DROP TABLE currencies;",
    ]
