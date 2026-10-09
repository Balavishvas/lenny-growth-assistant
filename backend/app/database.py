"""SQLAlchemy database connection for PostgreSQL."""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for database models."""


def check_database_connection() -> bool:
    """Return True if PostgreSQL responds to a simple query."""
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return True
