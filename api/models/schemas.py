"""Pydantic schemas for request/response models."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared
# ---------------------------------------------------------------------------

class GeoJsonPolygon(BaseModel):
    type: str = "Polygon"
    coordinates: list[list[list[float]]]


class BoundingBox(BaseModel):
    west: float = Field(..., ge=-180, le=180)
    south: float = Field(..., ge=-90, le=90)
    east: float = Field(..., ge=-180, le=180)
    north: float = Field(..., ge=-90, le=90)


# ---------------------------------------------------------------------------
# Acquisitions
# ---------------------------------------------------------------------------

class AcquisitionOut(BaseModel):
    acquisition_id: str
    event_name: str
    acquisition_date: date
    sensor: str
    resolution_cm: float
    footprint_wkt: str | None = None
    download_url: str
    file_size_bytes: int | None
    crs: str
    ingested_at: datetime

    model_config = {"from_attributes": True}


class AcquisitionListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    results: list[AcquisitionOut]


# ---------------------------------------------------------------------------
# Coverage statistics
# ---------------------------------------------------------------------------

class CoverageStatOut(BaseModel):
    event_name: str
    stat_date: date
    acquisition_count: int
    avg_resolution_cm: float | None
    total_area_km2: float | None
    cumulative_acquisitions: int

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Spatial search
# ---------------------------------------------------------------------------

class SpatialSearchRequest(BaseModel):
    geometry: GeoJsonPolygon
    event_name: str | None = None
    date_from: date | None = None
    date_to: date | None = None
    max_resolution_cm: float | None = None


class SpatialSearchResponse(BaseModel):
    count: int
    results: list[AcquisitionOut]


# ---------------------------------------------------------------------------
# ML feature export
# ---------------------------------------------------------------------------

class MLFeatureRow(BaseModel):
    acquisition_id: str
    event_name: str
    acquisition_date: date
    sensor: str
    resolution_cm: float
    footprint_area_km2: float | None
    centroid_lon: float | None
    centroid_lat: float | None
    bbox_west: float | None
    bbox_south: float | None
    bbox_east: float | None
    bbox_north: float | None
    bbox_width_deg: float | None
    bbox_height_deg: float | None
    acquisition_year: int | None
    acquisition_month: int | None
    day_of_year: int | None
    day_of_week: int | None
    event_avg_resolution_cm: float | None
    event_daily_area_km2: float | None
    event_cumulative_count: int | None
    resolution_delta_cm: float | None
    area_rank_in_event_day: int | None

    model_config = {"from_attributes": True}


class MLExportResponse(BaseModel):
    event_name: str | None
    date_from: date | None
    date_to: date | None
    row_count: int
    rows: list[MLFeatureRow]
