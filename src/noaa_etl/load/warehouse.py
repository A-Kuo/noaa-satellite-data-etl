"""PostGIS warehouse loader."""

from __future__ import annotations

import structlog
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from noaa_etl.config import settings
from noaa_etl.transform.metadata import WarehouseRow

log = structlog.get_logger(__name__)

_INSERT_ACQUISITION = text("""
    INSERT INTO noaa_acquisitions (
        acquisition_id,
        event_name,
        acquisition_date,
        sensor,
        resolution_cm,
        footprint,
        download_url,
        file_size_bytes,
        crs,
        ingested_at
    ) VALUES (
        :acquisition_id,
        :event_name,
        :acquisition_date,
        :sensor,
        :resolution_cm,
        ST_GeomFromText(:footprint_wkt, 4326),
        :download_url,
        :file_size_bytes,
        :crs,
        :ingested_at
    )
    ON CONFLICT (acquisition_id) DO UPDATE SET
        event_name      = EXCLUDED.event_name,
        sensor          = EXCLUDED.sensor,
        resolution_cm   = EXCLUDED.resolution_cm,
        footprint       = EXCLUDED.footprint,
        download_url    = EXCLUDED.download_url,
        file_size_bytes = EXCLUDED.file_size_bytes,
        ingested_at     = EXCLUDED.ingested_at;
""")


def get_engine() -> Engine:
    return create_engine(settings.db_url, pool_pre_ping=True)


def load_acquisitions(rows: list[WarehouseRow], engine: Engine | None = None) -> int:
    """Upsert *rows* into noaa_acquisitions. Returns the number of rows processed."""
    if not rows:
        return 0

    eng = engine or get_engine()
    params = [
        {
            "acquisition_id": r.acquisition_id,
            "event_name": r.event_name,
            "acquisition_date": r.acquisition_date,
            "sensor": r.sensor,
            "resolution_cm": r.resolution_cm,
            "footprint_wkt": r.footprint_wkt,
            "download_url": r.download_url,
            "file_size_bytes": r.file_size_bytes,
            "crs": r.crs,
            "ingested_at": r.ingested_at,
        }
        for r in rows
    ]

    with eng.begin() as conn:
        conn.execute(_INSERT_ACQUISITION, params)

    log.info("loaded acquisitions", count=len(rows))
    return len(rows)
