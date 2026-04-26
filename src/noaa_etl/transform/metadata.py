"""Transform raw AcquisitionRecords into warehouse-ready rows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone

from noaa_etl.extract.noaa_client import AcquisitionRecord


@dataclass
class WarehouseRow:
    """Normalized row ready for insertion into noaa_acquisitions."""

    acquisition_id: str
    event_name: str
    acquisition_date: date
    sensor: str
    resolution_cm: float
    # WKT polygon derived from bounding box — PostGIS will cast this to geometry
    footprint_wkt: str
    download_url: str
    file_size_bytes: int | None
    crs: str
    ingested_at: datetime


def transform(records: list[AcquisitionRecord]) -> list[WarehouseRow]:
    """Convert a batch of raw records to warehouse rows, filtering out invalid entries."""
    rows: list[WarehouseRow] = []
    for rec in records:
        if not _is_valid(rec):
            continue
        rows.append(
            WarehouseRow(
                acquisition_id=rec.acquisition_id,
                event_name=rec.event_name,
                acquisition_date=rec.acquisition_date,
                sensor=rec.sensor,
                resolution_cm=rec.resolution_cm,
                footprint_wkt=_bbox_to_wkt(
                    rec.bbox_west, rec.bbox_south, rec.bbox_east, rec.bbox_north
                ),
                download_url=rec.download_url,
                file_size_bytes=rec.file_size_bytes,
                crs=rec.crs,
                ingested_at=datetime.now(tz=timezone.utc),
            )
        )
    return rows


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _is_valid(rec: AcquisitionRecord) -> bool:
    """Basic quality gate: reject records with null geometry or missing ID."""
    if not rec.acquisition_id:
        return False
    if rec.bbox_west >= rec.bbox_east or rec.bbox_south >= rec.bbox_north:
        return False
    if rec.resolution_cm <= 0:
        return False
    return True


def _bbox_to_wkt(west: float, south: float, east: float, north: float) -> str:
    """Convert a bounding box to a WKT POLYGON in lon/lat order."""
    return (
        f"POLYGON(("
        f"{west} {south}, "
        f"{east} {south}, "
        f"{east} {north}, "
        f"{west} {north}, "
        f"{west} {south}"
        f"))"
    )
