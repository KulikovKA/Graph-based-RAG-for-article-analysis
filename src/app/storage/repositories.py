"""Database engine and session setup shared by API and workers."""

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


def make_engine(database_url: str, *, pool_pre_ping: bool = True) -> Engine:
    """Create a SQLAlchemy engine, normalizing PostgreSQL URLs to psycopg 3."""
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return create_engine(database_url, pool_pre_ping=pool_pre_ping)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Return a factory for non-expiring synchronous sessions."""
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
