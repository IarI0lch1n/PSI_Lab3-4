"""SQLAlchemy engine and session-factory construction."""

from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config.settings import get_settings


def create_session_factory(database_url: str | None = None) -> sessionmaker[Session]:
    """Create a session factory for the configured SQL Server database URL."""
    url = database_url or get_settings().database_url
    engine = create_engine(url, pool_pre_ping=True)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@lru_cache(maxsize=1)
def get_session_factory() -> sessionmaker[Session]:
    """Return the process-wide session factory for the configured database."""
    return create_session_factory()
