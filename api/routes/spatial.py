"""Spatial search endpoint — POST a GeoJSON polygon, get intersecting acquisitions."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.auth import require_api_key
from api.db import get_db
from api.models.schemas import AcquisitionOut, SpatialSearchRequest, SpatialSearchResponse

router = APIRouter(prefix="/spatial", tags=["spatial"])


@router.post("/search", response_model=SpatialSearchResponse)
def spatial_search(
    req: SpatialSearchRequest,
    _key: str = Depends(require_api_key),
    db: Session = Depends(get_db),
) -> SpatialSearchResponse:
    """Return all acquisitions whose footprint intersects the supplied GeoJSON polygon."""
    geojson_str = json.dumps(req.geometry.model_dump())

    clauses = ["ST_Intersects(a.footprint, ST_GeomFromGeoJSON(:geojson))"]
    params: dict = {"geojson": geojson_str}

    if req.event_name:
        clauses.append("a.event_name = :event_name")
        params["event_name"] = req.event_name
    if req.date_from:
        clauses.append("a.acquisition_date >= :date_from")
        params["date_from"] = req.date_from
    if req.date_to:
        clauses.append("a.acquisition_date <= :date_to")
        params["date_to"] = req.date_to
    if req.max_resolution_cm:
        clauses.append("a.resolution_cm <= :max_res")
        params["max_res"] = req.max_resolution_cm

    where = " AND ".join(clauses)
    rows = db.execute(
        text(f"""
            SELECT
                a.acquisition_id, a.event_name, a.acquisition_date, a.sensor,
                a.resolution_cm, ST_AsText(a.footprint) AS footprint_wkt,
                a.download_url, a.file_size_bytes, a.crs, a.ingested_at
            FROM noaa_acquisitions a
            WHERE {where}
            ORDER BY a.acquisition_date DESC
        """),
        params,
    ).mappings().all()

    results = [AcquisitionOut(**dict(r)) for r in rows]
    return SpatialSearchResponse(count=len(results), results=results)


@router.post("/union", response_model=dict)
def spatial_union(
    req: SpatialSearchRequest,
    _key: str = Depends(require_api_key),
    db: Session = Depends(get_db),
) -> dict:
    """Return the ST_Union of all matching footprints as GeoJSON."""
    geojson_str = json.dumps(req.geometry.model_dump())

    clauses = ["ST_Intersects(footprint, ST_GeomFromGeoJSON(:geojson))"]
    params: dict = {"geojson": geojson_str}

    if req.event_name:
        clauses.append("event_name = :event_name")
        params["event_name"] = req.event_name

    where = " AND ".join(clauses)
    row = db.execute(
        text(f"""
            SELECT
                COUNT(*)                                             AS count,
                ST_AsGeoJSON(ST_Union(footprint))                    AS union_geojson,
                ST_Area(ST_Union(footprint)::geography) / 1e6        AS total_area_km2
            FROM noaa_acquisitions
            WHERE {where}
        """),
        params,
    ).mappings().first()

    if not row or row["count"] == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="No acquisitions found intersecting the supplied geometry.")

    return {
        "count": row["count"],
        "total_area_km2": row["total_area_km2"],
        "geometry": json.loads(row["union_geojson"]) if row["union_geojson"] else None,
    }
