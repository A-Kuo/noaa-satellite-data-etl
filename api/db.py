"""Database session factory for the API."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from noaa_etl.config import settings

_engine = create_engine(settings.db_url, pool_pre_ping=True, pool_size=10, max_overflow=20)
_SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()
