"""Acquisitions CRUD endpoints."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from api.auth import require_api_key
from api.db import get_db
from api.models.schemas import AcquisitionListResponse, AcquisitionOut

router = APIRouter(prefix="/acquisitions", tags=["acquisitions"])


@router.get("", response_model=AcquisitionListResponse)
def list_acquisitions(
    event_name: str | None = Query(None),
    sensor: str | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    min_resolution_cm: float | None = Query(None, gt=0),
    max_resolution_cm: float | None = Query(None, gt=0),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    _key: str = Depends(require_api_key),
    db: Session = Depends(get_db),
) -> AcquisitionListResponse:
    filters = _build_filters(event_name, sensor, date_from, date_to,
                              min_resolution_cm, max_resolution_cm)
    total_q = text(f"SELECT COUNT(*) FROM noaa_acquisitions WHERE {filters['where']}")
    total: int = db.execute(total_q, filters["params"]).scalar_one()

    rows_q = text(f"""
        SELECT
            acquisition_id, event_name, acquisition_date, sensor,
            resolution_cm, ST_AsText(footprint) AS footprint_wkt,
            download_url, file_size_bytes, crs, ingested_at
        FROM noaa_acquisitions
        WHERE {filters['where']}
        ORDER BY acquisition_date DESC
        LIMIT :limit OFFSET :offset
    """)
    rows = db.execute(
        rows_q,
        {**filters["params"], "limit": page_size, "offset": (page - 1) * page_size},
    ).mappings().all()

    return AcquisitionListResponse(
        total=total,
        page=page,
        page_size=page_size,
        results=[AcquisitionOut(**dict(r)) for r in rows],
    )


@router.get("/{acquisition_id}", response_model=AcquisitionOut)
def get_acquisition(
    acquisition_id: str,
    _key: str = Depends(require_api_key),
    db: Session = Depends(get_db),
) -> AcquisitionOut:
    row = db.execute(
        text("""
            SELECT acquisition_id, event_name, acquisition_date, sensor,
                   resolution_cm, ST_AsText(footprint) AS footprint_wkt,
                   download_url, file_size_bytes, crs, ingested_at
            FROM noaa_acquisitions
            WHERE acquisition_id = :id
        """),
        {"id": acquisition_id},
    ).mappings().first()

    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Acquisition {acquisition_id!r} not found.")
    return AcquisitionOut(**dict(row))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_filters(
    event_name: str | None,
    sensor: str | None,
    date_from: date | None,
    date_to: date | None,
    min_res: float | None,
    max_res: float | None,
) -> dict:
    clauses = ["1=1"]
    params: dict = {}
    if event_name:
        clauses.append("event_name = :event_name")
        params["event_name"] = event_name
    if sensor:
        clauses.append("UPPER(sensor) = UPPER(:sensor)")
        params["sensor"] = sensor
    if date_from:
        clauses.append("acquisition_date >= :date_from")
        params["date_from"] = date_from
    if date_to:
        clauses.append("acquisition_date <= :date_to")
        params["date_to"] = date_to
    if min_res:
        clauses.append("resolution_cm >= :min_res")
        params["min_res"] = min_res
    if max_res:
        clauses.append("resolution_cm <= :max_res")
        params["max_res"] = max_res
    return {"where": " AND ".join(clauses), "params": params}
